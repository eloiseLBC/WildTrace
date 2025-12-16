from smbus2 import SMBus
import time

def get_humidity_temperature():
    """
    Lit la température et l'humidité depuis un capteur SHT31 connecté via I2C.
    Retourne un tuple (température en °C, humidité en %).
    """
    I2C_BUS = 21          # bus GPIO du Raspberry Pi 4
    SHT31_ADDR = 0x44     # adresse détectée par i2cdetect

    # Commande "single shot, high repeatability, clock stretching disabled"
    MEASURE_CMD = [0x24, 0x00]

    with SMBus(I2C_BUS) as bus:
        # Envoi de la commande de mesure
        bus.write_i2c_block_data(SHT31_ADDR, MEASURE_CMD[0], [MEASURE_CMD[1]])

        # Le capteur a besoin d'un petit temps de réflexion
        time.sleep(0.015)

        # Lecture de 6 octets :
        # T_MSB, T_LSB, T_CRC, H_MSB, H_LSB, H_CRC
        data = bus.read_i2c_block_data(SHT31_ADDR, 0x00, 6)

        temp_raw = data[0] << 8 | data[1]
        hum_raw  = data[3] << 8 | data[4]

        temperature = -45 + (175 * temp_raw / 65535.0)
        humidity = 100 * hum_raw / 65535.0

        print(f"Température : {temperature:.2f} °C")
        print(f"Humidité    : {humidity:.2f} %")
