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
        "stress_status": "insufficient_data"
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

    try:
        date = datetime.strptime(biological_data["date"], "%Y-%m-%d")
    except (KeyError, ValueError, TypeError):
        logger.warning("Date biologique absente ou invalide.")
        return result

    if get_biological_day is None:
        return result

    historical_hrv = []

    # Uniquement les jours précédents : exclure le jour calculé.
    first_watch_date = datetime(2026, 2, 1).date()

    for offset in range(1, 29):
        previous_day = (date - timedelta(days=offset)).date()

        if previous_day < first_watch_date:
            break

        previous_date = previous_day.isoformat()
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

    # Au moins 14 jours valides sur les 28 précédents.
    if len(historical_hrv) >= 14:
        baseline = median(historical_hrv)
        result["hrv_baseline_ms"] = round(baseline, 2)

        if valid_number(current_hrv) and current_hrv > 0:
            change = (current_hrv - baseline) / baseline * 100

            result["hrv_change_percent"] = round(change, 1)

            # Indicateur expérimental : baisse relative de HRV.
            # Zéro signifie aucune baisse détectée, pas absence de stress.
            result["stress_score"] = round(
                min(100, max(0, -change)), 1
            )
            result["stress_status"] = "estimated"
        else:
            result["stress_status"] = "missing_current_hrv"

    return result

from .gpsUtils import resolve_gps


def compute_data(data, get_biological_day=None, get_previous_files=None, source_file=None):
    # Initialisation des variables
    json_object = []
    matched_days = set()
    missing_days = set()
    try:
        for row in data:
            row = dict(row)
            for field in ("temperature", "humidity", "luminosity", "concentration_co2"):
                row.setdefault(field, None)
            white_luminosity = row.get("white_luminosity")
            # Les valeurs et les sources appartiennent à une mesure, pas au fichier.
            reconstructed = bool(row.get("reconstruction"))
            lat_source = lng_source = altitude_source = "computed" if reconstructed else "sensor"
            temperature_source = humidity_source = concentration_co2_source = "sensor"
            luminosity_source = "sensor"
            moods = row.get("moods", [])
            environments = row.get("environments", [])
            timezone_input = row.get("timezone")
            timestamp_str = row.get("local_timestamp") or row.get("timestamp")
            if not timestamp_str:
                logger.warning("Timestamp absent : fichier conservé dans to_compute.")
                return ""
            try:
                timestamp_utc = datetime.fromisoformat(timestamp_str)
            except ValueError:
                timestamp_utc = datetime.strptime(timestamp_str, "%d-%m-%Y %H:%M:%S")
            if timestamp_utc.tzinfo is not None and timezone_input:
                timestamp_utc = timestamp_utc.astimezone(ZoneInfo(timezone_input))
            lat = row.get("latitude")
            lng = row.get("longitude")
            altitude = row.get("altitude")
            if altitude is None:
                altitude = row.get("altitude_m")

            
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
                        day = date.date().isoformat()
                        biological_data = get_biological_day(day)
                        if (not isinstance(biological_data, dict)
                                or biological_data.get("date") != day):
                            biological_data = None
                            if day not in missing_days:
                                logger.warning(
                                    f"Aucun fichier biologique pour la date {day} "
                                    f"du fichier environnemental {source_file or '(source en mémoire)'}."
                                )
                                missing_days.add(day)
                        elif day not in matched_days:
                            logger.info(
                                f"Correspondance biologique pour la date {day} du fichier "
                                f"environnemental {source_file or '(source en mémoire)'} : "
                                f"collected/computed/biological_daily_{day}.json"
                            )
                            matched_days.add(day)
                except (ValueError, TypeError, LookupError) as exc:
                    logger.warning(f"Recherche biologique impossible : {exc}")

                return biological_data

            position = resolve_gps(
                row, get_previous_files or (lambda: []), load_biological_day
            )
            if position is None:
                return ""
            lat, lng = position["latitude"], position["longitude"]
            lat_source = "sensor" if not reconstructed and lat == row.get("latitude") else "computed"
            lng_source = "sensor" if not reconstructed and lng == row.get("longitude") else "computed"
            if altitude is None:
                altitude = position.get("altitude")
                if altitude is None:
                    altitude = get_altitude(lat, lng)
                altitude_source = "computed"
            # Résoudre les coordonnées avant les appels météo, quel que soit
            # l'ordre des clés du JSON.
            if row.get("temperature") is None or row.get("humidity") is None:
                temperature_api, temperature_source_api, humidity_api, humidity_source_api = (
                    get_temperature_humidity(lat, lng, timestamp_str, timezone_input)
                    or (None, None, None, None)
                )
            for k, v in row.items():
                match k:
                    case "temperature":
                        if v is not None:
                            temperature = v
                        else:
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
                            concentration_co2_api, concentration_co2_source_api = (
                                get_co2(lat, lng, timestamp_str, timezone_input)
                                or (None, None)
                            )
                            concentration_co2 = concentration_co2_api
                            concentration_co2_source = concentration_co2_source_api

                    case "moods":
                        moods = v

                    case "environments":
                        environments = v

            logger.info(f"Timestamp str : {timestamp_str}")
            if timestamp_str == "" or timestamp_str == None:
                return ""

            if any(value is None for value in (lat, lng, altitude, temperature, humidity, concentration_co2, luminosity,)):
                if not reconstructed:
                    logger.warning(
                        "Donnée manquante après fallback. "
                        "Le fichier reste dans collected/to_compute."
                    )
                    return ""
                logger.warning(
                    f"Reconstruction partielle pour {timestamp_str} : "
                    "les données indisponibles restent à null."
                )
            
            # Charger le fichier même si les coordonnées capteur sont présentes.
            biological_data = load_biological_day()
            biological_metrics = compute_biological_data(
                biological_data, get_biological_day
            )
    
            formatted_ddmmyyyy = timestamp_utc.date().isoformat()
            row = {
                "timestamp": timestamp_str,
                "timezone": timezone_input,
                "formatted_ddmmyyyy": formatted_ddmmyyyy,
                "gps_coordinates": position["gps_coordinates"],
                "latitude": lat,
                "latitude_source": lat_source,
                "longitude": lng,
                "longitude_source": lng_source,
                "temperature": temperature,
                "temperature_source": temperature_source,
                "humidity": humidity,
                "humidity_source": humidity_source,
                "pressure": get_pressure(
                    lat, lng, formatted_ddmmyyyy, timestamp_utc.hour,
                    timezone_name=timezone_input or "UTC",
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

            if reconstructed:
                row["reconstruction"] = data[len(json_object)]["reconstruction"]
                row["biological"]["summary"] = (biological_data or {}).get("summary", {})
                location = (biological_data or {}).get("city_country") or {}
                for field in ("city", "country", "formatted_address", "aquatic_location"):
                    if field in location:
                        row[field] = location[field]
            logger.info(f"Computed row: {row}")
            json_object.append(row)

        for day in sorted(matched_days):
            logger.info(
                f"Date {day} retrouvée dans le fichier biologique "
                f"collected/computed/biological_daily_{day}.json "
                f"pour le fichier environnemental {source_file or '(source en mémoire)'} ; "
                "données biologiques utilisées pour le calcul."
            )
        return json_object

    except Exception as e:
        logger.error(f"Erreur dans compute_data : {e}", exc_info=True)
        raise
    
