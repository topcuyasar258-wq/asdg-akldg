"""Lead puanlama motoru.

Bir reklam ajansının (veridiareklam.com.tr) satabileceği hizmetlere göre
0-100 arası puan üretir. Puan yükseldikçe işletmenin dijital varlığı
zayıf, yani ajans için potansiyel o kadar yüksek demektir.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .places import Business
from .reviews import ReviewReport
from .website_analyzer import WebsiteReport


@dataclass
class Lead:
    business: Business
    website: WebsiteReport
    reviews: ReviewReport
    score: int = 0
    reasons: list[str] = field(default_factory=list)
    services: list[str] = field(default_factory=list)  # önerilecek hizmetler


def score_lead(business: Business, web: WebsiteReport, rev: ReviewReport) -> Lead:
    lead = Lead(business=business, website=web, reviews=rev)
    score = 0

    # --- Web sitesi durumu ---
    if not web.has_website and not web.is_free_platform:
        score += 30
        lead.reasons.append("Web sitesi yok")
        lead.services.append("Web tasarım")
    elif web.is_free_platform:
        score += 25
        lead.reasons.append("Site yerine ücretsiz platform kullanıyor (Instagram/Linktree vb.)")
        lead.services.append("Kurumsal web sitesi")
    else:
        if not web.reachable:
            score += 25
            lead.reasons.append("Web sitesi açılmıyor")
            lead.services.append("Web sitesi yenileme")
        else:
            if not web.has_ssl:
                score += 10
                lead.reasons.append("SSL sertifikası yok (güvensiz site)")
                lead.services.append("SSL / teknik bakım")
            if not web.mobile_friendly:
                score += 10
                lead.reasons.append("Mobil uyumlu değil")
                lead.services.append("Responsive tasarım")
            if web.load_time_seconds and web.load_time_seconds > 5:
                score += 5
                lead.reasons.append(f"Site yavaş ({web.load_time_seconds}s)")
                lead.services.append("Site hızlandırma")

    # --- Sosyal medya varlığı ---
    if "instagram" not in web.socials:
        score += 15
        lead.reasons.append("Instagram hesabı bulunamadı")
        lead.services.append("Sosyal medya yönetimi")
    if "facebook" not in web.socials:
        score += 5
        lead.reasons.append("Facebook sayfası bulunamadı")

    # --- Google Maps itibarı ---
    if rev.review_count < 20:
        score += 10
        lead.reasons.append(f"Az yorum ({rev.review_count} adet) — görünürlük düşük")
        lead.services.append("Google haritalar optimizasyonu")
    if rev.rating is not None and rev.rating < 4.0:
        score += 10
        lead.reasons.append(f"Düşük puan ({rev.rating}) — itibar riski")
        lead.services.append("İtibar yönetimi")
    elif rev.negative_review_count >= 2:
        score += 5
        lead.reasons.append("Son yorumlarda şikayetler var")
        lead.services.append("İtibar yönetimi")

    lead.score = min(score, 100)
    # Aynı hizmet birden fazla eklendiyse tekilleştir (sıra korunur)
    lead.services = list(dict.fromkeys(lead.services))
    return lead
