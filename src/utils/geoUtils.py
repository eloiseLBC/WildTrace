import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import requests
import geopandas as gpd
from shapely.geometry import Point
from opencage.geocoder import OpenCageGeocode, RateLimitExceededError, InvalidInputError
from utils.constants import dataset_altitude
from my_secrets.secrets import apikey


OCG = OpenCageGeocode(apikey)


def get_city_country(lat: float, lng: float):
    """
    Détermine la ville et le pays selon la latitude et la longitude.
    """
    try:
        results = OCG.reverse_geocode(lat, lng)
        if results and len(results):
            try:
                city = results[0]['components']['city']
                country = results[0]['components']['country']
                formatted_address = results[0]['formatted']
                return {
                    "city": city,
                    "country": country,
                    "formatted_address": formatted_address
                }
            except KeyError:
                return {"aquatic_location": results[0]['formatted']}
    except Exception as ex:
        print(f"ERROR: {ex}")
        return {}
    except RateLimitExceededError as ex:
        # Use all available requests
        print(ex)
    except InvalidInputError as ex:
        print(f"Request city, country : Invalid Input Error : {ex}")


def get_altitude(lat, lng):
    """
    Détermine l'altitude à l'aide de  la latitude et la longitude
    """
    try:
        url = f"https://api.opentopodata.org/v1/{dataset_altitude}?locations={lat},{lng}"
        r = requests.get(url).json()
        return r['results'][0]['elevation']
    except InvalidInputError as ex:
        print(f"Request altitude : Invalid Input Error : {ex}")


def get_distance_from_equator(lat):
    """
    Détermine la distancce depuis l'équateur
    """
    distance = abs(lat)
    climat = "équatorial" if distance <= 10 else "tropical" if distance <= 23.5 else "polaire" if distance > 60 else "tempéré"
    distance_km = distance * 111
    return {
        "distance_equator": distance,
        "distance_equator_km": distance_km,
        "climat": climat
    }


def get_coastline_distance(lat, lng):
    """
    Détermine la distance d'une position d'une côté
    """
    # Charger les côtes (costline file)
    coastlines = gpd.read_file("data/ne_10m_coastline.shp")
    location = Point(lng, lat)
    dist = coastlines.distance(location).min()
    return {
        "distance_coastline" : dist
    }


def get_hemisphere(lat):
    """
    Détermine l'émisphère dans lequel se situe la position
    """
    hemisphere = "nord" if lat > 0 else "sud" if lat < 0 else "equateur"
    return hemisphere