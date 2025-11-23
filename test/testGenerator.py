import unittest
import sys
import os
# Injecter la clé API dans le module secrets avant l'import
if 'OPEN_CAGE_GEOCODE_APIKEY' in os.environ:
    # Créer un module secrets temporaire pour les tests
    import types
    secrets_module = types.ModuleType('secrets')
    secrets_module.apikey = os.environ.get('OPEN_CAGE_GEOCODE_APIKEY')
    sys.modules['my_secrets.secrets'] = secrets_module

from src.utils.generator import (generate_timestamp, generate_temperature, generate_humidity, generate_pression,
                                 generate_co2, generate_environment, generate_lat_lng, generate_computed, get_luminosity)
from datetime import datetime

class MyTestCase(unittest.TestCase):
    def test_generate_timestamp(self):
        """Test the generate_timestamp function to ensure it returns a valid timestamp string"""
        timestamp = generate_timestamp()
        try:
            datetime.strptime(timestamp, "%d-%m-%Y %H:%M:%S.%f")
            valid_format = True
        except ValueError:
            valid_format = False
        self.assertTrue(valid_format, "Timestamp format is invalid")

    def test_get_luminosity(self):
        luminosity = get_luminosity(0, True, "desert")
        self.assertIsInstance(luminosity, float, "Luminosity should be an integer")
        self.assertGreaterEqual(luminosity, 0, "Nighttime luminosity should be >= 0")
        self.assertLessEqual(luminosity, 50, "Nighttime luminosity should be <= 50")

    def test_generate_temperature(self):
        temp = generate_temperature()
        self.assertIsInstance(temp, int, "Temperature should be an integer")
        self.assertGreaterEqual(temp, -51, "Temperature should be >= -50")
        self.assertLess(temp, 51, "Temperature should be < 50")

    def test_generate_humidity(self):
        hum = generate_humidity()
        self.assertIsInstance(hum, int, "Humidity should be an integer")
        self.assertGreaterEqual(hum, 0, "Humidity should be >= 0")
        self.assertLessEqual(hum, 100, "Humidity should be <= 100")

    def test_generate_pression(self):
        pres = generate_pression(100)
        self.assertIsInstance(pres, float, "Pression should be an integer")
        self.assertGreaterEqual(pres, 300.0, "Pression should be >= 300")
        self.assertLessEqual(pres, 1100.0, "Pression should be <= 1100")

    def test_generate_environment(self):
        env = generate_environment()
        self.assertIn(env, ["Desert", "Mountain", "Jungle", "Field", "City Dense", "City Airy", "Village", "Indoors", "Cloudy"], "Environment should be valid")

    def test_generate_co2(self):
        co2 = generate_co2("desert")
        self.assertIsInstance(co2, int, "CO2 concentration should be an integer")
        self.assertGreaterEqual(co2, 380, "CO2 concentration should be >= 400")
        self.assertLessEqual(co2, 450, "CO2 concentration should be <= 600")

    def test_generate_lat_lng(self):
        lat, lng = generate_lat_lng("desert")
        self.assertIsInstance(lat, float, "Latitude should be a float")
        self.assertIsInstance(lng, float, "Longitude should be a float")
        self.assertGreaterEqual(lat, -30, "Latitude should be >= -30")
        self.assertLessEqual(lat, 30, "Latitude should be <= 30")
        self.assertGreaterEqual(lng, -20, "Longitude should be >= -20")
        self.assertLessEqual(lng, 60, "Longitude should be <= 60")


    def test_generate_one_row(self):
        row = generate_computed()
        self.assertIsInstance(row, dict, "Generated row should be a dictionary")
        expected_keys = {"timestamp", "formatted_ddmmyyyy", "latitude", "longitude", "temperature",
                         "humidity", "pression", "luminosity", "concentration_co2", "environment",
                         "altitude", "hemisphere", "season", "is_night", "distance_equator",
                         "distance_coastline", "distance_equator_km", "climat"}

        # Vérifier que toutes les clés attendues sont présentes (permet des clés supplémentaires)
        self.assertTrue(expected_keys.issubset(set(row.keys())),
                        f"Generated row should contain at least these keys: {expected_keys}. "
                        f"Missing keys: {expected_keys - set(row.keys())}")

        # Optionnel: afficher les clés supplémentaires pour information
        extra_keys = set(row.keys()) - expected_keys
        if extra_keys:
            print(f"Additional keys found: {extra_keys}")  # Ou utilisez logging si disponible


if __name__ == '__main__':
    unittest.main()
