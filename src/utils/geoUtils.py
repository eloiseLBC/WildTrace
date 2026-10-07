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
from zoneinfo import ZoneInfo



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
                logger.info(f"Results pour get_city_country : {results}")
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
    if lat is not None : 
        distance = abs(lat)
        climat = "equatorial" if distance <= 10 else "tropical" if distance <= 23.5 else "polaire" if distance > 60 else "tempere"
        distance_km = distance * 111
        return {
            "distance_equator": distance,
            "distance_equator_km": distance_km,
            "climat": climat
        }
    else:
        logger.warning(f"Latitude nulle -> Pas de calcul de distance_equator, distance_equator_km et climat")
        return {
            "distance_equator": None,
            "distance_equator_km": None,
            "climat": None
        }
        


def get_coastline_distance(lat, lng):
    """
    Détermine la distance d'une position d'une côté
    """
    if lat is not None or lng is not None: 
        distance = abs(lat)
        climat = "equatorial" if distance <= 10 else "tropical" if distance <= 23.5 else "polaire" if distance > 60 else "tempere"
        distance_km = distance * 111
        return {
            "distance_equator": distance,
            "distance_equator_km": distance_km,
            "climat": climat
        }
        # Get the directory where this script is located
        project_root = Path(__file__).parent.parent.parent
        coastline_path = project_root / "data" / "input" / "ne_10m_coastline.shp"
        coastlines = gpd.read_file(coastline_path)
        location = Point(lng, lat)
        dist = coastlines.distance(location).min()
        return {
            "distance_coastline" : float(dist)
        }
    else:
        logger.warning(f"Latitude et/ou longitude nulle -> Pas de calcul de distance_coastline")
        return {
            "distance_coastline" : None
        }
        


def get_hemisphere(lat):
    """
    Détermine l'hémisphère dans lequel se situe la position
    """
    if lat is not None:
        hemisphere = "North" if lat > 0 else "South" if lat < 0 else "equateur"
        return hemisphere
    else:
        logger.warning(f"Latitude nulle -> Pas de calcul de hemisphere")
        return None
    
def get_temperature_humidity(lat, lng, timestamp, timezone):
    """
    Détermine la température dans le cas d'un capteur défaillant
    Nécessite en entrée : latitude, longitude, timestamp
    """
    date = datetime.fromisoformat(timestamp).replace(
        tzinfo=ZoneInfo(timezone)
    )
    logger.info(f"Timestamp avec timezone : {date}")
    previous_hour = date.replace(minute=0, second=0, microsecond=0)
    next_hour = previous_hour + timedelta(hours=1)

    params = {
        "latitude": lat,
        "longitude": lng,
        "timezone": timezone,
        "start_date": previous_hour.date().isoformat(),
        "end_date": next_hour.date().isoformat(),
        "hourly": "temperature_2m,relative_humidity_2m",
        "temperature_unit": "celsius",
    }

    try:
        response = requests.get(
            "https://archive-api.open-meteo.com/v1/archive",
            params=params,
            timeout=20,
        )
        response.raise_for_status()
        hourly = response.json()["hourly"]

        times = hourly["time"]
        before = times.index(previous_hour.strftime("%Y-%m-%dT%H:%M"))
        weight = (date - previous_hour).total_seconds() / 3600

        # À une heure exacte, la valeur suivante n'est pas nécessaire.
        after = (
            times.index(next_hour.strftime("%Y-%m-%dT%H:%M"))
            if weight > 0 else before
        )

        def interpolate(variable):
            start = hourly[variable][before]
            end = hourly[variable][after]

            if start is None or end is None:
                raise ValueError(f"Donnée manquante : {variable}")

            return round(start + weight * (end - start), 2)

        return interpolate("temperature_2m"), "open_meteo", interpolate("relative_humidity_2m"), "open_meteo"

    except (
        requests.RequestException,
        KeyError,
        IndexError,
        ValueError,
        TypeError,
    ) as exc:
        logger.warning(f"Fallback Open-Meteo indisponible : {exc}")
        return None
    
def get_co2(latitude, longitude, timestamp, timezone):
    date = datetime.fromisoformat(timestamp).replace(
        tzinfo=ZoneInfo(timezone)
    )
    previous_hour = date.replace(minute=0, second=0, microsecond=0)
    next_hour = previous_hour + timedelta(hours=1)

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": timezone,
        "start_date": previous_hour.date().isoformat(),
        "end_date": next_hour.date().isoformat(),
        "hourly": "carbon_dioxide",
    }

    try:
        response = requests.get(
            "https://air-quality-api.open-meteo.com/v1/air-quality",
            params=params,
            timeout=20,
        )
        response.raise_for_status()
        hourly = response.json()["hourly"]

        times = hourly["time"]
        values = hourly["carbon_dioxide"]
        before = times.index(previous_hour.strftime("%Y-%m-%dT%H:%M"))
        weight = (date - previous_hour).total_seconds() / 3600
        after = (
            times.index(next_hour.strftime("%Y-%m-%dT%H:%M"))
            if weight > 0 else before
        )

        if values[before] is None or values[after] is None:
            raise ValueError("Concentration CO₂ manquante")

        return round(
            values[before] + weight * (values[after] - values[before]),
            2,
        ), "open_meteo"

    except (
        requests.RequestException,
        KeyError,
        IndexError,
        ValueError,
        TypeError,
    ) as exc:
        logger.warning(f"Fallback CO₂ indisponible : {exc}")
        return None