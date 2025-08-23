import unittest
from src.utils.dataUtils import get_formatted_ddmmyyyy, is_night, get_season
from datetime import datetime

class MyTestCase(unittest.TestCase):
    def test_is_night_false(self):
        timestamp = datetime.strptime("2023-10-01 12:00:00", "%Y-%m-%d %H:%M:%S")
        self.assertEqual(is_night(48.8566, 2.3522, timestamp), False)

    def test_is_night_true(self):
        timestamp = datetime.strptime("2023-10-01 23:00:00", "%Y-%m-%d %H:%M:%S")
        self.assertEqual(is_night(48.8566, 2.3522, timestamp), True)

    def test_get_season_north_summer(self):
        self.assertEqual(get_season("nord", "21-06-2023"), "Summer")

    def test_get_season_north_Sprint(self):
        self.assertEqual(get_season("nord", "20-03-2023"), "Spring")

    def test_get_season_north_automn(self):
        self.assertEqual(get_season("nord", "22-09-2023"), "Automne")

    def test_get_season_north_winter(self):
        self.assertEqual(get_season("nord", "21-12-2023"), "Winter")

    def test_get_season_south_summer(self):
        self.assertEqual(get_season("sud", "21-12-2023"), "Summer")

    def test_get_season_south_spring(self):
        self.assertEqual(get_season("sud", "22-09-2023"), "Spring")

    def test_get_season_south_automn(self):
        self.assertEqual(get_season("sud", "20-03-2023"), "Automne")

    def test_get_season_south_winter(self):
        self.assertEqual(get_season("sud", "22-06-2023"), "Winter")

    def test_get_formatted_ddmmyyyy(self):
        self.assertEqual(get_formatted_ddmmyyyy("01-10-2023 15:30:45.123456"), "01-10-2023")

if __name__ == '__main__':
    unittest.main()
