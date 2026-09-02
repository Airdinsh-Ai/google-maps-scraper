# Google Maps Lead Scraper

Ein Desktop-Tool zum Sammeln von Firmenkontakten (Name, Adresse, Telefonnummer,
Website, E-Mail-Adresse) aus Google Maps – mit grafischer Oberfläche, ganz
ohne Kommandozeile oder Python-Kenntnisse.

Entstanden als Lern- und Portfolioprojekt im Rahmen der
KI-Engineering/Softwareentwicklung-Ausbildung bei Masterschool.

## Über dieses Projekt

Der ursprüngliche Scraper (zwei einfache CLI-Skripte) ist vibecoded entstanden,
bevor ich Python gelernt habe - komplett mit KI-Unterstützung. Ich befinde mich
aktuell in der KI-Engineering-Ausbildung bei Masterschool und lerne dort aktiv
Python. Die Umstrukturierung in dieses Projekt (Modultrennung, GUI, Aufräumen
des Codes) entstand im selben Prozess - als Lernprojekt, an dem ich mich Stück
für Stück weiter durcharbeite.

![Platzhalter: Screenshot der Oberfläche](resources/screenshot-placeholder.png)

> Screenshots folgen, sobald die App das erste Mal auf allen drei
> Plattformen gebaut wurde.

## Funktionen

- Eigene Suchanfragen: Branche (z. B. "Fitnessstudio") und beliebig viele
  Städte frei eingeben – keine hartcodierte Städteliste mehr
- Ergebnisse live in einer sortierbaren Tabelle in der Oberfläche
- Start-/Stop-Button mit Fortschrittsanzeige, jederzeit unterbrechbar
- Automatische Suche nach der E-Mail-Adresse auf der Firmenwebsite
  (inkl. Impressum/Kontakt-Unterseiten), falls Google Maps selbst keine
  E-Mail anzeigt
- Export der Ergebnisse als Excel (.xlsx) oder CSV
- Läuft unter Windows, macOS und Linux
- Automatische ChromeDriver-Verwaltung im Hintergrund (webdriver-manager) –
  keine manuelle Dateiverwaltung nötig
- Klare Fehlermeldung mit Installationshinweis, falls Google Chrome fehlt,
  statt eines stillen Absturzes
- Nachvollziehbares Protokoll statt einfacher Konsolenausgaben (Logging)

## Voraussetzung

Die **einzige** Voraussetzung ist eine installierte Version von
**Google Chrome**: https://www.google.com/chrome/

Eine eigene Python-Installation ist für die fertige Anwendung **nicht**
nötig (siehe "Fertige Anwendung nutzen" unten). Python wird nur benötigt,
wenn man selbst am Quellcode arbeiten oder die Anwendung selbst bauen möchte.

## Fertige Anwendung nutzen (für Endnutzer ohne Python)

1. Die passende Datei für dein Betriebssystem aus dem
   [Releases-Bereich](../../releases) dieses Repositories herunterladen:
   - **Windows:** `GoogleMapsLeadScraper-windows.zip` entpacken und
     `GoogleMapsLeadScraper.exe` starten
   - **macOS:** `GoogleMapsLeadScraper-macos.zip` entpacken und
     `GoogleMapsLeadScraper.app` starten (beim ersten Start ggf. mit
     Rechtsklick → "Öffnen" bestätigen, da die App nicht von Apple
     signiert ist)
   - **Linux:** `GoogleMapsLeadScraper-linux.zip` entpacken, die Datei
     `GoogleMapsLeadScraper` ausführbar machen (`chmod +x GoogleMapsLeadScraper`)
     und starten
2. Google Chrome muss installiert sein – falls nicht, zeigt die App das
   direkt beim Start an.
3. Branche und mindestens eine Stadt eingeben, auf "Scraping starten"
   klicken.

> Hinweis: Die fertigen Installer-Dateien werden pro Plattform separat
> gebaut (siehe Abschnitt "Selbst bauen" unten) und im Releases-Bereich
> von GitHub bereitgestellt, sobald ein Release veröffentlicht wurde.

## Für Entwickler: Aus dem Quellcode starten

Vorausgesetzt wird Python 3.11 oder neuer.

