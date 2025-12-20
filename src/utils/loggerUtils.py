import logging
import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from my_secrets.secrets import log_dir

timestamp_str = datetime.now().strftime("%d-%m-%Y %H:%M:%S.%f")
timestamp_file = datetime.strptime(timestamp_str, "%d-%m-%Y %H:%M:%S.%f")
timestamp_formatted = timestamp_file.strftime(f"%d-%m-%Y-%H-%M-%S")

# Crée un logger
logger = logging.getLogger("WildTrace")
logger.setLevel(logging.INFO)
logger.propagate = False  # Important pour éviter les doublons

# Format de log
formatter = logging.Formatter(
    "{asctime} | WildTrace | {levelname} | {message}", style="{", datefmt="%Y-%m-%d %H:%M:%S"
)

# Handler console
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# Handler fichier
log_dir = Path(log_dir)
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"wildtrace-{timestamp_formatted}.log"
file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
file_handler.setFormatter(formatter)

# N'ajoute les handlers qu'une seule fois
if not logger.hasHandlers():
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
