from pathlib import Path
import oci
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from utils.loggerUtils import logger, log_file
from my_secrets.secrets import config_oci_path


def connect_to_bucket():
    logger.info("Connexion au bucket Oracle Cloud...")
    # Charger la configuration OCI à partir du fichier config
    config = oci.config.from_file(config_oci_path)
    # Créer le client Object Storage
    object_storage = oci.object_storage.ObjectStorageClient(config)
    # Récupérer le namespace
    namespace = object_storage.get_namespace().data
    logger.info(f"Connecté au namespace : {namespace}")

    # Exemple : lister les buckets
    buckets = object_storage.list_buckets(namespace, config["tenancy"])
    for b in buckets.data:
        logger.info(f"- {b.name}")

    return object_storage, namespace


def upload_to_bucket(folder_path, bucket_name, options):
    object_storage, namespace = connect_to_bucket()
    logger.info("Upload des fichiers vers le bucket Oracle Cloud...")
    folder = Path(folder_path)
    bucket_path = ""
    if options.generator_collected:
        bucket_path = "generated/collected"
    elif options.generator_computed:
        bucket_path = "generated/computed"
    else:
        bucket_path = "collected/to_compute"

    if not folder.exists() or not folder.is_dir():
        logger.info(f"No such directory: `{folder_path}`")
        return

    files = [f for f in folder.glob("*") if f.is_file()]
    if not files:
        logger.info(f"No files to upload in folder: `{folder_path}`")
        return

    for file in files:
        logger.info(f"Uploading file: {file.name}")
        with file.open("rb") as f:
            object_storage.put_object(namespace, bucket_name, f"{bucket_path}/{file.name}", f)
            logger.info(f"→ {file.name} uploaded.")
        # Move file to 'uploaded' subfolder
        uploaded_folder = folder / "uploaded"
        uploaded_folder.mkdir(exist_ok=True)
        file.rename(uploaded_folder / file.name)

