import time
import board
import busio
import adafruit_ds3231
import adafruit_scd30
import adafruit_veml7700
import serial
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from adafruit_bmp280 import Adafruit_BMP280_I2C
from .loggerUtils import logger

RTC_ADDR = 0x68
I2C_BUS = 1

# Globals (créés à la demande)
_I2C = None
_VEML = None
_SCD = None
_BMP = None
_RTC = None

def _get_i2c():
    global _I2C
    if _I2C is None:
        _I2C = busio.I2C(board.SCL, board.SDA)
    return _I2C


def _retry(fn, tries=5, delay=0.2, name="I2C op"):
    last = None
    for i in range(tries):
        try:
            return fn()
        except OSError as e:
            last = e
            logger.warning(f"{name} failed ({i+1}/{tries}): {e}")
            time.sleep(delay)
    raise last


def _get_veml():
    global _VEML
    if _VEML is None:
        i2c = _get_i2c()
        _VEML = _retry(lambda: adafruit_veml7700.VEML7700(i2c), name="VEML init")
        # Config stable
        _VEML.integration_time = 100
        _VEML.gain = 1
        time.sleep(0.2)
    return _VEML


def _get_scd():
    global _SCD
    if _SCD is None:
        i2c = _get_i2c()
        _SCD = _retry(lambda: adafruit_scd30.SCD30(i2c), name="SCD30 init")
        # IMPORTANT: la config I²C du SCD30 peut échouer -> retry aussi
        _retry(lambda: setattr(_SCD, "measurement_interval", 2), name="SCD30 set interval")
        _retry(lambda: setattr(_SCD, "self_calibration_enabled", False), name="SCD30 disable ASC")
        time.sleep(0.2)
    return _SCD


def _get_bmp():
    global _BMP
    if _BMP is None:
        i2c = _get_i2c()
        # adapte 0x76/0x77 selon ton câblage BMP280
        _BMP = _retry(lambda: Adafruit_BMP280_I2C(i2c, address=0x76), name="BMP280 init")
        time.sleep(0.1)
    return _BMP


def _bcd_to_int(bcd: int) -> int:
    return ((bcd >> 4) * 10) + (bcd & 0x0F)


def get_pressure_temperature():
    try:
        bmp = _get_bmp()
        temperature = bmp.temperature
        pressure = bmp.pressure
        logger.info(f"Temperature: {temperature:.2f} °C, Pressure: {pressure:.2f} hPa")
        return temperature, pressure
    except Exception as e:
        logger.error(f"BMP280 Error : {e}")
        return None, None


def read_luminosity():
    try:
        veml = _get_veml()
        time.sleep(0.2)
        lux = veml.lux
        white = veml.white
        logger.info(f"Luminosity: {lux:.2f} lux, White: {white}")
        return lux, white
    except Exception as e:
        logger.error(f"VEML7700 Error : {e}")
        return None, None


def get_scd30_data():
    try:
        scd = _get_scd()

        t0 = time.time()
        while not scd.data_available:
            if time.time() - t0 > 5:
                raise TimeoutError("SCD30: no data available (timeout)")
            time.sleep(0.2)

        co2 = scd.CO2
        temp = scd.temperature
        rh = scd.relative_humidity

        logger.info(f"CO2: {co2:.0f}ppm, Temperature: {temp:.2f}°C, Relative Humidity: {rh:.2f}%")
        return co2, temp, rh

    except Exception as e:
        logger.error(f"SCD30 Error : {e}")
        return None, None, None

    
def nmea_to_decimal(coord, direction):
    """
    Convertit un format NMEA (ddmm.mmmm) en degrés décimaux
    """
    if not coord or not direction:
        return None

    degrees = int(coord[:2])
    minutes = float(coord[2:])
    decimal = degrees + minutes / 60

    if direction in ("S", "W"):
        decimal *= -1

    return decimal


def read_gps_position(timeout=30):
    """
    Lit l'UART et retourne (latitude, longitude, altitude)
    ou (None, None, None) si pas de fix dans le timeout.
    """
    start = time.time()

    try:
        ser = serial.Serial(
        port="/dev/serial0",
        baudrate=9600,
        timeout=1
        )
        
        while time.time() - start < timeout:
            line = ser.readline().decode(errors="ignore").strip()

            if not line.startswith("$GPGGA"):
                continue

            parts = line.split(",")

            fix_quality = parts[6]
            if fix_quality == "0":
                continue  # pas de fix

            lat = nmea_to_decimal(parts[2], parts[3])
            lon = nmea_to_decimal(parts[4], parts[5])
            alt = float(parts[9]) if parts[9] else None
            
            logger.info(f"GPS position : Latitude={lat}, Longitude={lon}, Altitude={alt} m")

            return lat, lon, alt
        if start + timeout <= time.time():
            logger.error("Timeout reached without obtaining GPS fix.")
    except Exception as e:
        logger.error(f"Error during GPS reading : {e}")

    finally:
        ser.close()

    return None, None, None


def get_rtc_datetime(timezone):
    """
    Get RTC datetime as a formatted string in local timezone (Asia/Bangkok).
    """
    logger.info(f"Getting RTC datetime for timezone: {timezone}")
    dt = datetime.now(ZoneInfo(timezone)).strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"Local timestamp for timezone '{timezone}': {dt}")
    return dt
