"""Startet die PySide6-Anwendung (QApplication-Setup, getrennt vom eigentlichen Fenster)."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from gmaps_scraper.logging_config import setup_logging

from .main_window import MainWindow


def main() -> int:
    setup_logging()

    app = QApplication(sys.argv)
    app.setApplicationName("Google Maps Lead Scraper")
    app.setOrganizationName("Airdinsh")

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
