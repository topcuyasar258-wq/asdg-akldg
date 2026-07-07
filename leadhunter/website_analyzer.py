"""İşletmenin web sitesini ve sosyal medya varlığını analiz eder.

Ajans gözüyle bakılır: sitesi olmayan, SSL'siz, mobil uyumsuz, yavaş veya
sosyal medyası zayıf işletmeler potansiyel müşteridir.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

SOCIAL_PATTERNS = {
    "instagram": re.compile(r"instagram\.com/([A-Za-z0-9_.]+)", re.I),
    "facebook": re.compile(r"facebook\.com/([A-Za-z0-9_.\-]+)", re.I),
    "twitter": re.compile(r"(?:twitter|x)\.com/([A-Za-z0-9_]+)", re.I),
    "linkedin": re.compile(r"linkedin\.com/(?:company|in)/([A-Za-z0-9_\-]+)", re.I),
    "youtube": re.compile(r"youtube\.com/(?:@|channel/|c/)([A-Za-z0-9_\-]+)", re.I),
}

# Sosyal medya linklerinde lead açısından anlamsız olan sayfalar
_SOCIAL_IGNORE = {"sharer", "share", "intent", "plugins", "policies", "help"}

# Site kurmak yerine hazır platform kullananlar da web tasarım adayıdır
FREE_PLATFORM_HOSTS = (
    "instagram.com",
    "facebook.com",
    "wa.me",
    "api.whatsapp.com",
    "linktr.ee",
    "sites.google.com",
    "blogspot.com",
    "wordpress.com",
    "wixsite.com",
)


@dataclass
class WebsiteReport:
    has_website: bool = False
    is_free_platform: bool = False   # site yerine instagram/linktree vb.
    reachable: bool = False
    has_ssl: bool = False
    mobile_friendly: bool = False
    load_time_seconds: float | None = None
    title: str = ""
    socials: dict[str, str] = field(default_factory=dict)
    error: str = ""


def analyze_website(url: str) -> WebsiteReport:
    report = WebsiteReport()
    if not url:
        return report

    host = urlparse(url).netloc.lower()
    if any(host.endswith(p) or p in url.lower() for p in FREE_PLATFORM_HOSTS):
        report.is_free_platform = True
        # Instagram/Facebook linkini sosyal medya varlığı olarak da say
        _extract_socials(url, report.socials)
        return report

    report.has_website = True
    try:
        start = time.time()
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=15,
            allow_redirects=True,
        )
        report.load_time_seconds = round(time.time() - start, 2)
        report.reachable = resp.status_code < 400
        report.has_ssl = resp.url.startswith("https://")

        if report.reachable and "text/html" in resp.headers.get("Content-Type", "html"):
            soup = BeautifulSoup(resp.text, "html.parser")
            if soup.title and soup.title.string:
                report.title = soup.title.string.strip()[:100]
            viewport = soup.find("meta", attrs={"name": "viewport"})
            report.mobile_friendly = viewport is not None
            _extract_socials(resp.text, report.socials)
    except requests.RequestException as exc:
        report.error = type(exc).__name__
        log.debug("Site erişilemedi (%s): %s", url, exc)

    return report


def _extract_socials(html: str, socials: dict[str, str]) -> None:
    for network, pattern in SOCIAL_PATTERNS.items():
        if network in socials:
            continue
        for match in pattern.finditer(html):
            handle = match.group(1)
            if handle.lower() not in _SOCIAL_IGNORE:
                socials[network] = handle
                break
