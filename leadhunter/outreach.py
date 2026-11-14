"""Lead'lere ulaşım asistanı.

Her lead için işletmeye özel, tespit edilen eksikliklere dayanan bir tanıtım
mesajı üretir ve tek tıkla açılan bir WhatsApp linki (wa.me) hazırlar.

ÖNEMLİ — bu modül mesajı OTOMATİK GÖNDERMEZ. Sadece hazır metni ve linki
üretir; "gönder"e ekip üyesi kendi telefonundan basar. Bunun iki sebebi var:
1) Yasal: Türkiye'de 6563 sayılı kanun (İYS) kapsamında izinsiz ticari
   elektronik ileti göndermek yasaktır; ilk temas birebir/kişisel olmalıdır.
2) Pratik: WhatsApp toplu/otomatik soğuk mesaj atan numaraları kalıcı banlar.
"""

from __future__ import annotations

import urllib.parse

from .scorer import Lead

AGENCY_NAME = "Veridia Reklam"


def _clean_phone(phone: str) -> str:
    """wa.me için numarayı yalnız rakama indirir (+90… -> 90…)."""
    digits = "".join(ch for ch in phone if ch.isdigit())
    # 0 ile başlayan yerel format -> Türkiye ülke koduyla değiştir
    if digits.startswith("0"):
        digits = "90" + digits[1:]
    elif len(digits) == 10:  # ülke kodu ve baştaki 0 olmadan
        digits = "90" + digits
    return digits


def craft_message(lead: Lead) -> str:
    """İşletmeye özel, kısa ve satışçı bir açılış mesajı üretir."""
    b = lead.business
    name = b.name

    # Selamlama + neyi fark ettiğimiz (kişiselleştirme burada)
    hook = _opening_hook(lead)
    services = lead.services[:2] or ["dijital görünürlük"]
    service_text = " ve ".join(services).lower()

    return (
        f"Merhaba, {name} ekibi 👋\n\n"
        f"Ben {AGENCY_NAME}'dan yazıyorum. {hook} "
        f"Sizin gibi işini iyi yapan bir işletmenin internette de hak ettiği "
        f"yeri almasını sağlayabiliriz.\n\n"
        f"Özellikle {service_text} konusunda kısa bir fikir alışverişi yapmak isteriz. "
        f"Uygun olduğunuz bir zaman 10 dakikalık bir görüşme ayarlayabilir miyiz?\n\n"
        f"İyi çalışmalar dileriz."
    )


def _opening_hook(lead: Lead) -> str:
    """Puanlamada tespit edilen en güçlü sinyale göre giriş cümlesi seçer."""
    web = lead.website
    rev = lead.reviews
    b = lead.business

    if not web.has_website and not web.is_free_platform:
        return (
            f"Google'da işletmenizi incelerken bir web sitenizin olmadığını fark ettik; "
            f"oysa {b.review_count}+ yorumla ciddi bir müşteri kitleniz var."
        )
    if web.is_free_platform:
        return (
            "İşletmenizi yalnızca sosyal medya üzerinden yönettiğinizi gördük; "
            "kurumsal bir web siteniz güven ve görünürlüğü ciddi artırır."
        )
    if web.has_website and not web.reachable:
        return "Web sitenizin şu an açılmadığını fark ettik — potansiyel müşteri kaybı olabilir."
    if "instagram" not in web.socials:
        return "Aktif bir Instagram hesabınıza rastlayamadık; bu kanal sizin sektörünüzde çok iş getiriyor."
    if rev.rating is not None and rev.rating < 4.0:
        return f"Google puanınızın ({rev.rating}) hak ettiğinizden düşük olduğunu düşünüyoruz."
    return "Google'daki dijital görünürlüğünüzü daha da güçlendirebileceğimizi düşünüyoruz."


def whatsapp_link(lead: Lead) -> str:
    """Tıklanınca WhatsApp'ı mesaj hazır şekilde açan wa.me linki üretir."""
    phone = _clean_phone(lead.business.phone)
    text = urllib.parse.quote(craft_message(lead))
    return f"https://wa.me/{phone}?text={text}"


def craft_pitch(lead: Lead) -> list[str]:
    """Telefonda kullanacağın somut satış cephanesi — 2-3 kısa madde.

    Rapordaki 'site yok/Instagram yok' listesinden farklı olarak, arama
    anında ağzından çıkacak cümleleri hazır verir.
    """
    web = lead.website
    rev = lead.reviews
    b = lead.business
    ammo: list[str] = []

    if b.unclaimed:
        ammo.append(
            "Google profiliniz henüz sahiplenilmemiş; şu an bilgilerinizi rakipleriniz "
            "veya rastgele kullanıcılar düzenleyebilir. Biz sahiplenip kilitleyelim."
        )
    if rev.rating is not None and rev.review_count:
        if rev.rating >= 4.3 and (not web.has_website or not web.reachable):
            ammo.append(
                f"Google'da {rev.rating} puan ve {rev.review_count} yorumla sınıfının en "
                f"iyilerindensiniz — ama sizi arayan müşteri tıklayacak bir siteniz olmadığını "
                f"görüyor. Bu itibarı web'e taşımak ciddi ek iş demek."
            )
        elif rev.rating < 4.0:
            ammo.append(
                f"Google'da sizi arayan müşteri {rev.rating} puan"
                + (" ve cevaplanmamış şikayetlerle" if rev.negative_review_count else "")
                + " karşılaşıyor; birkaç haftada bu tabloyu çevirebiliriz."
            )
    if not web.has_website and not web.is_free_platform:
        ammo.append(
            "Aramada çıkıyorsunuz ama tıklanacak bir siteniz yok; müşteri rakibinizin "
            "sitesine gidiyor. Basit, mobil uyumlu bir site bu kaçağı durdurur."
        )
    elif web.has_website and web.reachable and not web.mobile_friendly:
        ammo.append(
            "Siteniz telefonda düzgün görünmüyor; ziyaretlerin büyük kısmı mobilden "
            "geldiği için bu doğrudan müşteri kaybı."
        )
    if "instagram" not in web.socials:
        ammo.append(
            "Aktif bir Instagram'ınıza rastlamadık; sektörünüzde vitrin burası, "
            "haftalık içerikle görünürlüğü hızla artırırız."
        )

    return ammo[:3]
