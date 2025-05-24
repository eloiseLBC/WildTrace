from datetime import datetime

def is_night():
    return True

def get_season(hemisphere, date_now, format="%d-%m-%Y"):
    timestamp = datetime.strptime(date_now, format)
    try:
        if hemisphere == "nord":
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

        elif hemisphere == "sud":
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
    timestamp = datetime.strptime(timestamp, "%d-%m-%Y %H:%M:%S.%f")
    formatted = f"{timestamp.day}-{timestamp.month}-{timestamp.year}"
    return formatted