"""Speichern und Exportieren der gescrapten Daten (Excel/CSV), getrennt von der Scraping-Logik."""

from __future__ import annotations

import os
import time

import pandas as pd

from .extractor import BusinessRecord
from .logging_config import get_logger

logger = get_logger(__name__)

COLUMNS = ["Firmenname", "Adresse", "Telefonnummer", "Webseite", "E-Mail-Adresse"]


def records_to_dataframe(records: list[BusinessRecord]) -> pd.DataFrame:
    """Wandelt eine Liste von BusinessRecord-Objekten in ein DataFrame um."""
    if not records:
        return pd.DataFrame(columns=COLUMNS)
    return pd.DataFrame([r.to_dict() for r in records], columns=COLUMNS)


def deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    """Entfernt doppelte Einträge anhand von Firmenname + Adresse."""
    before = len(df)
    df = df.drop_duplicates(subset=["Firmenname", "Adresse"], keep="first")
    removed = before - len(df)
    if removed:
        logger.info("%s Duplikate entfernt.", removed)
    return df


def save_excel(df: pd.DataFrame, filepath: str) -> None:
    """Speichert als temp-Datei + Umbenennen, damit ein Absturz mittendrin nicht die alte Datei zerstört."""
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    temp_path = filepath + ".tmp"

    try:
        df.to_excel(temp_path, index=False, engine="openpyxl")
        if os.path.exists(filepath):
            os.remove(filepath)
        os.rename(temp_path, filepath)
        logger.info("Excel-Datei gespeichert: %s (%s Einträge)", filepath, len(df))
    except Exception:
        logger.exception("Fehler beim Speichern der Excel-Datei %s", filepath)
        # CSV-Fallback, damit die Daten nicht verloren gehen
        csv_fallback = filepath.rsplit(".", 1)[0] + f"_backup_{int(time.time())}.csv"
        df.to_csv(csv_fallback, index=False, encoding="utf-8-sig")
        logger.warning("CSV-Sicherung geschrieben: %s", csv_fallback)
        raise


def save_csv(df: pd.DataFrame, filepath: str) -> None:
    """Speichert das DataFrame als CSV-Datei (UTF-8 mit BOM für Excel-Kompatibilität)."""
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    logger.info("CSV-Datei gespeichert: %s (%s Einträge)", filepath, len(df))


def load_existing(filepath: str) -> pd.DataFrame:
    """Lädt bereits vorhandene Ergebnisse, falls die Datei existiert (sonst leeres DataFrame)."""
    if os.path.exists(filepath):
        try:
            df = pd.read_excel(filepath)
            logger.info("%s bestehende Einträge geladen aus %s", len(df), filepath)
            return df
        except Exception:
            logger.exception("Bestehende Datei %s konnte nicht gelesen werden, starte neu.", filepath)
    return pd.DataFrame(columns=COLUMNS)
