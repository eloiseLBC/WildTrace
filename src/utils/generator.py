import os
import json
import math
import random
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed


from .dataUtils import get_formatted_ddmmyyyy, is_night, get_season
from .geoUtils import (get_altitude, get_city_country, get_hemisphere, get_distance_from_equator,
                                get_coastline_distance, constants)
from .loggerUtils import logger, log_file

"""
TODO: Générer des fausses données pour ces clés
latitude	Numérique 
longitude	Numérique 
"""

def generate_timestamp():
    start = datetime(2027, 1, 1)
    end = datetime(2030, 1, 1)
    delta = end - start
    random_days = random.randint(0, delta.days - 1)
    random_seconds = random.randint(0, 86399)  # secondes dans une journée
    timestamp = start + timedelta(days=random_days, seconds=random_seconds)
    timestamp = timestamp.strftime("%d-%m-%Y %H:%M:%S.%f")
    return timestamp

def generate_temperature():
    temperature = random.randint(-50, 50)
    return temperature

def generate_humidity():
    humidity = random.randint(0, 100)
    return humidity

def generate_pression(altitude):
    pression = 1013.25 * (1 - (float(altitude) / float(44330))) ** 5.255
    return pression

def get_luminosity(hour, is_night, environment):
    """
    Simule une luminosité réaliste (en lux) selon l'heure.
    - hour : entre 0 et 23
    """
    rules = {
        "desert":       ((0.1, 5),      (60000, 188000)),
        "mountain":     ((0.1, 5),      (30000, 150000)),
        "jungle":       ((0.05, 1),     (50, 5000)),
        "field":        ((0.1, 5),      (10000, 90000)),
        "city":         ((5, 200),      (2000, 50000)),
        "village":      ((1, 50),       (1000, 30000)),
        "indoors":      ((1, 20),       (50, 1000)),
        "cloudy":       ((0.1, 1),      (1000, 10000))
    }

    min_lux, max_lux = rules.get(environment, ((1, 10), (100, 1000)))[0 if is_night else 1]

    # Ajoute une variation en sinusoïde douce en fonction de l'heure de jour
    if not is_night:
        light_factor = max(0, math.sin(math.pi * (hour - 6) / 12))  # 0 à 1 entre 6h et 18h
        base = min_lux + light_factor * (max_lux - min_lux)
        noise = random.uniform(-0.1, 0.1) * base
        luminosity = round(base + noise, 2)
        return luminosity
    else:
        luminosity = round(random.uniform(min_lux, max_lux), 2)
        return luminosity

def generate_environment():
    category = constants['environments']
    index = random.randint(0, len(category)-1)
    environment = category[index]
    return environment

def generate_co2(environment):
    co2_ranges_ppm = {
        "desert":       (380, 450),
        "mountain":     (370, 440),
        "jungle":       (390, 500),
        "field":        (390, 550),
        "city_dense":   (600, 900),
        "city_airy":    (450, 700),
        "village":      (400, 650),
        "indoors":      (450, 1500),
        "cloudy":       (400, 700)
    }
    co2_range = co2_ranges_ppm.get(environment, (400, 600))
    co2_concentration = random.randint(co2_range[0], co2_range[1])
    return co2_concentration

def generate_lat_lng(environment):
    lat_ranges = {
        "desert": (-30, 30),
        "mountain": (-50, 60),
        "jungle": (-15, 15),
        "field": (30, 50),
        "city_dense": (-40, 60),
        "city_airy": (-40, 60),
        "village": (-40, 60),
        "indoors": (-40, 60),
        "cloudy": (-60, 60)
    }

    lon_ranges = {
        "desert": (-20, 60),
        "mountain": (-130, 120),
        "jungle": (-80, 160),
        "field": (-100, 100),
        "city_dense": (-180, 180),
        "city_airy": (-180, 180),
        "village": (-180, 180),
        "indoors": (-180, 180),
        "cloudy": (-180, 180)
    }

    lat = round(random.uniform(*lat_ranges.get(environment, (-40, 60))), 6)
    lon = round(random.uniform(*lon_ranges.get(environment, (-180, 180))), 6)
    return lat, lon


