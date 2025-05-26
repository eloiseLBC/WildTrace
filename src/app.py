from utils.writeUtils import write_json, write_log_drive, find_folder_id
from utils.dataUtils import get_season, get_formatted_ddmmyyyy, is_night
from utils.geoUtils import get_city_country, get_altitude, get_distance_from_equator, \
    get_coastline_distance, get_hemisphere
import pandas as pd
from datetime import datetime, timezone
from utils.loggerUtils import logger, timestamp_str
from utils.generator import generate_timestamp, generate_temperature, generate_humidity, generate_pression, \
    get_luminosity, generate_environment, generate_co2, generate_lat_lng
from memory_profiler import profile
from pyspark.sql import SparkSession


df = pd.DataFrame()

@profile
def job():
    if __name__ == "__main__":
        logger.info("----- Application en cours de développement -----")
        spark = SparkSession.builder \
            .appName("DataGenerationTest") \
            .master("local[*]") \
            .getOrCreate()

        df = spark.range(0, 10).toDF("id")
        df.show()
        #logger.info("----- Partie data generator -----")
        #json_object = []
        #timestamp_begin_job = datetime.now().strftime("%d-%m-%Y %H:%M:%S.%f")
        #logger.info(f"Début du job : {timestamp_begin_job}")
        #try:
        #    for _ in range(10):
        #        timestamp_str = generate_timestamp()
        #        altitude = None
        #        timestamp_utc = datetime.strptime(str(timestamp_str), "%d-%m-%Y %H:%M:%S.%f").replace(tzinfo=timezone.utc)
        #        hour = timestamp_utc.hour
        #        environment = generate_environment()
        #        while altitude is None:
        #            lat, lng = generate_lat_lng(environment)
        #            altitude = get_altitude(lat, lng)
        #        temperature = generate_temperature()
        #        humidity = generate_humidity()
        #        pression = generate_pression(altitude)
        #        environment = generate_environment()
        #        luminosity = get_luminosity(hour, is_night, environment)
        #        concentration_co2 = generate_co2(environment)

        #        try:
        #            row = {
        #                "timestamp": timestamp_str,
        #                "formatted_ddmmyyyy" : get_formatted_ddmmyyyy(timestamp_str),
        #                "latitude": lat,
        #                "longitude": lng,
        #                "temperature": temperature,
        #                "humidity" : humidity,
        #                "pression" : pression,
        #                "luminosity" : luminosity,
        #                "concentration_co2": concentration_co2,
        #                "environment" : environment,
        #                **get_city_country(lat, lng),
        #                "altitude": altitude,
        #                **get_distance_from_equator(lat),
        #                **get_coastline_distance(lat, lng),
        #                "hemisphere": get_hemisphere(lat),
        #                "season": get_season("sud", get_formatted_ddmmyyyy(timestamp_str)),
        #                "is_night": is_night(lat, lng, timestamp_utc)
        #            }
        #            logger.info(row)
        #            json_object.append(row)

        #        except Exception as e:
        #            logger.error(f"Erreur programme principal : {e}")
        #except Exception as e:
        #    logger.error(f"Erreur : {e}")
        #finally:
            #write_log_drive()
        #    duree = datetime.strptime(datetime.now().strftime("%d-%m-%Y %H:%M:%S.%f"), "%d-%m-%Y %H:%M:%S.%f") - datetime.strptime(timestamp_begin_job, "%d-%m-%Y %H:%M:%S.%f")
        #    logger.info(f"Durée du programme : {duree} ")

        #write_json(json_object, timestamp_str)
        #df = pd.DataFrame([json_object])

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

job()





