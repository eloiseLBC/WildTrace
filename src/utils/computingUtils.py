import sys
import os
import json
import math
import random
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from statistics import median



sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from utils.loggerUtils import logger, log_file
from .dataUtils import get_formatted_ddmmyyyy, is_night, get_season
from .geoUtils import (get_altitude, get_city_country, get_hemisphere, get_distance_from_equator,
                                get_coastline_distance, constants, get_pressure, get_temperature_humidity,
                                get_co2, get_luminosity, get_location_coordinates)

def compute_biological_data(biological_data, get_biological_day):
    """Calcule des indicateurs personnels à partir du résumé biologique."""
    result = {
        "sleep_duration_score": None,
        "sleep_score_source": "duration_ratio_v1",
        "hrv_baseline_ms": None,
        "hrv_baseline_days": 0,
        "hrv_change_percent": None,
        "stress_score": None,
        "stress_status": "insufficient_data",
    }

    def valid_number(value):
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
        )

    if not isinstance(biological_data, dict):
        return result

    summary = biological_data.get("summary")
    if not isinstance(summary, dict):
        return result

    # Zéro reste indéterminé : sommeil absent ou non enregistré.
    sleep_hours = summary.get("sleep_duration_hours")
    if valid_number(sleep_hours) and 0 < sleep_hours <= 24:
        result["sleep_duration_score"] = round(
            min(sleep_hours / 8, 1) * 100, 1
        )

    current_hrv = summary.get("hrv_avg_ms")
    if not valid_number(current_hrv) or current_hrv <= 0:
        return result

    try:
        date = datetime.strptime(biological_data["date"], "%Y-%m-%d")
    except (KeyError, ValueError, TypeError):
        logger.warning("Date biologique absente ou invalide.")
        return result

    if get_biological_day is None:
        return result

    historical_hrv = []

    # Uniquement les jours précédents : exclure le jour calculé.
    for offset in range(1, 29):
        previous_date = (date - timedelta(days=offset)).date().isoformat()
        previous = get_biological_day(previous_date)

        if not isinstance(previous, dict):
            continue

        # Ne pas utiliser un fichier attribué à une autre journée.
        if previous.get("date") != previous_date:
            continue

        previous_summary = previous.get("summary")
        if not isinstance(previous_summary, dict):
            continue

        value = previous_summary.get("hrv_avg_ms")
        if valid_number(value) and value > 0:
            historical_hrv.append(value)

    result["hrv_baseline_days"] = len(historical_hrv)

    # Choix applicatif : au moins 14 jours valides sur les 28 précédents.
    if len(historical_hrv) >= 14:
        baseline = median(historical_hrv)
        result["hrv_baseline_ms"] = round(baseline, 2)
        result["hrv_change_percent"] = round(
            (current_hrv - baseline) / baseline * 100, 1
        )
        result["stress_status"] = "not_calibrated"

    return result

