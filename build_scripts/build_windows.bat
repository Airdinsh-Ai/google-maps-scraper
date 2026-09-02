@echo off
REM ============================================================
REM Baut die Windows-EXE des Google Maps Lead Scrapers.
REM Muss unter WINDOWS ausgeführt werden (PyInstaller baut nur
REM für das Betriebssystem, auf dem es laeuft).
REM ============================================================

echo Erstelle/aktiviere virtuelle Umgebung ...
python -m venv .venv
call .venv\Scripts\activate.bat

echo Installiere Abhaengigkeiten ...
pip install --upgrade pip
pip install -r requirements-dev.txt

echo Baue Windows-Anwendung mit PyInstaller ...
pyinstaller gmaps_scraper.spec --noconfirm

echo.
echo Fertig! Die Anwendung liegt in: dist\GoogleMapsLeadScraper\
pause
