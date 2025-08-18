from pyspark.sql import SparkSession
from pyspark.conf import SparkConf
from utils.loggerUtils import logger

def create_spark_session():
    """Créer une session Spark compatible avec Java 17"""
    import os

    # Configuration des variables d'environnement AVANT de créer Spark
    os.environ['SPARK_LOCAL_IP'] = '127.0.0.1'

    # Désactiver complètement le security manager
    java_opts = (
        "--add-opens=java.base/sun.nio.ch=ALL-UNNAMED "
        "--add-opens=java.base/java.lang=ALL-UNNAMED "
        "--add-opens=java.base/java.lang.reflect=ALL-UNNAMED "
        "--add-opens=java.base/java.io=ALL-UNNAMED "
        "--add-opens=java.base/java.net=ALL-UNNAMED "
        "--add-opens=java.base/java.nio=ALL-UNNAMED "
        "--add-opens=java.base/java.util=ALL-UNNAMED "
        "--add-opens=java.base/java.util.concurrent=ALL-UNNAMED "
        "--add-opens=java.base/java.util.concurrent.atomic=ALL-UNNAMED "
        "--add-opens=java.base/sun.security.action=ALL-UNNAMED "
        "--add-opens=java.base/javax.security.auth=ALL-UNNAMED "
        "--add-opens=java.base/java.security=ALL-UNNAMED "
        "-Djava.security.manager=allow "
        "-Djava.security.policy=all.policy"
    )

    os.environ['SPARK_SUBMIT_OPTIONS'] = f'--driver-java-options "{java_opts}"'
    os.environ['PYSPARK_SUBMIT_ARGS'] = f'--driver-java-options "{java_opts}" pyspark-shell'

    try:
        # Essai 1: Configuration complète
        conf = SparkConf()
        conf.set("spark.driver.extraJavaOptions", java_opts)
        conf.set("spark.executor.extraJavaOptions", java_opts)

        # Configuration additionnelle pour éviter les problèmes
        conf.set("spark.sql.warehouse.dir", "/tmp/spark-warehouse")
        conf.set("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
        conf.set("spark.hadoop.fs.defaultFS", "file:///")

        # Créer la session Spark
        spark = SparkSession.builder \
            .appName("WildTrace-DataGeneration") \
            .master("local[*]") \
            .config(conf=conf) \
            .getOrCreate()

        # Réduire le niveau de log pour éviter trop de messages
        spark.sparkContext.setLogLevel("WARN")

        logger.info("Session Spark créée avec succès")
        return spark

    except Exception as e:
        logger.error(f"Erreur lors de la création de la session Spark : {e}")

        # Fallback 1: Mode ultra-simple sans configuration Java
        try:
            logger.info("Tentative Fallback 1: Spark minimal...")

            # Nettoyer les variables d'environnement problématiques
            for key in ['SPARK_SUBMIT_OPTIONS', 'PYSPARK_SUBMIT_ARGS']:
                if key in os.environ:
                    del os.environ[key]

            spark = SparkSession.builder \
                .appName("WildTrace-Minimal") \
                .master("local[1]") \
                .config("spark.sql.warehouse.dir", "/tmp/spark-warehouse") \
                .config("spark.hadoop.fs.defaultFS", "file:///") \
                .config("spark.driver.host", "127.0.0.1") \
                .getOrCreate()

            spark.sparkContext.setLogLevel("WARN")
            logger.info("Session Spark créée en mode fallback 1")
            return spark

        except Exception as e2:
            logger.error(f"Fallback 1 échoué : {e2}")

            # Fallback 2: Complètement sans Spark
            try:
                logger.info("Fallback 2: Mode sans Spark - utilisation de pandas uniquement")
                return None

            except Exception as e3:
                logger.error(f"Impossible de créer la session Spark : {e3}")
                raise