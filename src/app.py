from opencage.geocoder import OpenCageGeocode
from src.secrets import apikey

OCG = OpenCageGeocode(apikey)

def get_city_country(lat, lng):
    results = OCG.reverse_geocode(lat, lng)
    print(results[0]['formatted'])

if __name__ == "__main__":
    latitude, longitude = 44.838295, -0.575381
    get_city_country(latitude, longitude)

