#!/usr/bin/env bash
# ============================================================
# Baut die Linux-Anwendung des Google Maps Lead Scrapers.
# Muss unter Linux ausgeführt werden (PyInstaller baut nur
# für das Betriebssystem, auf dem es laeuft).
# ============================================================
set -e

echo "Erstelle/aktiviere virtuelle Umgebung ..."
python3 -m venv .venv
source .venv/bin/activate

echo "Installiere Abhaengigkeiten ..."
pip install --upgrade pip
pip install -r requirements-dev.txt

echo "Baue Linux-Anwendung mit PyInstaller ..."
pyinstaller gmaps_scraper.spec --noconfirm

echo ""
echo "Fertig! Die Anwendung liegt in: dist/GoogleMapsLeadScraper/"
echo "Starten mit: ./dist/GoogleMapsLeadScraper/GoogleMapsLeadScraper"
