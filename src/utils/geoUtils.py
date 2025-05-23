import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import requests
from opencage.geocoder import OpenCageGeocode, RateLimitExceededError, InvalidInputError
from utils.constants import dataset_altitude
from my_secrets.secrets import apikey


OCG = OpenCageGeocode(apikey)


def get_city_country(lat: float, lng: float):
    try:
        results = OCG.reverse_geocode(lat, lng)
        if results and len(results):
            city, country, formatted_address = results[0]['components']['country'], results[0]['components']['city'], results[0]['formatted']
            print(f"City : {city}, country : {country}, formatted address : {formatted_address}")
            return city, country, formatted_address
    except RateLimitExceededError as ex:
        # Use all available requests
        print(ex)
    except InvalidInputError as ex:
        print(f"Request city, country : Invalid Input Error : {ex}")


def get_altitude(lat, lng):
    try:
        url = f"https://api.opentopodata.org/v1/{dataset_altitude}?locations={lat},{lng}"
        r = requests.get(url).json()
        altitude = r['results'][0]['elevation']
        print(f"Altitude de {altitude}m.")
        return altitude
    except InvalidInputError as ex:
        print(f"Request altitude : Invalid Input Error : {ex}")