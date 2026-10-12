"""Date minimale autorisée pour le calcul environnemental."""
from datetime import datetime
from zoneinfo import ZoneInfo

ENVIRONMENTAL_START_DAY = "2026-10-01"
BIOLOGICAL_START_DAY = "2026-10-01"


def environmental_day(row):
    timestamp = row.get("local_timestamp") or row.get("timestamp")
    try:
        date = datetime.fromisoformat(timestamp)
    except ValueError:
        date = datetime.strptime(timestamp, "%d-%m-%Y %H:%M:%S")
    if date.tzinfo is not None:
        date = date.astimezone(ZoneInfo(row["timezone"]))
    return date.date().isoformat()
