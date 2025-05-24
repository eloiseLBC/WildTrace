import json
from datetime import datetime


def write_json(row, timestamp):
    timestamp_file = datetime.strptime(timestamp, "%d-%m-%Y %H:%M:%S.%f")
    timestamp_formatted = timestamp_file.strftime(f"%d-%m-%Y-%H-%M-%S")
    with open(f"data/output/collect_process_data_{timestamp_formatted}.json", "w") as f:
        json.dump(row, f, indent=2)