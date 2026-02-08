from pathlib import Path
import oci
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from utils.loggerUtils import logger, log_file
from my_secrets.secrets import config_oci_path

bucket_name = "wildtrace-environmental"

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


def upload_to_bucket(folder_path, options):
    object_storage, namespace = connect_to_bucket()
    logger.info("Upload des fichiers vers le bucket Oracle Cloud...")
    folder = Path(folder_path)
    bucket_path = ""
    if options.generator_collected:
        bucket_path = "generated/collected"
    elif options.generator_computed:
        bucket_path = "generated/computed"

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

def computing_collected():
    object_storage, namespace = connect_to_bucket()
    bucket_path = "collected/to_compute"
    object_list = object_storage.list_objects(namespace, bucket_name, fields="name,timeCreated,size")
    
    if len(object_list.data.objects) == 0:
        logger.info("No files to compute.")
        return
    
    for o in object_list.data.objects:
        # Récupération du nom du fichier
        file_name = str(o.name).rsplit('/', 1)[-1]
        logger.info(f"Nom du fichier : {file_name}")
        
        # Vérifier que le fichier existe en local dans 'to_compute'
        # Oui : On compute, on enregistre en local dans 'computed', on envoie dans le bucket, on supprime de 'to_compute' des deux environnements
        # Non : On logge et on vérifie si le fichier existe déjà dans 'computed'
            # Si oui, on logge et un vérifie si le fichier a bien toutes les key des sorties qu'on souhaite, 
                #  si c'est bon on le logg et on vérifier qu'il n'existe pas dans le bucket dans 'computed', s'il n'existe pas on l'upload, s'il existe on logg et on le supprime de 'to_compute', puis prochain fichier
            # Si non, on le download dans 'to_compute' et le compute puis le reste (upload bucket)
        
        