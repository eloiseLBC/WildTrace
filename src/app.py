from utils.geoUtils import get_city_country

if __name__ == "__main__":
    latitude, longitude = 44.838295, -0.575381
    city, country, formatted_address = get_city_country(latitude, longitude)
    print(f"City : {city}, country : {country}, formatted address : {formatted_address}")

