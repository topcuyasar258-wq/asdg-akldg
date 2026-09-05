"""Tıkla-gönder ulaşım sayfası üreticisi.

Her tarama için data/outreach/<tarih>-<profil>.md dosyası yazar. Telefonundan
GitHub üzerinde açtığında her işletmenin altında "WhatsApp'tan ulaş" bağlantısı
olur; tıklayınca WhatsApp o işletmeye özel mesaj hazır şekilde açılır — "gönder"e
sen basarsın (yasal ve WhatsApp-güvenli birebir temas).
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from .outreach import craft_message, craft_pitch, whatsapp_link
from .scorer import Lead

OUTREACH_DIR = Path(__file__).resolve().parent.parent / "data" / "outreach"


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-")


def write_sheet(profile_name: str, leads: list[Lead], out_dir: Path = OUTREACH_DIR) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    path = out_dir / f"{today}-{_slug(profile_name)}.md"

    lines = [
        f"# 📲 Ulaşım Sayfası — {profile_name}",
        f"_{date.today().strftime('%d.%m.%Y')} · {len(leads)} potansiyel müşteri_",
        "",
        "> Her işletmenin altındaki **WhatsApp'tan ulaş** bağlantısına telefonundan "
        "tıkla; mesaj hazır açılır, sadece **Gönder**'e bas. Mesajı göndermeden "
        "kişiselleştirmen (isim, tarih) dönüşümü artırır.",
        "",
        "---",
        "",
    ]

    for i, lead in enumerate(leads, 1):
        b = lead.business
        tag = " 🏆 ÖNCELİKLİ" if lead.is_prime else ""
        lines.append(f"## {i}) {b.name} — Skor {lead.score}/100{tag}")
        lines.append("")
        lines.append(f"- 📞 **{b.phone or 'Telefon yok'}**")
        if b.address:
            lines.append(f"- 📍 {b.address}")
        if b.rating:
            lines.append(f"- ⭐ {b.rating} ({b.review_count} yorum)")
        lines.append(f"- 💼 Önerilecek: {', '.join(lead.services[:4])}")

        pitch = craft_pitch(lead)
        if pitch:
            lines.append("- 🎯 **Arama cephanesi:**")
            for point in pitch:
                lines.append(f"    - {point}")

        if b.phone:
            lines.append("")
            lines.append(f"  👉 **[WhatsApp'tan ulaş]({whatsapp_link(lead)})**")
            lines.append("")
            lines.append("  <details><summary>Hazır mesajı gör</summary>")
            lines.append("")
            lines.append("  ```")
            for msg_line in craft_message(lead).splitlines():
                lines.append(f"  {msg_line}")
            lines.append("  ```")
            lines.append("  </details>")
        lines.append("")
        lines.append("---")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def github_url_for(path: Path) -> str:
    """GitHub Actions ortamında dosyanın tıklanabilir blob URL'sini üretir."""
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    ref = os.environ.get("GITHUB_REF_NAME", "")
    if not repo or not ref:
        return ""
    try:
        rel = path.resolve().relative_to(Path(__file__).resolve().parent.parent)
    except ValueError:
        return ""
    return f"https://github.com/{repo}/blob/{ref}/{rel.as_posix()}"
