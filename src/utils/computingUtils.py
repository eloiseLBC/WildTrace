import sys
import os
import json
import math
import random
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from utils.loggerUtils import logger, log_file
from .dataUtils import get_formatted_ddmmyyyy, is_night, get_season
from .geoUtils import (get_altitude, get_city_country, get_hemisphere, get_distance_from_equator,
                                get_coastline_distance, constants, get_pressure, get_temperature_humidity,
                                get_co2, get_luminosity, get_location_coordinates)

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
    altitude = None
    moods = []
    enviroments = []
    position = None
        
    try:
        for row in data:
            logger.info(f"Data : {data}")
            logger.info(f"Data type : {type(data)}")
            logger.info(f"Data first row : {data[0]}")

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
                            (concentration_co2_api, concentration_co2_source_api,) = get_co2(lat, lng, timestamp_str, timezone_input)
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

            formatted_ddmmyyyy = get_formatted_ddmmyyyy(timestamp_str)
            row = {
                "timestamp": timestamp_str,
                "timezone": timezone_input,
                "formatted_ddmmyyyy": formatted_ddmmyyyy,
                "latitude": lat,
                "longitude": lng,
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
                **get_distance_from_equator(lat),
                **get_coastline_distance(lat, lng),
                "hemisphere": get_hemisphere(lat),
                "season": get_season(
                    get_hemisphere(lat), formatted_ddmmyyyy
                ),
                "is_night": is_night(lat, lng, timestamp_utc),
                "moods": moods,
                "environments": environments,
            }

            logger.info(f"--------------- Computed row --------------- : \n{row}")
            json_object.append(row)

        return json_object

    except Exception as e:
        logger.error(f"Erreur dans compute_data : {e}", exc_info=True)
        raise
    