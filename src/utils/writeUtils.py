import io
import sys
import os
import json
import requests

from .credentialsUtils import generate_credentials_google_drive

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from my_secrets.secrets import headers, drive_folder_collected_data_id, bearer_token, drive_folder_logs
from datetime import datetime
from .loggerUtils import logger, timestamp_formatted


def write_json(row, timestamp, option_generator):
    timestamp_file = datetime.strptime(timestamp, "%d-%m-%Y %H:%M:%S.%f")
    timestamp_formatted = timestamp_file.strftime(f"%d-%m-%Y-%H-%M-%S")
    filename = f"collect_process_data_{timestamp_formatted}.json"
    path = f"data/output/generated/environmental_to_send/{filename}" if option_generator is True else f"data/output/collected/environmental_to_send{filename}"
    with open(path, "w") as f:
        json.dump(row, f, indent=2)
        # Permet de synchroniser le système et que s'il y a lecture le fichier soit bien trouvé
        f.flush()
        os.fsync(f.fileno())
        logger.info(f"Fichier enregistré sous le nom : {filename}")
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


def upload_file_to_drive(filepath, filename, parent_folder_id):
    """
        Sauvegarde un JSON dans Google Drive (upload multipart).
        Args:
            filepath (str): Chemin complet du fichier à écrire.
            filename (str): Nom du fichier dans Google Drive.
            parent_folder_id (str): ID du dossier Drive cible.
    """
    try:
        # Lecture binaire
        with open(filepath, "rb") as f:
            file_content = f.read()
        if not file_content:
            if logger:
                logger.error("Le fichier est vide après écriture. Upload annulé.")
            return None
    except Exception as e:
        if logger:
            logger.error(f"Erreur lors de la lecture du fichier : {e}")
        return None

    try:
        # Construction multipart
        url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"
        metadata = {
            "name": filename,
            "parents": [parent_folder_id]
        }

        files = {
            "metadata": ("metadata", json.dumps(metadata), "application/json; charset=UTF-8"),
            "file": (filename, io.BytesIO(file_content), "application/json")
        }

        # Requête HTTP vers Google Drive
        response = requests.post(url, headers=headers, files=files)
        response.raise_for_status()

        file_id = response.json()["id"]
        if logger:
            logger.info(f"Upload réussi : {filename} (ID: {file_id})")
        return file_id

    except requests.exceptions.RequestException as e:
        if logger:
            logger.error(f"Erreur HTTP lors de l’upload : {e}")
            if hasattr(e, 'response') and e.response is not None and e.response.status_code != 401:
                logger.error(f"Détail : {e.response.text}")
            elif e.response.status_code == 401:
                logger.warning("Erreur d'authentification (401). Génération de nouveaux credentials.")
                generate_credentials_google_drive()
        return None


def write_log_drive():
    logfile_name = f"wildtrace-{timestamp_formatted}.log"
    logfile_path = f"logs/{logfile_name}"
    filename = os.path.basename(logfile_path)

    if not os.path.exists(logfile_path):
        if logger:
            logger.warning(f"Fichier log introuvable : {logfile_path}")
        return None

    if os.path.getsize(logfile_path) == 0:
        if logger:
            logger.warning("Fichier log vide. Aucun upload.")
        return None

    return upload_file_to_drive(
        filepath=logfile_path,
        filename=filename,
        parent_folder_id=drive_folder_logs
    )