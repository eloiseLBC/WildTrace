"""Résolution des coordonnées avant tout calcul environnemental."""
import math
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from functools import lru_cache

import pytz

from .geoUtils import get_location_coordinates
from .loggerUtils import logger


def valid_coordinate(value, limit):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and -limit <= value <= limit)


def location_address(document):
    if not isinstance(document, dict):
        return None
    location = document.get("city_country") or document
    if not isinstance(location, dict):
        return None
    city, country = location.get("city"), location.get("country")
    if (isinstance(city, str) and city.strip()
            and isinstance(country, str) and country.strip()):
        return f"{city.strip()}, {country.strip()}"
    return None


@lru_cache(maxsize=128)
def timezone_capital(timezone_name):
    """Associe un fuseau IANA (ou un nom de pays) à sa capitale."""
    if not isinstance(timezone_name, str) or not timezone_name.strip():
        return None
    countries = [
        code for code, zones in pytz.country_timezones.items()
        if timezone_name in zones
        or timezone_name.casefold() == pytz.country_names[code].casefold()
    ]
    if len(countries) != 1:
        logger.warning(f"Pays indéterminé pour le fuseau : {timezone_name}")
        return None
    with Path(__file__).with_name("countryCapitals.json").open(encoding="utf-8") as file:
        country = json.load(file)["countries"].get(countries[0])
    return location_address(country)



def resolve_gps(row, previous_files, load_biological):
    latitude, longitude = row.get("latitude"), row.get("longitude")
    latitude_valid = valid_coordinate(latitude, 90)
    longitude_valid = valid_coordinate(longitude, 180)
    if latitude_valid and longitude_valid:
        return {"latitude": latitude, "longitude": longitude,
                "gps_coordinates": "computed" if row.get("reconstruction") else "sensor"}

    def measurement_time(measurement):
        timestamp = measurement.get("local_timestamp") or measurement.get("timestamp")
        try:
            date = datetime.fromisoformat(timestamp)
        except ValueError:
            date = datetime.strptime(timestamp, "%d-%m-%Y %H:%M:%S")
        if date.tzinfo is not None:
            zone = measurement.get("timezone") or row.get("timezone")
            if not zone:
                raise ValueError("Timezone absent pour déterminer le jour local")
            date = date.astimezone(ZoneInfo(zone))
        return date.replace(tzinfo=None)

    # Comparer les dates des mesures JSON, pas les noms ni les dates d'upload.
    candidates_from_history = []
    try:
        current_day = measurement_time(row).date()
        first_day = current_day - timedelta(days=5)
        for document in previous_files():
            rows = document if isinstance(document, list) else [document]
            for previous in rows:
                if not isinstance(previous, dict):
                    continue
                try:
                    date = measurement_time(previous)
                except (ValueError, TypeError, LookupError):
                    continue
                if first_day <= date.date() < current_day:
                    candidates_from_history.append((date, previous))
    except (ValueError, TypeError, LookupError) as exc:
        logger.debug(f"Recherche des cinq jours précédents impossible : {exc}")
    for date, previous in sorted(candidates_from_history, key=lambda item: item[0], reverse=True):
        previous_lat = previous.get("latitude")
        previous_lng = previous.get("longitude")
        previous_altitude = previous.get("altitude")
        if previous_altitude is None:
            previous_altitude = previous.get("altitude_m")
        if (valid_coordinate(previous_lat, 90)
                and valid_coordinate(previous_lng, 180)
                and isinstance(previous_altitude, (int, float))
                and not isinstance(previous_altitude, bool)
                and math.isfinite(previous_altitude)):
            logger.info(
                f"Coordonnées GPS reprises du {date.date().isoformat()} (J−5 à J−1) : "
                f"latitude={previous_lat}, longitude={previous_lng}, "
                f"altitude={previous_altitude}"
            )
            return {
                "latitude": latitude if latitude_valid else previous_lat,
                "longitude": longitude if longitude_valid else previous_lng,
                "altitude": previous_altitude,
                "gps_coordinates": "computed",
            }

    def candidates():
        address = location_address(load_biological())
        if address:
            yield address
        address = timezone_capital(row.get("timezone"))
        if address:
            yield address

    for address in candidates():
        position = get_location_coordinates(address)
        if (valid_coordinate(position.get("latitude"), 90)
                and valid_coordinate(position.get("longitude"), 180)):
            logger.info(f"Coordonnées GPS calculées depuis : {address}")
            return {
                **position,
                "latitude": latitude if latitude_valid else position["latitude"],
                "longitude": longitude if longitude_valid else position["longitude"],
                "gps_coordinates": "computed",
            }
    logger.warning(
        "Coordonnées GPS indisponibles : aucun repli exploitable "
        "(5 jours précédents, biologique, timezone). "
        "Le fichier reste dans collected/to_compute."
    )
    return None
