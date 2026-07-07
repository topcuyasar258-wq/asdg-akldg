"""veridiareklam.com.tr — Günlük potansiyel müşteri tarayıcısı.

Kullanım:
    python main.py                      # bugünün profiliyle çalışır
    python main.py --profile saglik     # belirli bir profili çalıştırır
    python main.py --query "kafe Moda"  # tek seferlik özel arama
    python main.py --dry-run            # WhatsApp göndermez, konsola yazar
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date
from pathlib import Path

import yaml

from leadhunter.places import PlacesClient
from leadhunter.report import format_report
from leadhunter.reviews import analyze_reviews
from leadhunter.scorer import Lead, score_lead
from leadhunter.state import SeenStore
from leadhunter.website_analyzer import analyze_website
from leadhunter.whatsapp import send_report

CONFIG_FILE = Path(__file__).resolve().parent / "config" / "profiles.yaml"

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("leadhunter")


def load_config() -> dict:
    with open(CONFIG_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f)


def pick_profile(config: dict, name: str | None) -> dict | None:
    profiles = config.get("profiles", [])
    if name:
        for profile in profiles:
            if profile["name"] == name:
                return profile
        log.error("Profil bulunamadı: %s (mevcut: %s)", name, ", ".join(p["name"] for p in profiles))
        return None

    weekday = date.today().weekday()
    for profile in profiles:
        if weekday in profile.get("days", []):
            return profile
    return None


def make_client(defaults: dict):
    """Veri kaynağını seçer: API anahtarı varsa resmi Places API,
    yoksa (varsayılan) tamamen ücretsiz tarayıcı tabanlı Maps scraper."""
    language = defaults.get("language", "tr")
    region = defaults.get("region", "tr")
    if os.environ.get("GOOGLE_PLACES_API_KEY"):
        log.info("Veri kaynağı: Google Places API")
        return PlacesClient(language=language, region=region)
    from leadhunter.maps_scraper import MapsScraper

    log.info("Veri kaynağı: ücretsiz Google Maps tarayıcısı (API anahtarı yok)")
    return MapsScraper(language=language, region=region)


def run_scan(queries: list[str], profile_name: str, defaults: dict, dry_run: bool) -> None:
    client = make_client(defaults)
    store = SeenStore()
    leads: list[Lead] = []
    scanned = 0

    for query in queries:
        for business in client.search(query, defaults.get("max_results_per_query", 20)):
            if not business.place_id or store.is_seen(business.place_id):
                continue
            scanned += 1
            store.mark(business.place_id, business.name)

            if defaults.get("require_phone", True) and not business.phone:
                continue

            web = analyze_website(business.website)
            rev = analyze_reviews(business.rating, business.review_count, business.reviews)
            lead = score_lead(business, web, rev)
            log.info("%-40s skor=%d", business.name[:40], lead.score)

            if lead.score >= defaults.get("min_lead_score", 40):
                leads.append(lead)

    leads.sort(key=lambda l: l.score, reverse=True)
    leads = leads[: defaults.get("max_leads_per_report", 10)]

    text = format_report(profile_name, leads, scanned)
    print("\n" + text + "\n")

    if dry_run:
        log.info("Dry-run: WhatsApp gönderimi atlandı, durum dosyası kaydedilmedi.")
        return

    send_report(text)
    store.save()


def main() -> int:
    parser = argparse.ArgumentParser(description="Google Maps lead tarayıcısı")
    parser.add_argument("--profile", help="Çalıştırılacak profil adı")
    parser.add_argument("--query", help="Tek seferlik özel arama sorgusu")
    parser.add_argument("--dry-run", action="store_true", help="WhatsApp göndermeden test et")
    args = parser.parse_args()

    config = load_config()
    defaults = config.get("defaults", {})

    if args.query:
        run_scan([args.query], f"özel arama: {args.query}", defaults, args.dry_run)
        return 0

    profile = pick_profile(config, args.profile)
    if not profile:
        log.info("Bugün için tanımlı profil yok — çıkılıyor.")
        return 0

    log.info("Profil çalıştırılıyor: %s (%d sorgu)", profile["name"], len(profile["queries"]))
    run_scan(profile["queries"], profile["name"], defaults, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
