import sys
import os
import time
import random
import json
import openmeteo_requests
import requests_cache
import requests
import geopandas as gpd

from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from retry_requests import retry
from datetime import datetime, timedelta, timezone
from shapely.geometry import Point
from opencage.geocoder import OpenCageGeocode, RateLimitExceededError, InvalidInputError
from .loggerUtils import logger
from my_secrets.secrets import apikey


OCG = OpenCageGeocode(apikey)

current_dir = Path(__file__).parent
constants_path = current_dir / 'constants.json'

with open(constants_path, 'r') as file:
    constants = json.load(file)


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


def get_altitude(lat, lng, max_retries=2, base_delay=1):
    """
    Détermine l'altitude à l'aide de la latitude et la longitude, avec gestion du retry.
    """
    for attempt in range(max_retries):
        try:
            url = f"https://api.open-elevation.com/api/v1/lookup?locations={lat},{lng}"
            r = requests.get(url, timeout=15).json()
            if r['results'][0]['elevation'] == 0.0:
                return None
            return r['results'][0]['elevation']
        except InvalidInputError as ex:
            logger.error(f"Request altitude : Invalid Input Error : {ex}")
            break
        except Exception as ex:
            delay = base_delay + random.uniform(0, 1)
            logger.warning(f"Attempt {attempt+1} failed: {ex}. Retrying in {delay:.2f} seconds.")
            if attempt < max_retries - 1:
                time.sleep(delay)

    # Fallback vers Open Topodata
    logger.info("GET ALTITUDE : Fallback vers Open Topodata...")
    try:
        url = f"https://api.opentopodata.org/v1/srtm30m?locations={lat},{lng}"
        r = requests.get(url, timeout=15).json()
        return r['results'][0]['elevation']
    except Exception as ex:
        logger.error(f"Open Topodata aussi indisponible: {ex}. \nAltitude non trouvée.")
    return None


def get_pressure(lat, long, formatted_timestamp, hour):
    try:
        # Setup the Open-Meteo API client with cache and retry on error
        cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
        retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
        openmeteo = openmeteo_requests.Client(session = retry_session)
        
        logger.info(f"Formatted yyyyMMdd : {formatted_timestamp}")

        # Make sure all required weather variables are listed here
        # The order of variables in hourly or daily is important to assign them correctly below
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": 20.4737,
            "longitude": 106.0229,
            "hourly": ["temperature_2m", "surface_pressure", "visibility", "rain"],
            "start_date": formatted_timestamp,
            "end_date": formatted_timestamp,
        }
        responses = openmeteo.weather_api(url, params=params)

        # Process first location. Add a for-loop for multiple locations or weather models
        response = responses[0]
        hourly = response.Hourly()
        hourly_surface_pressure = hourly.Variables(1).ValuesAsNumpy()
        return float(hourly_surface_pressure[hour])
    except Exception as e:
        logger.error(f"Error in get_pressure fonction : {e}")
        return ""
    
    

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
    # Get the directory where this script is located
    project_root = Path(__file__).parent.parent.parent
    coastline_path = project_root / "data" / "input" / "ne_10m_coastline.shp"
    coastlines = gpd.read_file(coastline_path)
    location = Point(lng, lat)
    dist = coastlines.distance(location).min()
    return {
        "distance_coastline" : float(dist)
    }


def get_hemisphere(lat):
    """
    Détermine l'émisphère dans lequel se situe la position
    """
    hemisphere = "North" if lat > 0 else "South" if lat < 0 else "equateur"
    return hemisphere