```bash
# Repository klonen
git clone https://github.com/<dein-benutzername>/<dein-repo>.git
cd <dein-repo>

# Virtuelle Umgebung anlegen und aktivieren
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# Abhängigkeiten installieren
pip install -r requirements.txt

# Anwendung starten
python main.py
```

## Eigenen Installer bauen (PyInstaller)

Installer/EXE-Dateien werden **auf der jeweiligen Zielplattform** gebaut –
ein Windows-.exe entsteht also nur, wenn man das Build-Skript unter Windows
ausführt (entsprechend für macOS und Linux).

| Plattform | Skript                              |
|-----------|--------------------------------------|
| Windows   | `build_scripts\build_windows.bat`    |
| macOS     | `build_scripts/build_macos.sh`       |
| Linux     | `build_scripts/build_linux.sh`       |

Die fertige Anwendung liegt danach im Ordner `dist/`.

## Projektstruktur

```
gmaps-lead-scraper/
├── main.py                        # Einstiegspunkt der Anwendung
├── gmaps_scraper.spec             # PyInstaller-Konfiguration
├── requirements.txt               # Laufzeit-Abhängigkeiten
├── requirements-dev.txt           # + Abhängigkeiten zum Bauen der EXE
├── build_scripts/                 # Build-Skripte pro Plattform
├── src/gmaps_scraper/
│   ├── browser.py                 # Chrome-Erkennung & Selenium-Setup
│   ├── extractor.py               # Datenextraktion aus Google Maps
│   ├── email_enricher.py          # E-Mail-Suche auf Firmenwebsites
│   ├── scraper.py                 # Ablaufsteuerung (Suche, Scrollen, Sammeln)
│   ├── storage.py                 # Excel/CSV-Export
│   ├── logging_config.py          # Zentrales Logging statt print()
│   └── gui/
│       ├── app.py                 # Anwendungsstart (QApplication)
│       ├── main_window.py         # Hauptfenster (Eingabe, Tabelle, Export)
│       ├── worker.py              # Hintergrund-Thread fürs Scraping
│       └── log_bridge.py          # Verbindet Logging mit der Oberfläche
└── resources/                     # Icons, Screenshots
```

Die Trennung von Browser-Steuerung (`browser.py`), Datenextraktion
(`extractor.py`) und Speichern (`storage.py`) folgt dem Prinzip
"eine Datei, eine Verantwortung" und macht den Code leichter verständlich,
testbar und erweiterbar.

## Rechtlicher Disclaimer

**Dieses Projekt dient ausschließlich zu Lern- und Demonstrationszwecken.**

Das automatisierte Auslesen (Scraping) von Google Maps kann gegen die
[Google Nutzungsbedingungen](https://policies.google.com/terms) und die
[Google Maps Platform Nutzungsbedingungen](https://cloud.google.com/maps-platform/terms)
verstoßen. Wer dieses Tool nutzt, ist selbst dafür verantwortlich, sich vor
dem Einsatz über die aktuellen Nutzungsbedingungen von Google sowie über
geltendes Recht zu informieren – insbesondere:

- **Urheber- und Datenbankrecht:** Die auf Google Maps angezeigten Daten
  sind urheber- bzw. datenbankrechtlich geschützt.
- **DSGVO/Datenschutz:** Sobald personenbezogene Daten (z. B. E-Mail-Adressen
  natürlicher Personen) erfasst und weiterverarbeitet werden, gelten die
  Vorgaben der Datenschutz-Grundverordnung (DSGVO), u. a. zu Rechtsgrundlage,
  Informationspflichten und Speicherbegrenzung.
- **Wettbewerbsrecht (UWG):** Die Nutzung gesammelter Kontaktdaten für
  unaufgeforderte Werbung (Cold-Mailing, Cold-Calling) ohne vorherige
  Einwilligung ist in Deutschland grundsätzlich unzulässig (§ 7 UWG).

Die Autorin/der Autor dieses Projekts übernimmt keine Haftung für die Art
und Weise, wie dieses Tool von Dritten eingesetzt wird. Nutzung auf eigene
Verantwortung.

## Lizenz

Der Quellcode dieses Projekts steht unter der [MIT-Lizenz](LICENSE).
Die Nutzung der von Google Maps bezogenen Daten unterliegt davon unabhängig
den oben genannten Nutzungsbedingungen von Google.
