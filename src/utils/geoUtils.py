import sys
import math
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
from datetime import datetime, timedelta, timezone, timezone as utc_timezone
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
    """Détermine la ville, le pays et l'adresse depuis les coordonnées."""
    try:
        results = OCG.reverse_geocode(lat, lng)

        if not results:
            return {}

        result = results[0]
        components = result.get("components", {})
        formatted_address = result.get("formatted", "")

        city = (
            components.get("city")
            or components.get("town")
            or components.get("village")
            or components.get("municipality")
        )
        country = components.get("country")

        # Secours pour une adresse du type :
        # "1 Rue Victor Hugo, 33000 Bordeaux, France"
        parts = [part.strip() for part in formatted_address.split(",")]

        if len(parts) >= 3:
            if not city:
                city = parts[-2]
                postcode, separator, name = city.partition(" ")
                if separator and postcode.isdigit():
                    city = name

            if not country:
                country = parts[-1]

        logger.info(f"Adresse de collecte de données : {formatted_address}")

        return {
            "city": city,
            "country": country,
            "formatted_address": formatted_address,
        }

    except Exception as ex:
        logger.error(f"Erreur get_city_country : {ex}")
        return {}


def get_location_coordinates(location):
    """Récupère latitude, longitude et altitude à partir d'une adresse."""
    empty = {"latitude": None, "longitude": None, "altitude": None}

    try:
        results = OCG.geocode(location, language="fr", limit=1)

        if not results:
            logger.warning(f"Localisation introuvable : {location}")
            return empty

        result = results[0]
        latitude = float(result["geometry"]["lat"])
        longitude = float(result["geometry"]["lng"])

        logger.info(f"Adresse trouvée : {result['formatted']}")

        return {
            "latitude": latitude,
            "longitude": longitude,
            "altitude": get_altitude(latitude, longitude),
        }

    except Exception as exc:
        logger.warning(f"Localisation indisponible : {exc}")
        return empty

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


def get_pressure(lat, long, formatted_timestamp, hour, timezone_name="UTC"):
    """Pression historique à la position et à l'heure locale demandées."""
    try:
        response = requests.get(
            "https://archive-api.open-meteo.com/v1/archive",
            params={
                "latitude": lat, "longitude": long,
                "timezone": timezone_name,
                "start_date": formatted_timestamp,
                "end_date": formatted_timestamp,
                "hourly": "surface_pressure",
            },
            timeout=20,
        )
        response.raise_for_status()
        hourly = response.json()["hourly"]
        index = hourly["time"].index(f"{formatted_timestamp}T{hour:02d}:00")
        value = hourly["surface_pressure"][index]
        if (not isinstance(value, (int, float)) or isinstance(value, bool)
                or not math.isfinite(value)):
            raise ValueError("Pression absente ou invalide")
        return float(value)
    except (requests.RequestException, KeyError, IndexError, ValueError, TypeError) as exc:
        logger.warning(f"Pression historique indisponible : {exc}")
        return None


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
    

