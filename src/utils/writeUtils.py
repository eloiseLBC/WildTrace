import io
import sys
import os
import json
import requests

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from my_secrets.secrets import headers, drive_folder_collected_data_id, bearer_token, drive_folder_logs, generated_collected_data_dir, computed_data_dir_to_send
from datetime import datetime
from .loggerUtils import logger, timestamp_formatted


def write_json(row, timestamp, options, filename):
    timestamp_file = datetime.strptime(timestamp, "%d-%m-%Y %H:%M:%S.%f")
    timestamp_formatted = timestamp_file.strftime(f"%d-%m-%Y-%H-%M-%S")
    filename = f"collect_process_data_{timestamp_formatted}.json" if filename is None else filename

    if options.generator_computed:
        path = f"data/output/generated/environmental_to_send/computed"
    elif options.generator_collected:
        path = f"{generated_collected_data_dir}"
    elif options.computed:
        path = f"{computed_data_dir_to_send}"
    else:
        path = f"/home/eloise/Desktop/WildTrace/data/output/collected/environmental_to_send"
    # Créer le répertoire s'il n'existe pas
    os.makedirs(os.path.dirname(f"{path}/"), exist_ok=True)
    with open(f"{path}/{filename}", "w") as f:
        json.dump(row, f, indent=2)
        # Permet de synchroniser le système et que s'il y a lecture le fichier soit bien trouvé
        f.flush()
        os.fsync(f.fileno())
        logger.info(f"File saved under name: {filename}")
        # upload_file_to_drive(path, filename, drive_folder_collected_data_id)


def find_folder_id(name, parent_id):
    url = "https://www.googleapis.com/drive/v3/files"
    params = {
        "q": f"mimeType='application/vnd.google-apps.folder' and name='{name}' and '{parent_id}' in parents and trashed=false",
        "fields": "files(id, name)"
    }
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    if "files" in data and data["files"]:
        folder_id = data["files"][0]["id"]
        logger.info(f"Folder {name} id : {folder_id}")
        return folder_id
    return None


def build_multipart_body(metadata, file_data, boundary="foo_bar_baz"):
    """
    Construit le corps multipart/related pour l'upload d'un fichier sur Google Drive.

    Ce format est requis par l'API Google Drive pour envoyer à la fois :
    - les métadonnées du fichier (nom, dossier parent, etc.)
    - le contenu binaire du fichier (ici de type JSON)

    Le corps est structuré selon la norme MIME multipart avec un délimiteur (boundary),
    et contient deux parties :
    1. Un bloc JSON avec les métadonnées
    2. Un bloc avec le contenu du fichier à uploader

    Args:
        metadata (dict): Métadonnées du fichier (ex: name, parents[])
        file_data (bytes): Contenu brut du fichier (déjà ouvert en mode binaire)
        boundary (str): Chaîne utilisée comme séparateur entre les parties MIME

    Returns:
        bytes: Contenu complet formaté pour l'envoi via une requête HTTP avec content-type multipart/related
    """
    meta_part = (
        f"--{boundary}\r\n"
        "Content-Type: application/json; charset=UTF-8\r\n\r\n"
        f"{json.dumps(metadata)}\r\n"
    ).encode("utf-8")

    file_part = (
        f"--{boundary}\r\n"
        "Content-Type: application/json\r\n\r\n"
    ).encode("utf-8") + file_data + f"\r\n--{boundary}--".encode("utf-8")

    return meta_part + file_part