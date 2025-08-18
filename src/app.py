import pandas as pd
import optparse

from utils.sparkUtils import create_spark_session
from utils.writeUtils import write_json, write_log_drive, find_folder_id
from utils.dataUtils import get_season, get_formatted_ddmmyyyy, is_night
from utils.geoUtils import get_city_country, get_altitude, get_distance_from_equator, \
    get_coastline_distance, get_hemisphere
from datetime import datetime, timezone
from utils.loggerUtils import logger, timestamp_str
from utils.generator import generate_timestamp, generate_temperature, generate_humidity, generate_pression, \
    get_luminosity, generate_environment, generate_co2, generate_lat_lng
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


if __name__ == "__main__":
    logger.info("----- Application en cours de développement -----")


    parser = optparse.OptionParser()

    # add options
    parser.add_option("-g", "--generator",
                      dest="generator",
                      action="store_true",
                      default=False,
                      help="Activate the data generator mode")

    (options, args) = parser.parse_args()

    if options.generator:
        print("Mode générateur activé")
        print(f"Options: {options}")
    else:
        print("Mode normal (générateur non activé)")
        exit(0)



    json_object = []
    timestamp_begin_job = datetime.now()

    try:
        logger.info("----- Partie data generator -----")
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Utilisation de ThreadPoolExecutor pour la génération parallèle
            # Warning : le nombre d'objets générés est à 2 pour tester
            futures = [executor.submit(generate_one_row) for _ in range(2)]
            for future in as_completed(futures):
                row = future.result()
                if row:
                    json_object.append(row)
                    logger.info(f"Row générée : {row}")

        # Créer la session Spark avec la configuration appropriée
        spark = create_spark_session()

        # Test simple avec Spark pour vérifier que ça fonctionne
        if json_object and spark is not None:
            logger.info("----- Test Spark DataFrame -----")
            try:
                spark_df = spark.createDataFrame(json_object)
                logger.info(f"DataFrame Spark créé avec {spark_df.count()} lignes")
                spark_df.printSchema()
                spark_df.show(truncate=False)
            except Exception as e:
                logger.error(f"Erreur avec Spark DataFrame : {e}")
                logger.info("Utilisation de Pandas à la place")
                df = pd.DataFrame(json_object)
                logger.info(f"DataFrame Pandas créé avec {len(df)} lignes")
                print(df.head())
        elif json_object:
            logger.info("----- Utilisation de Pandas (Spark non disponible) -----")
            df = pd.DataFrame(json_object)
            logger.info(f"DataFrame Pandas créé avec {len(df)} lignes")
            print(df.head())

    except Exception as e:
        logger.error(f"Erreur générale : {e}")

    finally:
        duree = datetime.now() - timestamp_begin_job
        logger.info(f"Durée du programme : {duree}")

        # Fermer la session Spark
        if 'spark' in locals() and spark is not None:
            spark.stop()
            logger.info("Session Spark fermée")

        write_log_drive()

        if json_object:
            write_json(json_object, timestamp_str)