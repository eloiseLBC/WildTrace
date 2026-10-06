import sys
import os
import json
import math
import random
from datetime import datetime, timedelta, timezone

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from utils.loggerUtils import logger, log_file
from .dataUtils import get_formatted_ddmmyyyy, is_night, get_season
from .geoUtils import (get_altitude, get_city_country, get_hemisphere, get_distance_from_equator,
                                get_coastline_distance, constants, get_pressure)

def compute_data(data):
    # Initialisation des variables
    json_object = []
    timestamp_str = ""
    timestamp_utc = None
    temperature = 0.0
    humidity = 0.0
    luminosity = 0.0
    white_luminosity = 0.0
    concentration_co2 = 0.0
    lat = 0.0
    lng = 0.0
    moods = []
    enviroments = []
        
    try:
        for row in data:
            logger.info(f"Data : {data}")
            logger.info(f"Row : {row}")
            logger.info(f"Row items : {row.items()}")
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
                            timestamp_utc = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                            timestamp_utc = timestamp_utc.strftime("%d-%m-%Y %H:%M:%S")
                            timestamp_utc = datetime.strptime(timestamp_utc, "%d-%m-%Y %H:%M:%S")
                    case "temperature":
                        temperature = v
                    case "humidity":
                        humidity = v
                    case "luminosity":
                        luminosity = v
                    case "white_luminosity":
                        white_luminosity = v
                    case "concentration_co2":
                        concentration_co2 = v
                    case "latitude":
                        lat = v
                    case "longitude":
                        lng = v
                    case "altitude":
                        altitude = v
                    case "altitude_m":
                        altitude = v
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
                    "formatted_ddmmyyyy": formatted_ddmmyyyy,
                    "latitude": lat,
                    "longitude": lng,
                    "temperature": temperature,
                    "humidity": humidity,
                    "pressure": get_pressure(lat, lng, formatted_ddmmyyyy, timestamp_utc.hour),
                    "luminosity": luminosity,
                    "white_luminosity": white_luminosity,
                    "concentration_co2": concentration_co2,
                    # "environment": environment,
                    **get_city_country(lat, lng),
                    "altitude": altitude,
                    **get_distance_from_equator(lat),
                    **get_coastline_distance(lat, lng),
                    "hemisphere": get_hemisphere(lat),
                    "season": get_season(get_hemisphere(lat), formatted_ddmmyyyy),
                    "is_night": is_night(lat, lng, timestamp_utc),
                    "moods": moods,
                    "environments": environments
                    }

            logger.info(f"--------------- Computed row --------------- : \n{row}")
            json_object.append(row)
            
        return json_object
    except Exception as e:
        logger.error(f"Erreur dans compute_data : {e}", exc_info=True)
        raise
    