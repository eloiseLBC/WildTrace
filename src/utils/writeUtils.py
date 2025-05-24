import json
from datetime import datetime
from utils.loggerUtils import logger


def write_json(row, timestamp):
    timestamp_file = datetime.strptime(timestamp, "%d-%m-%Y %H:%M:%S.%f")
    timestamp_formatted = timestamp_file.strftime(f"%d-%m-%Y-%H-%M-%S")
    filename = f"collect_process_data_{timestamp_formatted}.json"
    with open(f"data/output/{filename}", "w") as f:
        json.dump(row, f, indent=2)
        logger.info(f"Fichier enregistré sous le nom : {filename}")