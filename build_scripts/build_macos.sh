#!/usr/bin/env bash
# ============================================================
# Baut die macOS-App des Google Maps Lead Scrapers.
# Muss unter macOS ausgeführt werden (PyInstaller baut nur
# für das Betriebssystem, auf dem es laeuft).
# ============================================================
set -e

echo "Erstelle/aktiviere virtuelle Umgebung ..."
python3 -m venv .venv
source .venv/bin/activate

echo "Installiere Abhaengigkeiten ..."
pip install --upgrade pip
pip install -r requirements-dev.txt

echo "Baue macOS-App mit PyInstaller ..."
pyinstaller gmaps_scraper.spec --noconfirm

echo ""
echo "Fertig! Die App liegt in: dist/GoogleMapsLeadScraper.app"
echo "Hinweis: Beim ersten Start evtl. Rechtsklick -> Öffnen noetig,"
echo "da die App nicht von Apple signiert ist (Gatekeeper-Warnung)."
