"""
Sucht die E-Mail-Adresse auf der Firmenwebsite, da Google Maps selbst keine
E-Mail anzeigt (nur Website). Erst Startseite (mailto-Links + Freitext,
inkl. simpler De-Obfuskation wie "info (at) firma (dot) de"), dann bei
Bedarf Impressum/Kontakt-Unterseiten. Synchron mit requests, weil das im
GUI-Worker-Thread läuft und kein eigener asyncio-Loop nötig ist.
"""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .logging_config import get_logger

logger = get_logger(__name__)

EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

# Häufige Verschleierungen von E-Mail-Adressen auf Websites
OBFUSCATION_PATTERNS = [
    (re.compile(r"\s*\[?\(?\s*at\s*\)?\]?\s*", re.I), "@"),
    (re.compile(r"\bät\b", re.I), "@"),
    (re.compile(r"\s*\[?\(?\s*dot\s*\)?\]?\s*", re.I), "."),
    (re.compile(r"\bpunkt\b", re.I), "."),
]

INVALID_EMAIL_PATTERNS = (
    r"\.(png|jpe?g|gif|pdf|svg|webp)$",
    r"^(test|example|placeholder)@",
    r"@(example|test|placeholder)\.",
    r"@(localhost|127\.0\.0\.1)",
    r"sentry\.io",
    r"wixpress\.com",
)

FALLBACK_PATHS = ("/impressum", "/kontakt", "/contact", "/imprint", "/about", "/team")
ANCHOR_KEYWORDS = ("impressum", "kontakt", "contact", "imprint", "about")

PRIORITY_PREFIXES = (
    "info@", "kontakt@", "contact@", "office@", "hello@",
    "mail@", "support@", "service@",
)

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
}


def _deobfuscate(text: str) -> str:
    for pattern, replacement in OBFUSCATION_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _is_valid_email(email: str) -> bool:
    email_lower = email.lower()
    if any(re.search(pattern, email_lower) for pattern in INVALID_EMAIL_PATTERNS):
        return False
    return True


def _extract_emails_from_html(html: str) -> set[str]:
    emails: set[str] = set()
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")

    # 1) mailto-Links (zuverlässigste Quelle)
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if href.lower().startswith("mailto:"):
            address = href[7:].split("?")[0].strip()
            for match in EMAIL_PATTERN.findall(_deobfuscate(address)):
                if _is_valid_email(match):
                    emails.add(match.lower())

    # 2) Freitext der Seite (z. B. im Footer)
    text = _deobfuscate(soup.get_text(" ", strip=True))
    for match in EMAIL_PATTERN.findall(text):
        if _is_valid_email(match):
            emails.add(match.lower())

    return emails


def _best_email(emails: set[str], website_url: str) -> str:
    if not emails:
        return ""

    host = urlparse(website_url).netloc.lower().removeprefix("www.")
    same_domain = [e for e in emails if e.split("@")[-1].endswith(host)] or list(emails)

    for prefix in PRIORITY_PREFIXES:
        for email in same_domain:
            if email.startswith(prefix):
                return email

    return sorted(same_domain, key=len)[0]


def find_email_for_website(website_url: str, timeout: float = 8.0) -> str:
    """Sucht eine passende E-Mail für die Website. Leerer String, wenn nichts gefunden wurde."""
    if not website_url or "google.com" in website_url:
        return ""

    session = requests.Session()
    session.headers.update(REQUEST_HEADERS)

    urls_to_try = [website_url]

    try:
        response = session.get(website_url, timeout=timeout, allow_redirects=True)
        if response.status_code == 200 and "html" in response.headers.get("Content-Type", ""):
            emails = _extract_emails_from_html(response.text)
            if emails:
                return _best_email(emails, website_url)

            # Impressum/Kontakt-Links auf der Startseite suchen
            try:
                soup = BeautifulSoup(response.text, "lxml")
            except Exception:
                soup = BeautifulSoup(response.text, "html.parser")

            for link in soup.find_all("a", href=True):
                anchor_text = link.get_text(" ", strip=True).lower()
                if any(keyword in anchor_text for keyword in ANCHOR_KEYWORDS):
                    urls_to_try.append(urljoin(website_url, link["href"]))

        parsed = urlparse(website_url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        urls_to_try.extend(urljoin(base, path) for path in FALLBACK_PATHS)

    except requests.RequestException as exc:
        logger.debug("Startseite %s nicht erreichbar: %s", website_url, exc)

    # Deduplizieren, Startseite war schon dran
    seen = {website_url}
    for url in urls_to_try[1:6]:  # maximal 5 zusätzliche Unterseiten prüfen
        if url in seen:
            continue
        seen.add(url)
        try:
            response = session.get(url, timeout=timeout, allow_redirects=True)
            if response.status_code == 200 and "html" in response.headers.get("Content-Type", ""):
                emails = _extract_emails_from_html(response.text)
                if emails:
                    return _best_email(emails, website_url)
        except requests.RequestException as exc:
            logger.debug("Unterseite %s nicht erreichbar: %s", url, exc)
            continue

    return ""
