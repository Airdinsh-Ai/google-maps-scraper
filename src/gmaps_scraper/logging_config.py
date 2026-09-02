"""
Zentrale Logging-Konfiguration statt print()-Ausgaben im ganzen Projekt.
Log-Level zentral steuerbar, Ausgaben landen zusätzlich in LOG_FILE, und die
GUI klinkt sich als eigener Handler ein, um Logzeilen live anzuzeigen.
"""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler

# Verzeichnis für Log-Dateien neben dem Projekt (bzw. neben der EXE)
LOG_DIR = os.path.join(os.path.expanduser("~"), ".gmaps_scraper", "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "scraper.log")

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def setup_logging(level: int = logging.INFO) -> None:
    """Richtet das Root-Logging einmalig ein. Mehrfaches Aufrufen fügt keine doppelten Handler hinzu."""
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    root_logger.setLevel(level)

    formatter = logging.Formatter(_LOG_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Kleiner Komfort-Wrapper, damit Module nicht direkt `logging` importieren müssen."""
    return logging.getLogger(name)
