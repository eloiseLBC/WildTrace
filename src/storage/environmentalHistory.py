"""Historique des cinq fichiers environnementaux précédant la source courante."""
import json
import re
from datetime import datetime, timezone

import oci

from utils.loggerUtils import logger


def file_order(obj):
    # Les noms de collecte encodent la date de mesure, contrairement à la
    # création de l'objet, qui peut changer après upload ou archivage.
    match = re.search(r"(\d{2}-\d{2}-\d{4}-\d{2}-\d{2}-\d{2})", obj.name)
    if match:
        try:
            date = datetime.strptime(match.group(1), "%d-%m-%Y-%H-%M-%S")
            return date.replace(tzinfo=timezone.utc), obj.name.rsplit("/", 1)[-1]
        except ValueError:
            pass
    date = getattr(obj, "time_created", None)
    if not isinstance(date, datetime):
        date = datetime.min.replace(tzinfo=timezone.utc)
    elif date.tzinfo is None:
        date = date.replace(tzinfo=timezone.utc)
    return date, obj.name.rsplit("/", 1)[-1]


def list_environmental_objects(client, namespace, bucket, prefix):
    start = None
    while True:
        params = {"prefix": prefix, "fields": "name,timeCreated,size"}
        if start:
            params["start"] = start
        page = client.list_objects(namespace, bucket, **params).data
        yield from (obj for obj in page.objects if obj.name.endswith(".json"))
        start = page.next_start_with
        if not start:
            break


def previous_environmental_files(client, namespace, bucket, current):
    # Un même fichier brut/calculé/archivé ne compte qu'une fois.
    objects = {}
    for prefix in ("collected/to_compute/", "collected/computed/"):
        for obj in list_environmental_objects(client, namespace, bucket, prefix):
            objects[obj.name.rsplit("/", 1)[-1]] = obj
    current_name = current.name.rsplit("/", 1)[-1]
    previous = sorted(
        (obj for name, obj in objects.items()
         if name != current_name and file_order(obj) < file_order(current)),
        key=file_order, reverse=True,
    )[:5]
    for obj in previous:
        try:
            response = client.get_object(namespace, bucket, obj.name)
            try:
                yield json.loads(response.data.content.decode("utf-8-sig"))
            finally:
                response.data.close()
        except (oci.exceptions.ServiceError, oci.exceptions.RequestException,
                ValueError, UnicodeError) as exc:
            logger.warning(f"Historique environnemental illisible : {obj.name} : {exc}")
            # Une erreur compte quand même parmi les cinq fichiers précédents.
            yield None
