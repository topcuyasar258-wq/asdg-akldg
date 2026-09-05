"""WhatsApp rapor metnini oluşturur."""

from __future__ import annotations

from datetime import date

from .scorer import Lead


def format_report(
    profile_name: str, leads: list[Lead], scanned_count: int, sheet_url: str = ""
) -> str:
    today = date.today().strftime("%d.%m.%Y")
    lines = [
        f"🎯 *VERİDİA REKLAM — Günlük Lead Raporu*",
        f"📅 {today} | Profil: {profile_name}",
        f"🔍 Taranan işletme: {scanned_count} | Potansiyel müşteri: {len(leads)}",
    ]

    if not leads:
        lines.append("\nBugün kriterlere uyan yeni potansiyel müşteri bulunamadı.")
        return "\n".join(lines)

    for i, lead in enumerate(leads, 1):
        b = lead.business
        rating = f"⭐ {b.rating} ({b.review_count} yorum)" if b.rating else "⭐ Puan yok"
        lines.append("")
        lines.append(f"*{i}) {b.name}* — Skor: {lead.score}/100")
        lines.append(f"📞 {b.phone or 'Telefon yok'}")
        lines.append(f"📍 {b.address}")
        lines.append(rating)
        if b.website:
            lines.append(f"🌐 {b.website}")
        if lead.website.socials:
            socials = ", ".join(f"{k}: @{v}" for k, v in lead.website.socials.items())
            lines.append(f"📱 {socials}")
        lines.append("❗ " + " | ".join(lead.reasons[:4]))
        lines.append("💼 Önerilecek hizmet: " + ", ".join(lead.services[:3]))
        if lead.reviews.negative_snippets:
            lines.append(f'💬 Örnek şikayet: "{lead.reviews.negative_snippets[0]}"')
        if b.maps_url:
            lines.append(f"🗺️ {b.maps_url}")

    if sheet_url:
        lines.append("")
        lines.append(f"✍️ *Tıkla-gönder ulaşım sayfası:*\n{sheet_url}")

    return "\n".join(lines)
