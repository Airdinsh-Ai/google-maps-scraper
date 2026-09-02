"""Liest Firmendaten aus einer bereits geladenen Google-Maps-Detailseite (bekommt nur das Selenium-driver-Objekt)."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .logging_config import get_logger

logger = get_logger(__name__)

# E-Mails, die offensichtlich keine echten Kontaktadressen sind
EMAIL_BLACKLIST = (
    "noreply", "no-reply", "example.com", "test@", "admin@example",
    "support@wix", "info@sentry", "@placeholder", "your-email",
)

EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
STRICT_EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

NAME_SELECTORS = (
    '//h1[@class="DUwDvf lfPIob"]',
    '//h1[contains(@class,"fontHeadlineLarge")]',
    '//div[@role="main"]//h1',
    "//h1",
)

ADDRESS_SELECTORS = (
    '//button[@data-item-id="address"]//div[contains(@class, "fontBodyMedium")]',
    '//div[@data-item-id="address"]//div',
    '//button[contains(@aria-label, "Adresse")]',
)

PHONE_SELECTORS = (
    '//button[starts-with(@data-item-id, "phone:tel:")]//div[contains(@class, "fontBodyMedium")]',
    '//a[starts-with(@href, "tel:")]',
    '//button[contains(@aria-label, "Telefon")]//div',
)

WEBSITE_SELECTORS = (
    '//a[@data-item-id="authority"]',
    '//a[contains(@aria-label, "Website")]',
    '//a[contains(@href, "http") and not(contains(@href, "google.com"))]',
)


@dataclass
class BusinessRecord:
    """Ein einzelner Datensatz für ein Unternehmen."""

    name: str
    address: str = ""
    phone: str = ""
    website: str = ""
    email: str = ""

    def to_dict(self) -> dict:
        return {
            "Firmenname": self.name,
            "Adresse": self.address or "N/A",
            "Telefonnummer": self.phone or "N/A",
            "Webseite": self.website or "N/A",
            "E-Mail-Adresse": self.email or "N/A",
        }


def is_valid_email(email: str) -> bool:
    """Prüft, ob eine E-Mail-Adresse plausibel und nicht auf der Sperrliste ist."""
    if not email or "@" not in email:
        return False

    email_lower = email.lower()
    if any(bad in email_lower for bad in EMAIL_BLACKLIST):
        return False

    return bool(STRICT_EMAIL_PATTERN.match(email))


def _first_matching_text(driver, selectors: tuple[str, ...], min_length: int = 1) -> str:
    """Probiert mehrere XPath-Selektoren nacheinander durch (Fallback-Kette)."""
    for selector in selectors:
        try:
            elements = driver.find_elements(By.XPATH, selector)
            for element in elements:
                text = element.text.strip()
                if text and len(text) >= min_length:
                    return text
        except Exception:
            continue
    return ""


class BusinessPageExtractor:
    """Liest die Daten einer einzelnen Google-Maps-Unternehmensseite aus."""

    def __init__(self, driver, wait_timeout: float = 15.0):
        self.driver = driver
        self.wait = WebDriverWait(driver, wait_timeout)

    def wait_for_page_ready(self) -> bool:
        """Wartet, bis mindestens die Überschrift der Seite geladen ist."""
        try:
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
            return True
        except TimeoutException:
            logger.warning("Timeout beim Laden der Detailseite.")
            return False

    def extract_name(self) -> str:
        """Extrahiert den Firmennamen mit mehreren Fallback-Strategien."""
        name = _first_matching_text(self.driver, NAME_SELECTORS, min_length=2)
        if name:
            return name

        # Letzter Fallback: Titel des Browser-Tabs
        try:
            title = self.driver.title
            if title and title != "Google Maps":
                return title.split(" - ")[0].strip()
        except Exception:
            pass

        return ""

    def extract_address(self) -> str:
        return _first_matching_text(self.driver, ADDRESS_SELECTORS, min_length=5)

    def extract_phone(self) -> str:
        for selector in PHONE_SELECTORS:
            try:
                element = self.driver.find_element(By.XPATH, selector)
                if element.tag_name == "a":
                    phone = (element.get_attribute("href") or "").replace("tel:", "")
                else:
                    phone = element.text.strip()
                if phone and len(phone) > 5:
                    return phone
            except Exception:
                continue
        return ""

    def extract_website(self) -> str:
        for selector in WEBSITE_SELECTORS:
            try:
                element = self.driver.find_element(By.XPATH, selector)
                website = element.get_attribute("href")
                if website and "google.com" not in website and "/maps" not in website:
                    return website
            except Exception:
                continue
        return ""

    def extract(self) -> BusinessRecord | None:
        """Liest einen vollständigen Datensatz. None, wenn nicht mal ein Firmenname gefunden wurde."""
        if not self.wait_for_page_ready():
            return None

        # kurze Pause, damit Adresse/Telefon (laden verzögert nach) im DOM stehen
        time.sleep(1.5)

        name = self.extract_name()
        if not name:
            return None

        return BusinessRecord(
            name=name,
            address=self.extract_address(),
            phone=self.extract_phone(),
            website=self.extract_website(),
        )
