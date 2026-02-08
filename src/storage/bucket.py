from pathlib import Path
import oci
import sys
import os
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from utils.loggerUtils import logger, log_file, timestamp_str
from utils.computingUtils import compute_data
from utils.writeUtils import write_json
from my_secrets.secrets import config_oci_path, computed_data_dir_to_send, collected_uploaded_data_dir, tmp_to_compute_dir, computed_data_dir_uploaded

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
    bucket_path = "collected/to_compute"
    if options.generator_collected:
        bucket_path = "generated/collected"
    elif options.generator_computed:
        bucket_path = "generated/computed"
        
    logger.info(f"Bucket path : {bucket_path}")

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
        
        
def upload_to_bucket_single_file(object_storage, namespace, file_path, options):
    logger.info(f"Upload du fichier {file_path} vers le bucket Oracle Cloud...")
    file = Path(file_path)
    bucket_path = ""
    if options.computed:
        bucket_path = "collected/computed"
        
    if not file.exists():
        logger.error(f"No such file : {file.name}")
        return
    
    with file.open("rb") as f:
        try:
            object_storage.put_object(namespace, bucket_name, f"{bucket_path}/{file.name}", f)
            logger.info(f"→ {file.name} uploaded in collected/computed.")
            # Move file to 'uploaded' subfolder
            uploaded_folder = Path(computed_data_dir_uploaded)
            uploaded_folder.mkdir(exist_ok=True)
            file.rename(uploaded_folder / file.name)
            # Delete file in bucket 'to_compute'
            file_path_bucket = f"collected/to_compute/{file.name}"
            logger.info("File path bucket : " + str(file_path_bucket))
            object_storage.delete_object(
                namespace,
                bucket_name,
                file_path_bucket
            )
            logger.info(f"→ {file.name} deleted from collected/to_compute.")
            
        except Exception as e:
            logger.error(f"Upload du fichier dans le bucket échoué : {e}")
    
    
    
        

def computing_collected(options):
    object_storage, namespace = connect_to_bucket()

    bucket_path = "collected/to_compute"
    object_list = object_storage.list_objects(
        namespace,
        bucket_name,
        prefix=bucket_path + "/",  
        fields="name,timeCreated,size"
    )

    local_to_compute_dir = Path(tmp_to_compute_dir)
    local_to_compute_dir.mkdir(parents=True, exist_ok=True)

    uploaded_dir = Path(collected_uploaded_data_dir)
    uploaded_dir.mkdir(parents=True, exist_ok=True)

    objects = object_list.data.objects or []
    if len(objects) == 0:
        logger.info("No files to compute.")
        return

    files_computed_environmental_to_send = {
        f.name for f in Path(computed_data_dir_to_send).glob("*") if f.is_file()
    }
    logger.info(f"Already {len(files_computed_environmental_to_send)} files in local computed/environmental_to_send.")

    files_collected_uploaded = {f.name for f in uploaded_dir.glob("*") if f.is_file()}

    for o in objects:
        obj_name = o.name  
        file_name = obj_name.rsplit("/", 1)[-1]
        if not file_name:
            continue

        if file_name in files_computed_environmental_to_send:
            logger.warning(f"SKIP: {file_name} already exists in local computed/environmental_to_send")
            upload_to_bucket_single_file(object_storage, namespace, f"{computed_data_dir_to_send}/{file_name}", options)
            continue

        # Choix input local
        if file_name in files_collected_uploaded:
            logger.info(f"Using local uploaded file: {file_name}")
            local_input_path = uploaded_dir / file_name
        else:
            logger.info(f"Downloading {file_name} from bucket...")
            local_input_path = local_to_compute_dir / file_name

            if not local_input_path.exists():
                try:
                    response = object_storage.get_object(namespace, bucket_name, obj_name)
                    # download 
                    import shutil
                    with open(local_input_path, "wb") as f:
                        shutil.copyfileobj(response.data.raw, f)
                except Exception as e:
                    logger.error(f"DOWNLOAD FAILED for {file_name}: {e}")
                    continue

        # Lecture JSON 
        try:
            with open(local_input_path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
                computed_json = compute_data(data)
                if computed_json == "":
                    logger.info(f"-- Fichier sans timestamp : {file_name}")
                else:
                    write_json(computed_json, timestamp_str, options, file_name)
                    upload_to_bucket_single_file(object_storage, namespace, f"{computed_data_dir_to_send}/{file_name}", options)

        except json.JSONDecodeError as e:
            logger.error(f"INVALID JSON {file_name}: {e}")
            continue

        # Ici: enrichissement + write computed + upload + cleanup

        