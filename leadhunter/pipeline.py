"""Lead pipeline — her taramada bulunan lead'leri kalıcı CSV'ye ekler.

WhatsApp raporu uçucudur; okununca kaybolur. Bu modül aynı lead'leri
data/leads.csv'ye de yazar; böylece zamanla "kimi aradık, kim döndü, hangi
profil dönüşüyor" takip edilebilir ve sistem kendi kendini optimize eder.

'durum' kolonu elle doldurulur (yeni / arandı / toplantı / kazanıldı /
kaybedildi). Sistem bu kolona asla dokunmaz — sadece yeni satır ekler.
"""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from .outreach import whatsapp_link
from .scorer import Lead

LEADS_CSV = Path(__file__).resolve().parent.parent / "data" / "leads.csv"

FIELDNAMES = [
    "tarih",
    "profil",
    "isletme",
    "telefon",
    "skor",
    "tip",           # prime / normal / zayif
    "sahiplenilmemis",
    "hizmetler",
    "gerekce",
    "harita",
    "whatsapp_link",
    "durum",         # elle doldurulur
]


def append_leads(profile_name: str, leads: list[Lead], path: Path = LEADS_CSV) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    is_new_file = not path.exists()
    today = date.today().isoformat()

    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if is_new_file:
            writer.writeheader()
        for lead in leads:
            b = lead.business
            tip = "prime" if lead.is_prime else ("zayif" if lead.is_dead else "normal")
            writer.writerow(
                {
                    "tarih": today,
                    "profil": profile_name,
                    "isletme": b.name,
                    "telefon": b.phone,
                    "skor": lead.score,
                    "tip": tip,
                    "sahiplenilmemis": "evet" if b.unclaimed else "",
                    "hizmetler": "; ".join(lead.services[:4]),
                    "gerekce": " | ".join(lead.reasons[:4]),
                    "harita": b.maps_url,
                    "whatsapp_link": whatsapp_link(lead) if b.phone else "",
                    "durum": "yeni",
                }
            )
