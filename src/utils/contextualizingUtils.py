"""Jointure quotidienne et archivage des sources entièrement contextualisées."""
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import oci

from storage.bucket import connect_to_bucket, get_biological_daily
from utils.loggerUtils import logger


def measurement_day(row):
    timestamp = row.get("local_timestamp") or row.get("timestamp")

    try:
        date = datetime.fromisoformat(timestamp)
    except ValueError:
        date = datetime.strptime(timestamp, "%d-%m-%Y %H:%M:%S")

    # Un timestamp sans timezone représente déjà l'heure locale.
    if date.tzinfo is not None:
        timezone_name = row.get("timezone")
        if not timezone_name:
            raise ValueError(
                "Timezone manquant pour convertir le timestamp en heure locale"
            )
        date = date.astimezone(ZoneInfo(timezone_name))

    return date.date().isoformat()


def contextualize():
    object_storage, namespace = connect_to_bucket()
    environmental_bucket = "wildtrace-environmental"
    destination_bucket = "wildtrace-contextualized"

    # Créer le bucket privé dans le même compartiment que la source.
    try:
        object_storage.get_bucket(namespace, destination_bucket)
    except oci.exceptions.ServiceError as exc:
        if exc.status != 404:
            raise
        source = object_storage.get_bucket(
            namespace, environmental_bucket
        ).data
        object_storage.create_bucket(
            namespace,
            oci.object_storage.models.CreateBucketDetails(
                name=destination_bucket,
                compartment_id=source.compartment_id,
                public_access_type="NoPublicAccess",
            ),
        )

    # Lire les sorties pour retrouver les sources déjà entièrement traitées.
    existing_days = set()
    source_days = {}
    start = None
    while True:
        params = {"prefix": "contextualized_daily_"}
        if start:
            params["start"] = start
        page = object_storage.list_objects(namespace, destination_bucket, **params).data
        for obj in page.objects:
            if not obj.name.endswith(".json"):
                continue
            date = obj.name[len("contextualized_daily_"):-5]
            try:
                datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                continue
            existing_days.add(date)
            response = object_storage.get_object(namespace, destination_bucket, obj.name)
            try:
                document = json.loads(response.data.content.decode("utf-8-sig"))
                for name, dates in document.get("source_file_days", {}).items():
                    source_days.setdefault(name, set()).update(dates)
            finally:
                response.data.close()
        start = page.next_start_with
        if not start:
            break
    processed_files = {
        name for name, dates in source_days.items()
        if dates and dates <= existing_days
    }

    days = {}
    file_days = {}
    source_etags = {}
    unreadable_files = False
    start = None
    while True:
        params = {"prefix": "collected/computed/"}
        if start:
            params["start"] = start
        page = object_storage.list_objects(
            namespace, environmental_bucket, **params
        ).data

        for obj in page.objects:
            if (not obj.name.endswith(".json")
                    or obj.name.startswith("collected/computed/archives/")):
                continue
            if obj.name in processed_files:
                logger.info(f"Source déjà contextualisée : {obj.name}")
                continue
            try:
                response = object_storage.get_object(
                    namespace, environmental_bucket, obj.name
                )
                try:
                    rows = json.loads(response.data.content.decode("utf-8-sig"))
                    source_etags[obj.name] = response.headers["etag"]
                finally:
                    response.data.close()
                if isinstance(rows, dict):
                    rows = [rows]
                if not isinstance(rows, list):
                    raise ValueError("Objet ou liste JSON attendu")
                for row in rows:
                    try:
                        date = measurement_day(row)
                    except (ValueError, TypeError, KeyError, LookupError, AttributeError) as exc:
                        # Le jour est inconnu : éviter toute sortie quotidienne partielle.
                        unreadable_files = True
                        logger.warning(f"Mesure invalide dans {obj.name} : {exc}")
                        continue
                    file_days.setdefault(obj.name, set()).add(date)
                    if date in existing_days:
                        continue
                    day = days.setdefault(date, {"rows": [], "files": set()})
                    day["rows"].append(row)
                    day["files"].add(obj.name)
            except (oci.exceptions.ServiceError, oci.exceptions.RequestException,
                    ValueError, UnicodeError) as exc:
                unreadable_files = True
                logger.error(f"Lecture environnementale échouée : {obj.name} : {exc}")

        start = page.next_start_with
        if not start:
            break

    if unreadable_files:
        logger.warning("Contextualisation interrompue : sources environnementales incomplètes.")
        return

    for date, day in sorted(days.items()):
        biological = get_biological_daily(object_storage, namespace, date)
        if not isinstance(biological, dict) or biological.get("date") != date:
            logger.info(f"Jour ignoré sans correspondance biologique valide : {date}")
            continue
        result = {
            "date": date,
            "schema_version": "1.0.0",
            "environmental": day["rows"],
            "biological": biological,
            "source_files": {
                "environmental": sorted(day["files"]),
                "biological": f"collected/computed/biological_daily_{date}.json",
            },
            "source_file_days": {
                name: sorted(file_days[name]) for name in sorted(day["files"])
            },
        }
        name = f"contextualized_daily_{date}.json"
        try:
            object_storage.put_object(
                namespace, destination_bucket, name,
                json.dumps(result, ensure_ascii=False, indent=2,
                           allow_nan=False).encode("utf-8"),
                content_type="application/json",
                if_none_match="*",
            )
            existing_days.add(date)
            logger.info(f"Fichier contextualisé enregistré : {name}")
        except (oci.exceptions.ServiceError, oci.exceptions.RequestException,
                ValueError, TypeError) as exc:
            if isinstance(exc, oci.exceptions.ServiceError) and exc.status == 412:
                logger.info(f"Fichier déjà présent, conservé : {name}")
                continue
            logger.error(f"Contextualisation échouée pour {date} : {exc}")

    # Déplacer uniquement les sources dont tous les jours ont une sortie persistée.
    # Attendre la fin de la pagination avant de modifier les noms des objets.
    processed_files.update(
        name for name, dates in file_days.items()
        if dates and dates <= existing_days
    )
    for source_name in sorted(processed_files):
        prefix = "collected/computed/"
        archive_prefix = prefix + "archives/"
        if (not source_name.startswith(prefix)
                or source_name.startswith(archive_prefix)
                or not source_name.endswith(".json")):
            continue
        archive_name = archive_prefix + source_name[len(prefix):]
        try:
            etag = source_etags.get(source_name)
            if etag is None:
                etag = object_storage.head_object(
                    namespace, environmental_bucket, source_name
                ).headers["etag"]
            object_storage.rename_object(
                namespace, environmental_bucket,
                oci.object_storage.models.RenameObjectDetails(
                    source_name=source_name,
                    new_name=archive_name,
                    src_obj_if_match_e_tag=etag,
                    new_obj_if_none_match_e_tag="*",
                ),
            )
            logger.info(f"Source contextualisée archivée : {archive_name}")
        except (oci.exceptions.ServiceError, oci.exceptions.RequestException) as exc:
            if isinstance(exc, oci.exceptions.ServiceError) and exc.status == 404:
                logger.info(f"Source déjà déplacée ou absente : {source_name}")
                continue
            logger.error(f"Archivage échoué pour {source_name} : {exc}")
