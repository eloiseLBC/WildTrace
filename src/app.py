import pandas as pd
import optparse

from storage.sendOracle import upload_to_bucket
from utils.generator import activate_generator, activate_generator_collected
from utils.sparkUtils import create_spark_session
from utils.writeUtils import write_json
from datetime import datetime
from utils.loggerUtils import logger, timestamp_str


df = pd.DataFrame()


if __name__ == "__main__":
    logger.info("----- Application en cours de développement -----")

    parser = optparse.OptionParser()

    # add options
    parser.add_option("-g", "--generator",
                      dest="generator",
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
        if options.generator:
            logger.info("----- Partie data generator : full -----")
            try:
                json_object = activate_generator(json_object)
                if options.spark:
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
                else:
                    logger.info("----- Utilisation de Pandas (Spark non disponible) -----")
                    df = pd.DataFrame(json_object)
                    logger.info(f"DataFrame Pandas créé avec {len(df)} lignes")
                    print(df.head())

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
            exit(0)

    except Exception as e:
        logger.error(f"Erreur générale : {e}")
    finally:
        duree = datetime.now() - timestamp_begin_job
        logger.info(f"Durée du programme : {duree}")

        # Fermer la session Spark
        if 'spark' in locals() and spark is not None:
            spark.stop()
            logger.info("Session Spark fermée")

        if json_object:
            logger.info("----- Écriture des données générées au format JSON -----")
            write_json(json_object, timestamp_str, options)

        if options.bucket and options.generator:
            logger.info("----- Upload des fichiers générées (option -g) dans le bucket Oracle Cloud -----")
            upload_to_bucket("data/output/generated/environmental_to_send/computed/", "wildtrace-environmental", options)
        if options.bucket and options.generator_collected:
            logger.info("----- Upload des fichiers générées (option -gc) dans le bucket Oracle Cloud -----")
            upload_to_bucket("data/output/generated/environmental_to_send/collected/", "wildtrace-environmental", options)
        elif options.bucket :
            logger.info("Upload vers le bucket Oracle Cloud non activé.")
            logger.info("Pour activer, utiliser l'option -b ou --bucket, ainsi qu'une des options du generator.")

