import unittest
import os
import sys

# Injecter la clé API dans le module secrets avant l'import
if 'OPEN_CAGE_GEOCODE_APIKEY' in os.environ:
    # Créer un module secrets temporaire pour les tests
    import types
    secrets_module = types.ModuleType('secrets')
    secrets_module.apikey = os.environ.get('OPEN_CAGE_GEOCODE_APIKEY')
    sys.modules['my_secrets.secrets'] = secrets_module

from src.utils.geoUtils import get_city_country, get_altitude, get_coastline_distance, get_distance_from_equator, \
    get_hemisphere


class GeoUtilsCase(unittest.TestCase):
    def test_get_city_country(self):
        """Test the get_city_country function with a known latitude and longitude"""
        result = get_city_country(48.8566, 2.3522)
        expected = {
            "city": "Paris",
            "country": "France",
            "formatted_address": "Paris, Île-de-France, France"
        }
        self.assertEqual(result['city'], expected['city'])
        self.assertEqual(result['country'], expected['country'])
        self.assertIn("Paris", result['formatted_address'])

    def test_get_city_country_invalid_coordinates(self):
        """Test the get_city_country function with invalid coordinates"""
        result = get_city_country(9999, 9999)
        self.assertEqual(result, None)

    def test_get_city_country_unnamed_road(self):
        """Test the get_city_country function with coordinates in an aquatic location"""
        result = get_city_country(-33.9249, 18.4241)
        self.assertIn("unnamed road", result['formatted_address'].lower())

    def test_get_altitude(self):
        """Test the get_altitude function with a known latitude and longitude"""
        altitude = get_altitude(48.8566, 2.3522)
        self.assertIsInstance(altitude, (int, float))
        self.assertGreaterEqual(altitude, 0)

    def test_get_altitude_invalid_coordinates(self):
        """Test the get_altitude function with invalid coordinates"""
        altitude = get_altitude(9999, 9999)
        self.assertIsNone(altitude)

    def test_distance_equator_positive(self):
        """Test the get_distance_from_equator function with known latitude"""
        distance = get_distance_from_equator(48.8566)
        self.assertGreaterEqual(distance["distance_equator_km"], 0)

    def test_distance_equator_negative(self):
        """Test the get_distance_from_equator function with a negative latitude"""
        distance = get_distance_from_equator(-48.8566)
        self.assertGreaterEqual(distance["distance_equator_km"], 0)

    def test_coastline_distance(self):
        """Test the get_coastline_distance function with known coordinates"""
        distance = get_coastline_distance(48.8566, 2.3522)
        self.assertGreaterEqual(distance["distance_coastline"], 0)


    def test_north_hemisphere(self):
        """Test the get_hemisphere function with known latitude"""
        hemisphere = get_hemisphere(48.8566)
        self.assertEqual(hemisphere, "nord")

    def test_south_hemisphere(self):
        hemisphere = get_hemisphere(-48.8566)
        self.assertEqual(hemisphere, "sud")

if __name__ == '__main__':
    unittest.main()

