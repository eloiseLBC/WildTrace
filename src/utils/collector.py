import board
import busio
import serial
import time
import smbus2

from zoneinfo import ZoneInfo
from adafruit_bmp280 import Adafruit_BMP280_I2C
from .loggerUtils import logger, log_file
from datetime import datetime, timezone

I2C_BUS = 1
RTC_ADDR = 0x68

def get_humidity_temperature():
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        bmp280 = Adafruit_BMP280_I2C(i2c, address=0x76)

        temperature = bmp280.temperature      # °C
        pressure = bmp280.pressure            # hPa

        logger.info(f"Temperature: {temperature:.2f} °C, Pressure: {pressure:.2f} hPa")
        return temperature, pressure
    except Exception as e:
        logger.error(f"Erreur lors de la lecture du capteur BMP280 : {e}")
        return None, None


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
            
            logger.info(f"Position GPS : Latitude={lat}, Longitude={lon}, Altitude={alt} m")

            return lat, lon, alt
        if start + timeout <= time.time():
            logger.error("Timeout atteint sans obtenir de fix GPS.")
    except Exception as e:
        logger.error(f"Erreur lors de la lecture du GPS : {e}")

    finally:
        ser.close()

    return None, None, None




def _bcd_to_int(bcd: int) -> int:
    return ((bcd >> 4) * 10) + (bcd & 0x0F)

def read_rtc_datetime(addr: int = RTC_ADDR, bus_id: int = I2C_BUS) -> datetime:
    """
    Read current date/time from a DS3231/DS1307 RTC at I2C address 0x68.
    Returns a timezone-aware datetime in UTC by default (you can convert to local later).
    """
    bus = smbus2.SMBus(bus_id)

    # DS3231/DS1307 time registers start at 0x00 and are 7 bytes:
    # 0: seconds, 1: minutes, 2: hours, 3: day-of-week, 4: day, 5: month(+century bit), 6: year (0-99)
    data = bus.read_i2c_block_data(addr, 0x00, 7)

    seconds = _bcd_to_int(data[0] & 0x7F)
    minutes = _bcd_to_int(data[1] & 0x7F)

    # Hours can be in 24h or 12h format. We handle both.
    hr = data[2]
    if hr & 0x40:  # 12-hour mode
        hours = _bcd_to_int(hr & 0x1F)
        pm = bool(hr & 0x20)
        if pm and hours != 12:
            hours += 12
        if not pm and hours == 12:
            hours = 0
    else:  # 24-hour mode
        hours = _bcd_to_int(hr & 0x3F)

    day = _bcd_to_int(data[4] & 0x3F)
    month_raw = data[5]
    month = _bcd_to_int(month_raw & 0x1F)
    year = _bcd_to_int(data[6]) + 2000  # common assumption (works for DS3231 modules)

    # Return in UTC (you can change to local timezone if you want)
    return datetime(year, month, day, hours, minutes, seconds, tzinfo=timezone.utc)

def get_rtc_datetime():
    """
    Get RTC datetime as a formatted string in local timezone (Asia/Bangkok).
    """
    dt = read_rtc_datetime()
    dt_local = dt.astimezone(ZoneInfo("Asia/Bangkok")).strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"Local timestamp : {dt_local}")
    return dt_local