def compute_data(data, get_biological_day=None):
    # Initialisation des variables
    json_object = []
    timestamp_str = ""
    timestamp_utc = None
    timezone_input = None
    temperature = 0.0
    temperature_source = "sensor"
    humidity = 0.0
    humidity_source = "sensor"
    luminosity = None
    luminosity_source = "sensor"
    white_luminosity = 0.0
    concentration_co2 = 0.0
    concentration_co2_source = "sensor"
    lat = 0.0
    lng = 0.0
    lat_source = "sensor"
    lng_source = "sensor"
    altitude_source = "sensor"
    altitude = None
    moods = []
    enviroments = []
    position = None
        
    try:
        for row in data:
            lat = row.get("latitude")
            lng = row.get("longitude")
            altitude = row.get("altitude")
            if altitude is None:
                altitude = row.get("altitude_m")

            address = None
            position = None
            
            logger.info(f"Data : {data}")

            biological_data = None
            biological_checked = False

            def load_biological_day():
                nonlocal biological_data, biological_checked

                if biological_checked:
                    return biological_data

                biological_checked = True
                timestamp = row.get("local_timestamp") or row.get("timestamp")

                try:
                    try:
                        date = datetime.fromisoformat(timestamp)
                    except ValueError:
                        date = datetime.strptime(
                            timestamp, "%d-%m-%Y %H:%M:%S"
                        )

                    if date.tzinfo is not None and row.get("timezone"):
                        date = date.astimezone(ZoneInfo(row["timezone"]))

                    if get_biological_day is not None:
                        biological_data = get_biological_day(
                            date.date().isoformat()
                        )
                except (ValueError, TypeError, LookupError) as exc:
                    logger.warning(f"Recherche biologique impossible : {exc}")

                return biological_data

            for k, v in row.items():
                match k:
                    case "timestamp":
                        timestamp_str = v
                        timestamp_utc = datetime.strptime(timestamp_str, "%d-%m-%Y %H:%M:%S").replace(tzinfo=timezone.utc)
                        timestamp_utc = timestamp_utc.strftime("%d-%m-%Y %H:%M:%S")
                        timestamp_utc = datetime.strptime(timestamp_utc, "%d-%m-%Y %H:%M:%S")

                    case "local_timestamp":
                        timestamp_str = v
                        if timestamp_str != None:
                            timestamp_utc = datetime.strptime(
                                timestamp_str, "%Y-%m-%d %H:%M:%S"
                            ).replace(tzinfo=timezone.utc)
                            timestamp_utc = timestamp_utc.strftime(
                                "%d-%m-%Y %H:%M:%S"
                            )
                            timestamp_utc = datetime.strptime(timestamp_utc, "%d-%m-%Y %H:%M:%S")

                    case "timezone":
                        timezone_input = v

                    case "temperature":
                        if v is not None:
                            temperature = v
                        else:
                            (temperature_api ,temperature_source_api , humidity_api, humidity_source_api,) = get_temperature_humidity(lat, lng, timestamp_str, timezone_input)
                            temperature = temperature_api
                            temperature_source = temperature_source_api

                    case "humidity":
                        if v is not None:
                            humidity = v
                        else:
                            humidity = humidity_api
                            humidity_source = humidity_source_api

                    case "luminosity":
                        if v is None:
                            logger.warning("Calcul de la luminosité, capteur défaillant.")
                            light = get_luminosity(lat, lng, timestamp_str, timezone_input)
                            luminosity = light["luminosity"]
                            luminosity_source = light["luminosity_source"]
                        else:
                            luminosity = v

                    case "white_luminosity":
                        white_luminosity = v

                    case "concentration_co2":
                        if v is not None:
                            concentration_co2 = v
                        else:
                            (concentration_co2_api, concentration_co2_source_api) = get_co2(lat, lng, timestamp_str, timezone_input)
                            concentration_co2 = concentration_co2_api
                            concentration_co2_source = concentration_co2_source_api

                    case "latitude":
                        if v is not None:
                            lat = v
                        else:
                            logger.info("Latitude nulle -> Calcul de la donnée")
                            biological_data = load_biological_day()

                            address = (
                                (biological_data or {})
                                .get("city_country", {})
                                .get("formatted_address")
                            )
                            
                            logger.info(f"Address : {address}")

                            if address:
                                position = get_location_coordinates(address)
                                lat = position["latitude"]
                                lat_source = "computed"
                            else:
                                logger.warning(
                                    "Adresse absente du fichier biologique."
                                )

                    case "longitude":
                        if v is not None:
                            lng = v
                        else:
                            logger.info("Longitude nulle -> Calcul de la donnée")
                            if address:
                                lng = position["longitude"]
                                lng_source = "computed"
                            else:
                                logger.warning("Adresse absente du fichier biologique.")

                    case "altitude":
                        if v is not None:
                            altitude = v
                        else:
                            logger.info("Altitude nulle -> Calcul de la donnée")
                            if row.get("altitude_m") is None:
                                if address:
                                    altitude = position["altitude"]
                                    altitude_source = "computed"
                                else:
                                    logger.warning("Adresse absente du fichier biologique.")
                                                                    
                    case "altitude_m":
                        if v is not None:
                            altitude = v
                        else:
                            logger.info("Altitude_m nulle")
                            if row.get("altitude") is None:
                                if address:
                                    altitude = position["altitude"]
                                else:
                                    logger.warning("Adresse absente du fichier biologique.")
                                                               
                    case "moods":
                        moods = v

                    case "environments":
                        environments = v

            logger.info(f"Timestamp str : {timestamp_str}")
            if timestamp_str == "" or timestamp_str == None:
                return ""

            if any(value is None for value in (lat, lng, altitude, temperature, humidity, concentration_co2, luminosity,)):
                logger.warning(
                    "Donnée manquante après fallback. "
                    "Le fichier reste dans collected/to_compute."
                )
                return ""
            
            # Charger le fichier même si les coordonnées capteur sont présentes.
            biological_data = load_biological_day()
            biological_metrics = compute_biological_data(
                biological_data, get_biological_day
            )
            
            formatted_ddmmyyyy = get_formatted_ddmmyyyy(timestamp_str)
            row = {
                "timestamp": timestamp_str,
                "timezone": timezone_input,
                "formatted_ddmmyyyy": formatted_ddmmyyyy,
                "latitude": lat,
                "latitude_source": lat_source,
                "longitude": lng,
                "longitude_source": lng_source,
                "temperature": temperature,
                "temperature_source": temperature_source,
                "humidity": humidity,
                "humidity_source": humidity_source,
                "pressure": get_pressure(
                    lat, lng, formatted_ddmmyyyy, timestamp_utc.hour
                ),
                "luminosity": luminosity,
                "luminosity_source": luminosity_source,
                "white_luminosity": white_luminosity,
                "concentration_co2": concentration_co2,
                "concentration_co2_source": concentration_co2_source,
                **get_city_country(lat, lng),
                "altitude": altitude,
                "altitude_source": altitude_source,
                **get_distance_from_equator(lat),
                **get_coastline_distance(lat, lng),
                "hemisphere": get_hemisphere(lat),
                "season": get_season(
                    get_hemisphere(lat), formatted_ddmmyyyy
                ),
                "is_night": is_night(lat, lng, timestamp_utc),
                "moods": moods,
                "environments": environments,
                "biological": {
                    "date": (
                        biological_data.get("date")
                        if isinstance(biological_data, dict) else None
                    ),
                    "source": "wildtrace-biological",
                    **biological_metrics,
                },
            }

            logger.info(f"--------------- Computed row --------------- : \n{row}")
            json_object.append(row)

        return json_object

    except Exception as e:
        logger.error(f"Erreur dans compute_data : {e}", exc_info=True)
        raise
    