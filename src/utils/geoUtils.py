import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from my_secrets.secrets import apikey
from opencage.geocoder import OpenCageGeocode

OCG = OpenCageGeocode(apikey)

def get_city_country(lat, lng):
    results = OCG.reverse_geocode(lat, lng)
    return results[0]['components']['country'], results[0]['components']['city'], results[0]['formatted']