import sys
import os
import time, random

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import geopandas as gpd
from shapely.geometry import Point
from opencage.geocoder import OpenCageGeocode, RateLimitExceededError, InvalidInputError
from utils.constants import dataset_altitude
from utils.loggerUtils import logger
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
                logger.info(f"Adresse de collecte de données : {formatted_address}")
                return {
                    "city": city,
                    "country": country,
                    "formatted_address": formatted_address
                }
            except KeyError:
                aquatic_location = results[0]['formatted']
                logger.info(f"Données récoltées dans une zone aquatique : {aquatic_location}")
                return {"aquatic_location": aquatic_location}
    except Exception as ex:
        logger.error(f"{ex}")
        return {}
    except RateLimitExceededError as ex:
        # Use all available requests
        logger.error(ex)
    except InvalidInputError as ex:
        logger.error(f"Request city, country : Invalid Input Error : {ex}")


def get_altitude(lat, lng, max_retries=5, base_delay=1):
    """
    Détermine l'altitude à l'aide de la latitude et la longitude, avec gestion du retry.
    """
    for attempt in range(max_retries):
        try:
            url = f"https://api.opentopodata.org/v1/{dataset_altitude}?locations={lat},{lng}"
            r = requests.get(url).json()
            return r['results'][0]['elevation']
        except InvalidInputError as ex:
            logger.error(f"Request altitude : Invalid Input Error : {ex}")
            break
        except Exception as ex:
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            logger.warning(f"Attempt {attempt+1} failed: {ex}. Retrying in {delay:.2f} seconds.")
            time.sleep(delay)
    return None


def get_distance_from_equator(lat):
    """
    Détermine la distancce depuis l'équateur
    """
    distance = abs(lat)
    climat = "equatorial" if distance <= 10 else "tropical" if distance <= 23.5 else "polaire" if distance > 60 else "tempere"
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
    coastlines = gpd.read_file("data/input/ne_10m_coastline.shp")
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
    logger.info(f"Données récupérées dans l'hémisphère {hemisphere}")
    return hemisphere