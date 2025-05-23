from utils.geoUtils import get_city_country, get_altitude, get_distance_from_equator, \
    get_coastline_distance
import pandas as pd

df = pd.DataFrame()

if __name__ == "__main__":
    print("----- Application en cours de développement -----")
    lat, lng = 44.0997, -12.4567
    row = {
        "latitude": lat,
        "longitude": lng,
        **get_city_country(lat, lng),
        "altitude": get_altitude(lat, lng),
        **get_distance_from_equator(lat),
        **get_coastline_distance(48.872997, 2.348728)
    }

    df = pd.DataFrame([row])
    print(df)