def get_computed_luminosity(
    latitude, longitude, timestamp, timezone, sky_condition=1
):
    """
    Estimation extérieure en lux selon Janiczek et DeYoung (1987).

    sky_condition :
        1 : ciel clair
        2 : nuages fins
        3 : nuages moyens
        10 : stratus sombres

    Retourne luminosity et luminosity_source, ou None en cas d'échec.
    """
    try:
        latitude = float(latitude)
        longitude = float(longitude)
        sky_condition = float(sky_condition)

        if not (
            math.isfinite(latitude)
            and math.isfinite(longitude)
            and math.isfinite(sky_condition)
            and -90 <= latitude <= 90
            and -180 <= longitude <= 180
            and sky_condition >= 1
        ):
            raise ValueError("Coordonnées ou coefficient de ciel invalides")

        date = datetime.fromisoformat(timestamp)
        zone = ZoneInfo(timezone)

        # Un timestamp sans décalage représente une heure locale.
        if date.tzinfo is None:
            date = date.replace(tzinfo=zone)

        date = date.astimezone(utc_timezone.utc)

        rad = math.pi / 180
        sin, cos = math.sin, math.cos

        # Nombre de jours depuis l'époque utilisée par le modèle.
        days = (
            367 * date.year
            - int(7 * (date.year + int((date.month + 9) / 12)) / 4)
            + int(275 * date.month / 9)
            + date.day
            - 730531
        )
        day_fraction = (
            date.hour * 3600 + date.minute * 60
            + date.second + date.microsecond / 1_000_000
        ) / 86400
        days = days - 0.5 + day_fraction

        lat = latitude * rad
        ce, se = 0.91775, 0.39715

        def altitude_and_atmosphere(right_ascension, declination):
            hour_angle = (sidereal_angle - right_ascension) * rad
            sine_altitude = (
                sin(declination) * sin(lat)
                + cos(declination) * cos(lat) * cos(hour_angle)
            )
            altitude = math.asin(
                max(-1, min(1, sine_altitude))
            ) / rad

            # Réfraction atmosphérique près de l'horizon.
            apparent = altitude
            if altitude >= -5 / 6:
                apparent += 1 / (
                    math.tan(
                        (altitude + 8.6 / (altitude + 4.42)) * rad
                    ) * 60
                )

            u = sin(apparent * rad)
            s = math.asin(
                753.66156 * cos(apparent * rad) / 754.66156
            )
            air_mass = 753.66156 * (cos(s) - u) + cos(s)

            transmission = (
                math.exp(-0.21 * air_mass) * u
                + 0.0289 * math.exp(-0.042 * air_mass)
                * (1 + (apparent + 90) * u * rad)
            )
            return altitude * rad, transmission

        # Soleil.
        mean_longitude = (280.46 + 0.98565 * days) % 360
        anomaly = (357.5 + 0.98560 * days) * rad
        solar_longitude = (
            mean_longitude + 1.91 * sin(anomaly)
        ) * rad

        solar_ra = math.atan2(
            ce * sin(solar_longitude), cos(solar_longitude)
        ) / rad
        solar_declination = math.asin(se * sin(solar_longitude))

        sidereal_angle = (
            mean_longitude - 180
            + 360 * day_fraction + longitude
        )
        _, solar_transmission = altitude_and_atmosphere(
            solar_ra, solar_declination
        )
        solar_lux = 133775 * solar_transmission

        # Lune.
        mean_moon = (218.32 + 13.1764 * days) % 360
        lunar_anomaly = (134.96 + 13.06499 * days) * rad
        lunar_argument = (93.27 + 13.22935 * days) * rad
        elongation = (235.7 + 24.38150 * days) * rad

        moon_longitude = (
            mean_moon
            + (6.29 - 1.27 * cos(elongation)
               + 0.43 * cos(lunar_anomaly)) * sin(lunar_anomaly)
            + (0.66 + 1.27 * cos(lunar_anomaly)) * sin(elongation)
            - 0.19 * sin(anomaly)
            - 0.23 * sin(lunar_argument) * cos(lunar_argument)
        ) * rad

        moon_latitude = (
            (5.13 - 0.17 * cos(elongation)) * sin(lunar_argument)
            + (0.56 * sin(lunar_anomaly)
               + 0.17 * sin(elongation)) * cos(lunar_argument)
        ) * rad

        cb, sb = cos(moon_latitude), sin(moon_latitude)
        moon_ra = math.atan2(
            ce * sin(moon_longitude) * cb - se * sb,
            cb * cos(moon_longitude),
        ) / rad
        moon_declination = math.asin(
            se * sin(moon_longitude) * cb + ce * sb
        )

        moon_altitude, moon_transmission = altitude_and_atmosphere(
            moon_ra, moon_declination
        )

        phase_angle = math.acos(max(-1, min(
            1, cos(moon_longitude - solar_longitude) * cb
        )))
        phase_term = math.tan(phase_angle / 2) ** 0.632
        phase = (
            (0.892 * math.exp(-3.343 / phase_term)
             if phase_term > 0 else 0)
            + 0.0344 * (
                sin(phase_angle) - phase_angle * cos(phase_angle)
            )
        )
        moon_lux = (
            0.418 * phase * moon_transmission
            / (1 - 0.005 * cos(phase_angle)
               - 0.03 * sin(moon_altitude))
        )

        lux = (solar_lux + moon_lux + 0.0005) / sky_condition

        if not math.isfinite(lux) or lux < 0:
            raise ValueError("Éclairement calculé invalide")

        return {
            "luminosity": float(lux),
            "luminosity_source": "computed_janiczek_deyoung",
        }

    except (ValueError, TypeError, OverflowError, LookupError) as exc:
        logger.warning(f"Fallback luminosité indisponible : {exc}")
        return {
            "luminosity": None,
            "luminosity_source": None,
        }
        
    luminosity = row.get("luminosity")
    luminosity_source = "sensor" if luminosity is not None else None

    if luminosity is None:
        light = get_computed_luminosity(
            latitude=row.get("latitude"),
            longitude=row.get("longitude"),
            timestamp=row.get("local_timestamp") or row.get("timestamp"),
            timezone=row.get("timezone"),
            sky_condition=1,
        )
        luminosity = light["luminosity"]
        luminosity_source = light["luminosity_source"]
    

