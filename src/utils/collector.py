import board
import busio
import serial
import time

from adafruit_bmp280 import Adafruit_BMP280_I2C
from .loggerUtils import logger, log_file

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
    except Exception as e:
        logger.error(f"Erreur lors de la lecture du GPS : {e}")

    finally:
        ser.close()

    return None, None, None
