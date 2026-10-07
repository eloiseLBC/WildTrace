from astral import LocationInfo
from astral.sun import sun
from datetime import datetime, timezone
import pytz
from utils.loggerUtils import logger



def is_night(lat: float, lng: float, timestamp: datetime) -> bool:
    """
    Détermine s'il fait nuit à un emplacement donné (latitude, longitude) à une date précise.
    """
    if lat is not None or lng is not None :
        # Créer une localisation fictive (ville générique) sans chercher de ville
        location = LocationInfo(name="point", region="earth", timezone="UTC", latitude=lat, longitude=lng)
        # Calcule les heures du lever et coucher du soleil
        s = sun(location.observer, date=timestamp.date(), tzinfo=pytz.UTC)
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        return timestamp < s["sunrise"] or timestamp > s["sunset"]
    else:
        logger.warning(f"Latitude et/ou longitude nulle -> Pas de calcul de is_night")


def get_season(hemisphere, date_now, format="%Y-%m-%d"):
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
        logger.error("Error in getting season")
    return True


def  get_formatted_ddmmyyyy(timestamp):
    """
    Retourne la date formattée en dd-mm-yyyy
    """
    return timestamp[:10]

def get_formatted_moods(moods):
    if len(moods) == 1 and ',' in moods[0]:
        moods = moods[0].split(',')
    mood_dict = {}
    for index, mood in enumerate(moods):
        mood_dict[f"mood_{index}"] = mood
    logger.info(f"Moods collectés : {mood_dict}")
        
    return mood_dict

def get_formatted_environments(environments):
    if len(environments) == 1 and ',' in environments[0]:
        environments = environments[0].split(',')
    environment_dict = {}
    for index, environment in enumerate(environments):
        logger.info(f"Index : {index}, environmenr : {environment}")
        environment_dict[f"environment_{index}"] = environment
    logger.info(f"Collected environments : {environment_dict}")
        
    return environment_dict