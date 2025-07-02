from utils.writeUtils import write_json, write_log_drive, find_folder_id
from utils.dataUtils import get_season, get_formatted_ddmmyyyy, is_night
from utils.geoUtils import get_city_country, get_altitude, get_distance_from_equator, \
    get_coastline_distance, get_hemisphere
import pandas as pd
from datetime import datetime, timezone
from utils.loggerUtils import logger, timestamp_str
from utils.generator import generate_timestamp, generate_temperature, generate_humidity, generate_pression, \
    get_luminosity, generate_environment, generate_co2, generate_lat_lng
from pyspark.sql import SparkSession
from concurrent.futures import ThreadPoolExecutor, as_completed


df = pd.DataFrame()

def generate_one_row():
    try:
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
        logger.info(f"type de utc : {type(timestamp_utc)}")
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
            **get_city_country(lat, lng),
            "altitude": altitude,
            **get_distance_from_equator(lat),
            **get_coastline_distance(lat, lng),
            "hemisphere": get_hemisphere(lat),
            "season": get_season(get_hemisphere(lat), get_formatted_ddmmyyyy(timestamp_str)),
            "is_night": is_night(lat, lng, timestamp_utc)
        }

        return row

    except Exception as e:
        logger.error(f"Erreur dans generate_one_row : {e}", exc_info=True)
        raise
        return None
        """
        try:
            logger.info("----- Partie data processing, storage, analyse  : je sais pas trop quoi mettre comme titre-----")
            lat, lng = 48.872997, 2.348728
            timestamp_utc = datetime.strptime(timestamp_str, "%d-%m-%Y %H:%M:%S.%f").replace(tzinfo=timezone.utc)
    
            row = {
                "timestamp": timestamp_str,
                "formatted_ddmmyyyy" : get_formatted_ddmmyyyy(timestamp_str),
                "latitude": lat,
                "longitude": lng,
                **get_city_country(lat, lng),
                "altitude": get_altitude(lat, lng),
                **get_distance_from_equator(lat),
                **get_coastline_distance(lat, lng),
               "hemisphere": get_hemisphere(lat),
                "season": get_season("sud", get_formatted_ddmmyyyy(timestamp_str)),
                "is_night": is_night(lat, lng, timestamp_utc)
            }
            logger.info(row)
    
            write_json(row, timestamp_str)
    
            df = pd.DataFrame([row])
        except Exception as e:
            logger.error(f"Erreur programme principal : {e}")
        finally:
            write_log_drive()
        """


if __name__ == "__main__":
    logger.info("----- Application en cours de développement -----")
    spark = SparkSession.builder \
        .appName("DataGenerationTest") \
        .master("local[*]") \
        .getOrCreate()

    json_object = []
    timestamp_begin_job = datetime.now()

    try:
        logger.info("----- Partie data generator -----")
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Utilisation de ThreadPoolExecutor pour la génération parallèle
            # Warning : le nombre d'objets générés est à 1 car je veux tester le cloud pour la generation de credentials
            futures = [executor.submit(generate_one_row) for _ in range(1)]  # ← 100 objets par exemple
            for future in as_completed(futures):
                row = future.result()
                if row:
                    json_object.append(row)
                    logger.info(f"Row générée : {row}")

    except Exception as e:
        logger.error(f"Erreur générale : {e}")

    finally:
        duree = datetime.now() - timestamp_begin_job
        logger.info(f"Durée du programme : {duree}")
        write_log_drive()

        if json_object:
            timestamp_str = datetime.strptime(timestamp_str, "%d-%m-%Y %H:%M:%S")
            write_json(json_object, timestamp_str)

