"""
QThread-Wrapper um den GoogleMapsScraper. Selenium-Aufrufe dauern mehrere
Sekunden pro Seite - liefe das im GUI-Thread, würde das Fenster einfrieren.
Der Worker läuft deshalb separat und meldet Fortschritt/Ergebnisse per
Qt-Signal zurück.
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from gmaps_scraper.browser import ChromeNotFoundError
from gmaps_scraper.extractor import BusinessRecord
from gmaps_scraper.logging_config import get_logger
from gmaps_scraper.scraper import GoogleMapsScraper, ScrapeOptions, SearchQuery

logger = get_logger(__name__)


class ScraperWorker(QThread):
    """Führt den Scraping-Lauf im Hintergrund aus."""

    progress_changed = Signal(int, int, str)  # current, total, Statustext
    record_found = Signal(object)  # BusinessRecord
    finished_ok = Signal(int)  # Anzahl gefundener Einträge
    failed = Signal(str)  # Fehlermeldung für den Nutzer
    chrome_missing = Signal(str)  # Installationshinweis

    def __init__(self, queries: list[SearchQuery], options: ScrapeOptions, parent=None):
        super().__init__(parent)
        self.queries = queries
        self.options = options
        self._scraper: GoogleMapsScraper | None = None

    def run(self) -> None:
        """Läuft im Hintergrund-Thread - nicht direkt aufrufen, sondern .start()."""
        self._scraper = GoogleMapsScraper(
            options=self.options,
            on_progress=self._emit_progress,
            on_record=self._emit_record,
        )

        try:
            records = self._scraper.run(self.queries)
            self.finished_ok.emit(len(records))
        except ChromeNotFoundError as exc:
            logger.error("Chrome nicht gefunden: %s", exc)
            self.chrome_missing.emit(str(exc))
        except Exception as exc:
            logger.exception("Scraping mit Fehler beendet.")
            self.failed.emit(str(exc))

    def request_stop(self) -> None:
        """Wird vom Stop-Button im GUI-Thread aufgerufen."""
        if self._scraper is not None:
            self._scraper.request_stop()

    # übersetzt die (Qt-unabhängigen) Callbacks aus scraper.py in Qt-Signale
    def _emit_progress(self, current: int, total: int, message: str) -> None:
        self.progress_changed.emit(current, total, message)

    def _emit_record(self, record: BusinessRecord) -> None:
        self.record_found.emit(record)
