"""Créer les sources environnementales manquantes à partir des jours biologiques."""
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import oci

from storage.environmentalHistory import list_environmental_objects
from utils.geoUtils import get_location_coordinates
from utils.gpsUtils import location_address, valid_coordinate
from utils.loggerUtils import logger


def row_day(row):
    timestamp = row.get("local_timestamp") or row.get("timestamp")
    try:
        date = datetime.fromisoformat(timestamp)
    except ValueError:
        date = datetime.strptime(timestamp, "%d-%m-%Y %H:%M:%S")
    if date.tzinfo is not None:
        date = date.astimezone(ZoneInfo(row["timezone"]))
    return date.date().isoformat()


def backfill_environmental_days(client, namespace, biological_days):
    if not biological_days:
        return
    bucket = "wildtrace-environmental"
    existing_days = set()
    # computed/ inclut archives/ ; les sources encore en attente comptent aussi.
    for prefix in ("collected/to_compute/", "collected/computed/"):
        for obj in list_environmental_objects(client, namespace, bucket, prefix):
            try:
                response = client.get_object(namespace, bucket, obj.name)
                try:
                    rows = json.loads(response.data.content.decode("utf-8-sig"))
                finally:
                    response.data.close()
                if isinstance(rows, dict):
                    rows = [rows]
                if not isinstance(rows, list):
                    raise ValueError("Objet ou liste JSON attendu")
                for row in rows:
                    existing_days.add(row_day(row))
            except (oci.exceptions.ServiceError, oci.exceptions.RequestException,
                    ValueError, TypeError, KeyError, LookupError,
                    AttributeError, UnicodeError) as exc:
                logger.warning(
                    f"Vérification des jours impossible pour {obj.name} : {exc}. "
                    "Reconstruction interrompue pour éviter les doublons."
                )
                return

    for day, biological in sorted(biological_days.items()):
        if day in existing_days:
            continue
        name = f"collected/to_compute/environmental_daily_{day}.json"
        try:
            if not isinstance(biological, dict) or biological.get("date") != day:
                raise ValueError("Date biologique incohérente")
            datetime.strptime(day, "%Y-%m-%d")
            address = location_address(biological)
            if not address:
                raise ValueError("Ville/pays biologiques absents")
            timezone_name = biological.get("timezone")
            ZoneInfo(timezone_name)
            position = get_location_coordinates(address)
            if not (valid_coordinate(position.get("latitude"), 90)
                    and valid_coordinate(position.get("longitude"), 180)):
                raise ValueError("Géocodage de la ville biologique indisponible")
            row = {
                "local_timestamp": f"{day} 12:00:00",
                "timezone": timezone_name,
                "latitude": position["latitude"],
                "longitude": position["longitude"],
                "altitude": position.get("altitude"),
                "gps_coordinates": "computed",
                "city_country": biological["city_country"],
                "reconstruction": {
                    "source_bucket": "wildtrace-biological",
                    "source_file": f"collected/computed/biological_daily_{day}.json",
                    "sampling": "local_noon",
                },
            }
            client.put_object(
                namespace, bucket, name,
                json.dumps([row], ensure_ascii=False, allow_nan=False).encode("utf-8"),
                content_type="application/json", if_none_match="*",
            )
            existing_days.add(day)
            logger.info(f"Source environnementale recréée pour {day} : {name}")
        except (oci.exceptions.ServiceError, oci.exceptions.RequestException,
                ValueError, TypeError, KeyError, LookupError) as exc:
            if isinstance(exc, oci.exceptions.ServiceError) and exc.status == 412:
                continue
            logger.warning(f"Reconstruction environnementale impossible pour {day} : {exc}")
