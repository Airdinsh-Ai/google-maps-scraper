"""Chrome-Erkennung und Aufbau des Selenium-WebDrivers (inkl. automatischer ChromeDriver-Verwaltung)."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from .logging_config import get_logger

logger = get_logger(__name__)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


class ChromeNotFoundError(RuntimeError):
    """Kein Chrome auf dem System gefunden. Die GUI fängt das ab und zeigt einen Installationshinweis."""


@dataclass
class ChromeInfo:
    """Ergebnis der Chrome-Erkennung."""

    found: bool
    path: str | None = None


def find_chrome_binary() -> ChromeInfo:
    """Sucht die Chrome-Installation an den üblichen Orten (Windows/macOS/Linux) bzw. im PATH."""
    system = platform.system()

    candidates: list[str] = []

    if system == "Windows":
        program_files = [
            os.environ.get("PROGRAMFILES", r"C:\Program Files"),
            os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
            os.environ.get("LOCALAPPDATA", ""),
        ]
        for base in program_files:
            if base:
                candidates.append(os.path.join(base, "Google", "Chrome", "Application", "chrome.exe"))
        # Zusätzlich im PATH suchen
        which_result = shutil.which("chrome") or shutil.which("chrome.exe")
        if which_result:
            candidates.append(which_result)

    elif system == "Darwin":  # macOS
        candidates.append("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        candidates.append(
            os.path.expanduser(
                "~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            )
        )

    else:  # Linux und alles andere
        for exe_name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
            which_result = shutil.which(exe_name)
            if which_result:
                candidates.append(which_result)

    for path in candidates:
        if path and os.path.isfile(path):
            logger.info("Google Chrome gefunden: %s", path)
            return ChromeInfo(found=True, path=path)

    logger.warning("Google Chrome konnte auf diesem System nicht gefunden werden.")
    return ChromeInfo(found=False, path=None)


def get_chrome_install_hint() -> str:
    """Für Endnutzer verständlicher Installationshinweis, wenn Chrome fehlt."""
    return (
        "Google Chrome wurde auf diesem Computer nicht gefunden.\n\n"
        "Der Scraper benötigt eine installierte Chrome-Version, um Google Maps "
        "im Hintergrund zu steuern.\n\n"
        "Bitte installiere Google Chrome kostenlos von:\n"
        "https://www.google.com/chrome/\n\n"
        "Starte anschließend das Programm erneut."
    )


def build_chrome_options(headless: bool = False) -> webdriver.ChromeOptions:
    """Erstellt die Chrome-Optionen inkl. Performance- und Anti-Detection-Einstellungen."""
    options = webdriver.ChromeOptions()

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-notifications")
    options.add_argument(f"user-agent={DEFAULT_USER_AGENT}")

    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    if headless:
        options.add_argument("--headless=new")

    return options


def create_driver(headless: bool = False) -> webdriver.Chrome:
    """Baut einen einsatzbereiten Chrome-WebDriver auf (ChromeDriver-Download via webdriver-manager)."""
    chrome_info = find_chrome_binary()
    if not chrome_info.found:
        raise ChromeNotFoundError(get_chrome_install_hint())

    logger.info("Initialisiere ChromeDriver über webdriver-manager ...")
    options = build_chrome_options(headless=headless)

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as exc:
        logger.exception("ChromeDriver konnte nicht gestartet werden.")
        raise RuntimeError(
            "ChromeDriver konnte nicht gestartet werden. Bitte stelle sicher, "
            "dass Google Chrome aktuell ist und versuche es erneut.\n\n"
            f"Technische Details: {exc}"
        ) from exc

    # Anti-Detection: verschleiert typische Merkmale automatisierter Browser
    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                """
            },
        )
    except Exception:
        # Nicht kritisch - Scraping funktioniert auch ohne diesen Schritt
        logger.debug("Anti-Detection-Skript konnte nicht injiziert werden (nicht kritisch).")

    if not headless:
        driver.maximize_window()

    logger.info("ChromeDriver erfolgreich initialisiert.")
    return driver
