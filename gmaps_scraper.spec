# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller-Konfiguration für den Google Maps Lead Scraper.

Diese Datei wird von PyInstaller gelesen, wenn man aufruft:
    pyinstaller gmaps_scraper.spec

Sie baut auf ALLEN drei Plattformen (Windows/macOS/Linux) eine eigenständige
Anwendung, die keine separate Python-Installation beim Endnutzer benötigt.
PyInstaller muss dabei jeweils AUF der Zielplattform ausgeführt werden -
ein Windows-.exe entsteht also nur, wenn man dieses Kommando unter Windows
ausführt (siehe build_scripts/ für die passenden Skripte pro Plattform).
"""

import sys

block_cipher = None

app_name = "GoogleMapsLeadScraper"
icon_file = None
if sys.platform == "win32":
    icon_file = "resources/icon.ico"
elif sys.platform == "darwin":
    icon_file = "resources/icon.icns"

a = Analysis(
    ["main.py"],
    pathex=["src"],
    binaries=[],
    datas=[],
    hiddenimports=[
        "selenium",
        "webdriver_manager",
        "webdriver_manager.chrome",
        "bs4",
        "lxml",
        "openpyxl",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Kein Konsolenfenster - reine GUI-Anwendung
    icon=icon_file,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=app_name,
)

# Auf macOS zusätzlich ein .app-Bundle erzeugen
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name=f"{app_name}.app",
        icon=icon_file,
        bundle_identifier="de.airdinsh.gmapsleadscraper",
        info_plist={
            "NSHighResolutionCapable": "True",
            "CFBundleShortVersionString": "1.0.0",
        },
    )
