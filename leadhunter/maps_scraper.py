"""Google Maps web arayüzünden ücretsiz veri toplama.

API anahtarı ve kredi kartı GEREKTİRMEZ. Playwright ile gerçek bir tarayıcı
açıp Google Maps arama sonuçlarını ve işletme sayfalarını okur: isim,
telefon, adres, puan, yorum sayısı, web sitesi ve son yorumlar.

Not: Google arayüz sınıf adlarını zaman zaman değiştirir; bu yüzden her
alan için aria-label tabanlı yedek seçiciler de denenir ve tüm çıkarımlar
"elinden geleni yap" mantığıyla çalışır (bir alan okunamazsa boş kalır,
tarama durmaz).
"""

from __future__ import annotations

import logging
import os
import re
import time
import urllib.parse

from playwright.sync_api import Error as PWError, Page, TimeoutError as PWTimeout, sync_playwright

from .places import Business, Review

log = logging.getLogger(__name__)

PLACE_ID_RE = re.compile(r"0x[0-9a-f]+:0x[0-9a-f]+")
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


class MapsScraper:
    """PlacesClient ile aynı arayüz: .search(query, max_results) -> [Business]"""

    def __init__(self, language: str = "tr", region: str = "tr"):
        self.language = language

    def search(self, query: str, max_results: int = 20) -> list[Business]:
        businesses: list[Business] = []
        with sync_playwright() as p:
            launch_kwargs: dict = {
                "headless": True,
                "args": [
                    "--disable-blink-features=AutomationControlled",
                    f"--lang={self.language}-TR",
                ],
            }
            # Kurumsal proxy arkasında test için (normal kullanımda gerekmez)
            if os.environ.get("SCRAPER_PROXY"):
                launch_kwargs["proxy"] = {"server": os.environ["SCRAPER_PROXY"]}
            if os.environ.get("CHROMIUM_PATH"):
                launch_kwargs["executable_path"] = os.environ["CHROMIUM_PATH"]

            browser = p.chromium.launch(**launch_kwargs)
            context = browser.new_context(
                locale=f"{self.language}-TR",
                user_agent=USER_AGENT,
                viewport={"width": 1366, "height": 900},
                ignore_https_errors=os.environ.get("SCRAPER_IGNORE_TLS") == "1",
            )
            # Çerez onay duvarını baştan geçmek için
            context.add_cookies(
                [
                    {"name": "CONSENT", "value": "YES+", "domain": ".google.com", "path": "/"},
                    {"name": "SOCS", "value": "CAESEwgDEgk2NzM5OTg2NzQaAnRyIAEaBgiA_LyaBg", "domain": ".google.com", "path": "/"},
                ]
            )
            page = context.new_page()
            try:
                url = (
                    "https://www.google.com/maps/search/"
                    + urllib.parse.quote(query)
                    + f"?hl={self.language}"
                )
                page.goto(url, wait_until="domcontentloaded", timeout=60_000)
                self._dismiss_consent(page)

                if "/maps/place/" in page.url:
                    # Sorgu tek bir işletmeye yönlendirdi
                    b = self._scrape_place(page, page.url)
                    if b:
                        businesses.append(b)
                else:
                    links = self._collect_place_links(page, max_results)
                    log.info("'%s' sorgusu: %d işletme linki bulundu", query, len(links))
                    for href in links:
                        try:
                            b = self._scrape_place(page, href)
                            if b:
                                businesses.append(b)
                        except (PWTimeout, PWError) as exc:
                            log.warning("İşletme sayfası okunamadı: %s (%s)", href[:80], type(exc).__name__)
                        time.sleep(1.5)  # nazik tarama
            except (PWTimeout, PWError) as exc:
                log.error("'%s' sorgusunda tarayıcı hatası: %s", query, exc)
            finally:
                browser.close()

        log.info("'%s' sorgusu: %d işletme toplandı", query, len(businesses))
        return businesses[:max_results]

    # ------------------------------------------------------------------

    @staticmethod
    def _dismiss_consent(page: Page) -> None:
        try:
            btn = page.locator(
                'button:has-text("Tümünü kabul et"), button:has-text("Accept all")'
            ).first
            if btn.is_visible(timeout=3_000):
                btn.click()
                page.wait_for_load_state("domcontentloaded", timeout=15_000)
        except (PWTimeout, PWError):
            pass

    @staticmethod
    def _collect_place_links(page: Page, max_results: int) -> list[str]:
        links: list[str] = []
        seen: set[str] = set()
        try:
            feed = page.locator('div[role="feed"]').first
            feed.wait_for(state="visible", timeout=20_000)
        except (PWTimeout, PWError):
            log.warning("Sonuç listesi görünmedi (sayfa: %s)", page.url[:100])
            return links

        idle_rounds = 0
        while len(links) < max_results and idle_rounds < 4:
            for el in page.locator('a[href*="/maps/place/"]').all():
                href = el.get_attribute("href") or ""
                key = href.split("?")[0]
                if href and key not in seen:
                    seen.add(key)
                    links.append(href)
            before = len(links)
            feed.evaluate("el => el.scrollBy(0, 3000)")
            page.wait_for_timeout(1_500)
            idle_rounds = idle_rounds + 1 if len(links) == before else 0

        return links[:max_results]

    def _scrape_place(self, page: Page, url: str) -> Business | None:
        if page.url.split("?")[0] != url.split("?")[0]:
            page.goto(url, wait_until="domcontentloaded", timeout=45_000)
        name_el = page.locator("h1").first
        name_el.wait_for(state="visible", timeout=20_000)
        name = name_el.inner_text().strip()
        if not name:
            return None

        m = PLACE_ID_RE.search(page.url) or PLACE_ID_RE.search(url)
        place_id = m.group(0) if m else f"name:{name.lower()}"

        return Business(
            place_id=place_id,
            name=name,
            address=self._item_text(page, "address"),
            phone=self._extract_phone(page),
            website=self._extract_website(page),
            rating=self._extract_rating(page),
            review_count=self._extract_review_count(page),
            maps_url=page.url.split("?")[0],
            reviews=self._extract_reviews(page),
        )

    @staticmethod
    def _item_text(page: Page, item_id: str) -> str:
        try:
            el = page.locator(f'[data-item-id="{item_id}"]').first
            label = el.get_attribute("aria-label", timeout=3_000) or ""
            return label.split(":", 1)[-1].strip() if ":" in label else el.inner_text().strip()
        except (PWTimeout, PWError):
            return ""

    @staticmethod
    def _extract_phone(page: Page) -> str:
        try:
            el = page.locator('[data-item-id^="phone:tel:"]').first
            raw = el.get_attribute("data-item-id", timeout=3_000) or ""
            return raw.removeprefix("phone:tel:").strip()
        except (PWTimeout, PWError):
            return ""

    @staticmethod
    def _extract_website(page: Page) -> str:
        try:
            el = page.locator('a[data-item-id="authority"]').first
            return el.get_attribute("href", timeout=3_000) or ""
        except (PWTimeout, PWError):
            return ""

    @staticmethod
    def _extract_rating(page: Page) -> float | None:
        for attempt in (
            lambda: page.locator('div.F7nice span[aria-hidden="true"]').first.inner_text(timeout=3_000),
            lambda: (
                page.locator('span[role="img"][aria-label*="yıldız"], span[role="img"][aria-label*="star"]')
                .first.get_attribute("aria-label", timeout=3_000)
            ),
        ):
            try:
                text = attempt() or ""
                m = re.search(r"(\d[.,]\d)", text)
                if m:
                    return float(m.group(1).replace(",", "."))
            except (PWTimeout, PWError):
                continue
        return None

    @staticmethod
    def _extract_review_count(page: Page) -> int:
        try:
            el = page.locator('span[aria-label*="yorum"], span[aria-label*="review"]').first
            label = el.get_attribute("aria-label", timeout=3_000) or ""
            digits = re.sub(r"[^\d]", "", label)
            return int(digits) if digits else 0
        except (PWTimeout, PWError):
            return 0

    @staticmethod
    def _extract_reviews(page: Page, limit: int = 5) -> list[Review]:
        reviews: list[Review] = []
        try:
            tab = page.locator('button[role="tab"]').filter(
                has_text=re.compile("Yorum|Review", re.I)
            ).first
            tab.click(timeout=4_000)
            page.wait_for_selector("div.jftiEf", timeout=8_000)
        except (PWTimeout, PWError):
            return reviews

        for el in page.locator("div.jftiEf").all()[:limit]:
            try:
                stars = 0
                label = (
                    el.locator('span[role="img"][aria-label]').first.get_attribute("aria-label", timeout=2_000)
                    or ""
                )
                m = re.search(r"(\d)", label)
                if m:
                    stars = int(m.group(1))
                text = ""
                body = el.locator("span.wiI7pd").first
                if body.count():
                    text = body.inner_text(timeout=2_000).strip()
                if stars or text:
                    reviews.append(Review(rating=stars, text=text))
            except (PWTimeout, PWError):
                continue
        return reviews
