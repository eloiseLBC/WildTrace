import board
import busio
from adafruit_bmp280 import Adafruit_BMP280_I2C
from .loggerUtils import logger, log_file

def get_humidity_temperature():
    i2c = busio.I2C(board.SCL, board.SDA)
    bmp280 = Adafruit_BMP280_I2C(i2c, address=0x76)

    temperature = bmp280.temperature      # °C
    pressure = bmp280.pressure            # hPa

    logger.info(f"Temperature: {temperature:.2f} °C, Pressure: {pressure:.2f} hPa")
    return temperature, pressure