def generate_computed(collected_files_data):
    try:
        # Initialisation des variables
        json_object = []
        timestamp_str = ""
        timestamp_utc = None
        environment = ""
        temperature = 0.0
        humidity = 0.0
        pression = 0.0
        luminosity = 0.0
        concentration_co2 = 0.0
        lat = 0.0
        lng = 0.0
        ultra_violet_index = 0

        # Récupération des données par capteurs
        for file in collected_files_data:
            for list_file in file:
                for k, v in list_file.items():
                    match k:
                        case "timestamp":
                            timestamp_str = v
                            timestamp_utc = datetime.strptime(timestamp_str, "%d-%m-%Y %H:%M:%S.%f").replace(tzinfo=timezone.utc)
                            timestamp_utc = timestamp_utc.strftime("%d-%m-%Y %H:%M:%S")
                            timestamp_utc = datetime.strptime(timestamp_utc, "%d-%m-%Y %H:%M:%S")
                        case "environment":
                            environment = v
                        case "temperature":
                            temperature = v
                        case "humidity":
                            humidity = v
                        case "pression":
                            pression = v
                        case "luminosity":
                            luminosity = v
                        case "concentration_co2":
                            concentration_co2= v
                        case "latitude":
                            lat = v
                        case "longitude":
                            lng = v
                        case "ultra_violet_index":
                            ultra_violet_index = v

                altitude = None

                while altitude is None:
                    altitude = get_altitude(lat, lng)

                row = {
                    "timestamp": timestamp_str,
                    "formatted_ddmmyyyy": get_formatted_ddmmyyyy(timestamp_str),
                    "latitude": lat,
                    "longitude": lng,
                    "temperature": temperature,
                    "humidity": humidity,
                    "pression": pression,
                    "luminosity": luminosity,
                    "concentration_co2": concentration_co2,
                    "environment": environment,
                    "ultra_violet_index": ultra_violet_index,
                    **get_city_country(lat, lng),
                    "altitude": altitude,
                    **get_distance_from_equator(lat),
                    **get_coastline_distance(lat, lng),
                    "hemisphere": get_hemisphere(lat),
                    "season": get_season(get_hemisphere(lat), get_formatted_ddmmyyyy(timestamp_str)),
                    "is_night": is_night(lat, lng, timestamp_utc)
                }

                logger.info(f"---------------Row générée --------------- : {row}")


                json_object.append(row)

        return json_object

    except Exception as e:
        logger.error(f"Erreur dans generate_computed : {e}", exc_info=True)
        raise

def generate_one_collected_row():
    try:
        # Récupération des données par capteurs
        timestamp_str = generate_timestamp()
        timestamp_utc = datetime.strptime(timestamp_str, "%d-%m-%Y %H:%M:%S.%f").replace(tzinfo=timezone.utc)
        timestamp_utc = timestamp_utc.strftime("%d-%m-%Y %H:%M:%S")
        timestamp_utc = datetime.strptime(timestamp_utc, "%d-%m-%Y %H:%M:%S")

        hour = timestamp_utc.hour
        environment = generate_environment()
        altitude = None

        while altitude is None:
            lat, lng = generate_lat_lng(environment)
            altitude = get_altitude(lat, lng)

        temperature = generate_temperature()
        humidity = generate_humidity()
        pression = generate_pression(altitude)
        luminosity = get_luminosity(hour, is_night(lat, lng, timestamp_utc), environment)
        concentration_co2 = generate_co2(environment)

        row = {
            "timestamp": timestamp_str,
            "formatted_ddmmyyyy": get_formatted_ddmmyyyy(timestamp_str),
            "latitude": lat,
            "longitude": lng,
            "temperature": temperature,
            "humidity": humidity,
            "pression": pression,
            "luminosity": luminosity,
            "concentration_co2": concentration_co2,
            "environment": environment,
            "ultra_violet_index": random.randint(0, 11),
            "altitude": altitude
        }

        return row

    except Exception as e:
        logger.error(f"Erreur dans generate_one_collected_row : {e}", exc_info=True)
        raise


def activate_generator(json_object, file):
    """
    Active le mode générateur de données.
    """
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Utilisation de ThreadPoolExecutor pour la génération parallèle
        collected_dir = f'./data/output/generated/environmental_to_send/collected/{file}'
        collected_files_data = []
        try:
            with open(collected_dir, 'r', encoding='utf-8') as f:
                data = json.load(f)  # load entire file into a Python object (dict)
                collected_files_data.append(data)
                logger.info(f"Loaded JSON file ` {file} ` with {('list' if isinstance(data, list) else 'object')}.")
        except Exception as ex:
            logger.error(f"Failed to load JSON file ` {file} `: {ex}", exc_info=True)
        json_object = generate_computed(collected_files_data)
        logger.info(f"Total de {len(json_object)} rows générées.")

        return json_object

def activate_generator_collected(json_object):
    """
    Active le mode générateur de données.
    """
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Utilisation de ThreadPoolExecutor pour la génération parallèle
        # Warning : le nombre d'objets générés est à 2 pour tester
        futures = [executor.submit(generate_one_collected_row) for _ in range(2)]
        for future in as_completed(futures):
            row = future.result()
            if row:
                json_object.append(row)
                logger.info(f"Row générée : {row}")
        return json_object