import logging
import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))


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

# Un emplacement commun pour les lancements directs et via l'interface.
log_dir = Path(__file__).resolve().parents[2] / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
log_time = datetime.now()
log_file = log_dir / f"wildtrace-{log_time:%Y-%m-%d-%H-%M-%S}-{log_time.microsecond // 1000:03d}.log"

if not logger.hasHandlers():
    logger.addHandler(console_handler)
    # L'interface capture déjà la console dans son fichier de traitement.
    if os.environ.get("WILDTRACE_LOG_CAPTURED") != "1":
        file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
