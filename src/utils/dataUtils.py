from astral import LocationInfo
from astral.sun import sun
from datetime import datetime, timezone
import pytz



def is_night(lat: float, lng: float, timestamp: datetime) -> bool:
    """
    Détermine s'il fait nuit à un emplacement donné (latitude, longitude) à une date précise.
    """
    # Créer une localisation fictive (ville générique) sans chercher de ville
    location = LocationInfo(name="point", region="earth", timezone="UTC", latitude=lat, longitude=lng)
    # Calcule les heures du lever et coucher du soleil
    s = sun(location.observer, date=timestamp.date(), tzinfo=pytz.UTC)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp < s["sunrise"] or timestamp > s["sunset"]


def get_season(hemisphere, date_now, format="%d-%m-%Y"):
    """
    Détermine la saison selon la date et l'hémisphère.
    """
    timestamp = datetime.strptime(date_now, format)
    try:
        if hemisphere == "North":
            begin_spring = datetime.strptime(f"20-03-{timestamp.year}", "%d-%m-%Y")
            end_spring = datetime.strptime(f"20-06-{timestamp.year}", "%d-%m-%Y")
            begin_summer = datetime.strptime(f"21-06-{timestamp.year}", "%d-%m-%Y")
            end_summer = datetime.strptime(f"21-09-{timestamp.year}", "%d-%m-%Y")
            begin_automne = datetime.strptime(f"22-09-{timestamp.year}", "%d-%m-%Y")
            end_automne = datetime.strptime(f"20-12-{timestamp.year}", "%d-%m-%Y")

            if end_spring >= timestamp >= begin_spring:
                return "Spring"
            elif end_summer >= timestamp >= begin_summer:
                return "Summer"
            elif end_automne >= timestamp >= begin_automne:
                return "Automne"
            else:
                return "Winter"

        elif hemisphere == "South":
            begin_spring = datetime.strptime(f"22-09-{timestamp.year}", "%d-%m-%Y")
            end_spring = datetime.strptime(f"20-12-{timestamp.year}", "%d-%m-%Y")
            begin_summer = datetime.strptime(f"21-12-{timestamp.year}", "%d-%m-%Y")
            end_summer = datetime.strptime(f"19-03-{timestamp.year + 1}", "%d-%m-%Y")
            begin_automne = datetime.strptime(f"20-03-{timestamp.year}", "%d-%m-%Y")
            end_automne = datetime.strptime(f"20-06-{timestamp.year}", "%d-%m-%Y")

            if end_spring >= timestamp >= begin_spring:
                return "Spring"
            elif end_summer >= timestamp >= begin_summer:
                return "Summer"
            elif end_automne >= timestamp >= begin_automne:
                return "Automne"
            else:
                return "Winter"
    except:
        print("Error in getting season")
    return True


def  get_formatted_ddmmyyyy(timestamp):
    """
    Retourne la date formattée en dd-mm-yyyy
    """
    return timestamp[:10]
