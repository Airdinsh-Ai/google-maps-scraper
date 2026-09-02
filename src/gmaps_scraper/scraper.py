"""
Orchestriert den Scraping-Ablauf: Browser starten, Google Maps durchsuchen,
Links sammeln, jede Unternehmensseite öffnen, Daten extrahieren, E-Mail
nachrecherchieren.

Kennt weder GUI noch Kommandozeile, sondern meldet sich nur über Callbacks
(on_progress, on_record) nach außen - damit kann die GUI (oder ein Testskript)
den Fortschritt live mitverfolgen.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .browser import ChromeNotFoundError, create_driver
from .email_enricher import find_email_for_website
from .extractor import BusinessPageExtractor, BusinessRecord
from .logging_config import get_logger

logger = get_logger(__name__)


class ScrapingStopped(Exception):
    """Interne Signal-Exception, um das Scraping sauber abzubrechen (Stop-Button)."""


@dataclass
class SearchQuery:
    """Eine einzelne Kombination aus Branche und Stadt, z. B. 'Fitnessstudio' + 'Köln'."""

    branche: str
    stadt: str

    @property
    def search_term(self) -> str:
        return f"{self.branche.strip()} {self.stadt.strip()}".strip()

    def __str__(self) -> str:
        return self.search_term


@dataclass
class ScrapeOptions:
    """Einstellbare Parameter für einen Scraping-Lauf."""

    scroll_count: int = 20
    fetch_emails: bool = True
    headless: bool = False
    pause_between_queries: float = 3.0


# Callback-Signaturen (rein dokumentarisch, Python prüft das nicht zur Laufzeit):
#   on_progress(current: int, total: int, message: str) -> None
#   on_record(record: BusinessRecord) -> None
#   on_log(level: str, message: str) -> None
ProgressCallback = Callable[[int, int, str], None]
RecordCallback = Callable[[BusinessRecord], None]


def _noop_progress(current: int, total: int, message: str) -> None:
    pass


def _noop_record(record: BusinessRecord) -> None:
    pass


class GoogleMapsScraper:
    """Steuert einen kompletten Scraping-Lauf über mehrere Suchanfragen hinweg."""

    def __init__(
        self,
        options: Optional[ScrapeOptions] = None,
        on_progress: Optional[ProgressCallback] = None,
        on_record: Optional[RecordCallback] = None,
    ):
        self.options = options or ScrapeOptions()
        self.on_progress = on_progress or _noop_progress
        self.on_record = on_record or _noop_record

        self._stop_event = threading.Event()
        self.driver = None
        self._cookies_handled = False

    def request_stop(self) -> None:
        """Wird vom Stop-Button in der GUI aufgerufen (thread-sicher)."""
        logger.info("Stop angefordert - Scraping wird nach dem aktuellen Eintrag beendet.")
        self._stop_event.set()

    def _check_stop(self) -> None:
        if self._stop_event.is_set():
            raise ScrapingStopped()

    def run(self, queries: list[SearchQuery]) -> list[BusinessRecord]:
        """Läuft alle Suchanfragen ab. Bei Stop-Request werden die bisher gesammelten Records zurückgegeben."""
        all_records: list[BusinessRecord] = []
        self._stop_event.clear()

        try:
            self.driver = create_driver(headless=self.options.headless)
        except ChromeNotFoundError:
            raise  # von der GUI gezielt abgefangen und angezeigt
        except Exception:
            logger.exception("Browser konnte nicht gestartet werden.")
            raise

        try:
            for query_index, query in enumerate(queries, start=1):
                self._check_stop()
                logger.info("Suchanfrage %s/%s: %s", query_index, len(queries), query)
                self.on_progress(0, 0, f"Suche: {query}")

                try:
                    links = self._collect_business_links(query.search_term)
                except ScrapingStopped:
                    raise
                except Exception:
                    logger.exception("Fehler beim Sammeln der Links für '%s'", query)
                    continue

                logger.info("%s Ergebnisse gefunden für '%s'", len(links), query)

                for link_index, link in enumerate(links, start=1):
                    self._check_stop()
                    self.on_progress(
                        link_index, len(links), f"{query}: Eintrag {link_index}/{len(links)}"
                    )

                    record = self._scrape_single_business(link)
                    if record:
                        all_records.append(record)
                        self.on_record(record)

                if query_index < len(queries):
                    time.sleep(self.options.pause_between_queries)

        except ScrapingStopped:
            logger.info("Scraping wurde vom Nutzer gestoppt. %s Einträge gesammelt.", len(all_records))
        finally:
            self._quit_driver()

        return all_records

    def _handle_cookie_banner(self) -> None:
        """Akzeptiert Googles Cookie-/Einwilligungsseite, falls sie erscheint (nur beim ersten Aufruf nötig)."""
        cookie_selectors = [
            '//button[@aria-label="Alle akzeptieren"]',
            '//button[contains(text(), "Alle akzeptieren")]',
            '//button[contains(text(), "Accept all")]',
        ]
        for selector in cookie_selectors:
            try:
                button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                button.click()
                logger.info("Cookie-Einwilligung akzeptiert.")
                time.sleep(2)
                return
            except TimeoutException:
                continue
        logger.debug("Keine Cookie-Einwilligungsseite gefunden (oder bereits akzeptiert).")

    def _collect_business_links(self, search_term: str) -> list[str]:
        """Führt eine Google-Maps-Suche aus und sammelt alle Ergebnis-Links per Scrollen."""
        self.driver.get("https://www.google.com/maps")
        time.sleep(3)

        if not self._cookies_handled:
            self._handle_cookie_banner()
            self._cookies_handled = True

        search_input = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'input[name="q"]'))
        )
        search_input.clear()
        search_input.send_keys(search_term)
        search_input.send_keys(Keys.ENTER)
        time.sleep(4)

        try:
            scrollable = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//div[@role="feed"]'))
            )
        except TimeoutException:
            logger.info("Kein Ergebnis-Feed gefunden - vermutlich keine Treffer für '%s'.", search_term)
            return []

        all_links: set[str] = set()
        no_new_links_count = 0

        for scroll_index in range(self.options.scroll_count):
            self._check_stop()

            self.driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollHeight", scrollable
            )
            time.sleep(1.8)

            previous_count = len(all_links)
            try:
                results = self.driver.find_elements(By.XPATH, '//a[contains(@href, "/maps/place/")]')
                for result in results:
                    try:
                        href = result.get_attribute("href")
                        if href and "/maps/place/" in href:
                            all_links.add(href.split("?")[0])
                    except StaleElementReferenceException:
                        continue
            except Exception:
                logger.debug("Fehler beim Scrollen (Versuch %s), fahre fort.", scroll_index + 1)
                continue

            if len(all_links) > previous_count:
                no_new_links_count = 0
            else:
                no_new_links_count += 1
                if no_new_links_count >= 3:
                    break

        return list(all_links)

    def _scrape_single_business(self, link: str) -> BusinessRecord | None:
        """Öffnet eine Unternehmensseite und extrahiert alle verfügbaren Daten."""
        try:
            self.driver.get(link)
            time.sleep(2)

            extractor = BusinessPageExtractor(self.driver)
            record = extractor.extract()

            if record is None:
                logger.debug("Kein Firmenname gefunden für %s - übersprungen.", link)
                return None

            if self.options.fetch_emails and record.website:
                email = find_email_for_website(record.website)
                if email:
                    record.email = email
                    logger.info("E-Mail gefunden für '%s': %s", record.name, email)

            logger.info("Erfolgreich extrahiert: %s", record.name)
            return record

        except ScrapingStopped:
            raise
        except Exception:
            logger.exception("Fehler beim Verarbeiten von %s", link)
            return None

    def _quit_driver(self) -> None:
        if self.driver is not None:
            try:
                self.driver.quit()
                logger.info("Browser geschlossen.")
            except Exception:
                logger.debug("Browser war bereits geschlossen.")
            finally:
                self.driver = None
