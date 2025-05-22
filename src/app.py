import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from opencage.geocoder import OpenCageGeocode
from my_secrets.secrets import apikey

OCG = OpenCageGeocode(apikey)

def get_city_country(lat, lng):
    results = OCG.reverse_geocode(lat, lng)
    return results[0]['components']['country'], results[0]['components']['city'], results[0]['formatted']


if __name__ == "__main__":
    latitude, longitude = 44.838295, -0.575381
    city, country, formatted_address = get_city_country(latitude, longitude)
    print(f"City : {city}, country : {country}, formatted address : {formatted_address}")

