from pathlib import Path
import oci
import subprocess
import os

def internet_available():
    result = subprocess.run(
        ["ping", "-c", "1", "1.1.1.1"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    return result.returncode == 0

def files_exist():
    folder = Path("data/output/generated/environmental_to_send/collected/")
    if not folder.exists() or not folder.is_dir():
        print(f"No such directory: `{folder}`")
        return False

    files = [f for f in folder.glob("*") if f.is_file()]
    if not files:
        print(f"No files found in folder: `{folder}`")
        return False

    print(f"Files found in folder: `{folder}`")
    return True 

def connect_to_bucket():
    print("Connexion au bucket Oracle Cloud...")
    # Charger la configuration OCI à partir du fichier config
    config = oci.config.from_file(".oci/config")
    # Créer le client Object Storage
    object_storage = oci.object_storage.ObjectStorageClient(config)
    # Récupérer le namespace
    namespace = object_storage.get_namespace().data
    print(f"Connecté au namespace : {namespace}")

    # Exemple : lister les buckets
    buckets = object_storage.list_buckets(namespace, config["tenancy"])
    for b in buckets.data:
        print("-", b.name)

    return object_storage, namespace


def upload_to_bucket(folder_path, bucket_name, options):
    object_storage, namespace = connect_to_bucket()
    print("Upload des fichiers vers le bucket Oracle Cloud...")
    folder = Path(folder_path)
    bucket_path = ""
    if options.generator_collected:
        bucket_path = "generated/collected"
    elif options.generator_computed:
        bucket_path = "generated/computed"

    if not folder.exists() or not folder.is_dir():
        print(f"No such directory: `{folder_path}`")
        return

    files = [f for f in folder.glob("*") if f.is_file()]
    if not files:
        print(f"No files to upload in folder: `{folder_path}`")
        return

    for file in files:
        print("Uploading file:", file.name)
        with file.open("rb") as f:
            object_storage.put_object(namespace, bucket_name, f"{bucket_path}/{file.name}", f)
            print("→", file.name, "uploadé.")
        # Move file to 'uploaded' subfolder
        uploaded_folder = folder / "uploaded"
        uploaded_folder.mkdir(exist_ok=True)
        file.rename(uploaded_folder / file.name)

