#!/usr/bin/env python3
"""Einstiegspunkt der Anwendung - auch das Ziel für PyInstaller beim Bauen der EXE (siehe build_scripts/)."""

import os
import sys

# src/ in den Python-Pfad aufnehmen, falls das Paket nicht via `pip install -e .` installiert wurde
SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from gmaps_scraper.gui.app import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