def get_luminosity(lat, lng, timestamp, timezone):
    """
    Calcule les lux astronomiques corrigés par les nuages historiques.
    Retourne luminosity et luminosity_source, ou None en cas d'échec.
    """
    try:
        zone = ZoneInfo(timezone)
        date = datetime.fromisoformat(timestamp)
        date = (
            date.replace(tzinfo=zone)
            if date.tzinfo is None else date.astimezone(zone)
        )

        previous_hour = date.replace(minute=0, second=0, microsecond=0)
        weight = (date - previous_hour).total_seconds() / 3600
        next_hour = (
            previous_hour + timedelta(hours=1)
            if weight > 0 else previous_hour
        )

        response = requests.get(
            "https://archive-api.open-meteo.com/v1/archive",
            params={
                "latitude": lat,
                "longitude": lng,
                "timezone": timezone,
                "start_date": previous_hour.date().isoformat(),
                "end_date": next_hour.date().isoformat(),
                "hourly": "cloud_cover",
            },
            timeout=20,
        )
        response.raise_for_status()
        hourly = response.json()["hourly"]

        times = hourly["time"]
        before = times.index(previous_hour.strftime("%Y-%m-%dT%H:%M"))
        after = times.index(next_hour.strftime("%Y-%m-%dT%H:%M"))

        start = hourly["cloud_cover"][before]
        end = hourly["cloud_cover"][after]

        if any(
            not isinstance(v, (int, float))
            or isinstance(v, bool)
            or not math.isfinite(v)
            or not 0 <= v <= 100
            for v in (start, end)
        ):
            raise ValueError("Couverture nuageuse absente ou invalide")

        cloud_cover = start + weight * (end - start)

        # Coefficients empiriques à calibrer.
        divisor = 1 if cloud_cover < 30 else 2 if cloud_cover < 80 else 10

        light = get_computed_luminosity(
            lat, lng, date.isoformat(), timezone,
            sky_condition=1,
        )

        if light["luminosity"] is None:
            raise ValueError("Calcul astronomique indisponible")

        return {
            "luminosity": float(light["luminosity"] / divisor),
            "luminosity_source": (
                "computed_janiczek_deyoung_open_meteo_cloud_cover"
            ),
        }

    except (
        requests.RequestException,
        KeyError,
        IndexError,
        ValueError,
        TypeError,
        LookupError,
    ) as exc:
        logger.warning(f"Fallback luminosité indisponible : {exc}")
        return {
            "luminosity": None,
            "luminosity_source": None,
        }
