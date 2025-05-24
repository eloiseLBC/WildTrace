from utils.dataUtils import get_season, get_formatted_ddmmyyyy
from utils.geoUtils import get_city_country, get_altitude, get_distance_from_equator, \
    get_coastline_distance, get_hemisphere
import pandas as pd
from datetime import datetime

df = pd.DataFrame()

if __name__ == "__main__":
    print("----- Application en cours de développement -----")
    lat, lng = 48.872997, 2.348728
    timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S.%f")

    row = {
        "timestamp": timestamp,
        "formatted_ddmmyyyy" : get_formatted_ddmmyyyy(timestamp),
        "latitude": lat,
        "longitude": lng,
        **get_city_country(lat, lng),
        "altitude": get_altitude(lat, lng),
        **get_distance_from_equator(lat),
        **get_coastline_distance(lat, lng),
        "hemisphere": get_hemisphere(lat),
        "season": get_season("sud", get_formatted_ddmmyyyy(timestamp))
    }

    df = pd.DataFrame([row])
    print(df)






