import pandas as pd
import optparse
import os

from utils.collector import get_humidity_temperature
from storage.sendOracle import upload_to_bucket
from utils.generator import activate_generator, activate_generator_collected
#from utils.sparkUtils import create_spark_session
from utils.writeUtils import write_json
from datetime import datetime
from utils.loggerUtils import logger, timestamp_str


df = pd.DataFrame()


if __name__ == "__main__":
    logger.info("----- Application en cours de développement -----")

    parser = optparse.OptionParser()

    # add options
    parser.add_option("-g", "--generator-computed",
                      dest="generator_computed",
                      action="store_true",
                      default=False,
                      help="Activate the data generator mode (default: False)")
    parser.add_option("--generator-collected",
                      dest="generator_collected",
                      default=False,
                      help="Generate data as collected data only.\n On other hand, -g option allows to generate complete test data, after collecting and computing.\n (default: False)")
    parser.add_option("-s", "--spark",
                      dest="spark",
                      action="store_true",
                      default=False,
                      help="Launch Spark session (default: False)")
    parser.add_option("-b", "--bucket",
                      dest="bucket",
                      default=False,
                      help="Upload generated files to Oracle Cloud bucket (default: False)")


    (options, args) = parser.parse_args()

    timestamp_begin_job = datetime.now()
    json_object = []

    try:
        if options.generator_computed:
            logger.info("----- Partie data generator : computed -----")
            try:
                collected_dir = './data/output/generated/environmental_to_send/collected/'
                collected_files_data = []
                if os.path.isdir(collected_dir):
                    for file in os.listdir(collected_dir):
                        if file.endswith('.json'):
                            logger.info(f"file found: {file}")
                            path = os.path.join(collected_dir, file)
                            logger.info(f"JSON object passé au generator: {json_object}")
                            json_object = activate_generator(json_object, file)
                            if options.spark:
                                ## Créer la session Spark avec la configuration appropriée
                                #spark = create_spark_session()

                                # Test simple avec Spark pour vérifier que ça fonctionne
                                #if json_object and spark is not None:
                                #    logger.info("----- Test Spark DataFrame -----")
                                #    try:
                                #        spark_df = spark.createDataFrame(json_object)
                                #        logger.info(f"DataFrame Spark créé avec {spark_df.count()} lignes")
                                #        spark_df.printSchema()
                                #        spark_df.show(truncate=False)
                                #    except Exception as e:
                                #        logger.error(f"Erreur avec Spark DataFrame : {e}")
                                logger.warn("Pas de lancement avec spark pour le moment. Installation non surportée par le RaspeberryPi, et non nécessaire actuellement.")
                            else:
                                logger.info("----- Utilisation de Pandas (Spark non disponible) -----")
                                df = pd.DataFrame(json_object)
                                logger.info(f"DataFrame Pandas créé avec {len(df)} lignes")
                                print(df.head())
                                logger.info("----- Écriture des données générées au format JSON -----")
                                write_json(json_object, timestamp_str, options, file)

            except Exception as e:
                logger.error(f"Erreur data generator : {e}")
        elif options.generator_collected:
            logger.info("----- Partie data generator : collected -----")
            try:
                json_object = activate_generator_collected(json_object)
                df = pd.DataFrame(json_object)
                logger.info(f"DataFrame Pandas créé avec {len(df)} lignes")
                print(df.head())

            except Exception as e:
                logger.error(f"Erreur data generator : {e}")

        else:
            print("Mode normal (générateur non activé)")
            get_humidity_temperature()
            exit(0)

    except Exception as e:
        logger.error(f"Erreur générale : {e}")
    finally:
        duree = datetime.now() - timestamp_begin_job
        logger.info(f"Durée du programme : {duree}")

        # Fermer la session Spark
        # if 'spark' in locals() and spark is not None:
            #spark.stop()
            #logger.info("Session Spark fermée")

        if json_object and not options.generator_computed:
            logger.info("----- Écriture des données générées au format JSON -----")
            write_json(json_object, timestamp_str, options, None)

        if options.bucket and options.generator_computed:
            logger.info("----- Upload des fichiers générées (option -g) dans le bucket Oracle Cloud -----")
            upload_to_bucket("data/output/generated/environmental_to_send/computed/", "wildtrace-environmental", options)
        if options.bucket and options.generator_collected:
            logger.info("----- Upload des fichiers générées (option -gc) dans le bucket Oracle Cloud -----")
            upload_to_bucket("data/output/generated/environmental_to_send/collected/", "wildtrace-environmental", options)
        elif options.bucket and not (options.generator_computed or options.generator_collected):
            logger.info("Upload vers le bucket Oracle Cloud non activé.")
            logger.info("Pour activer, utiliser l'option -b ou --bucket, ainsi qu'une des options du generator.")

