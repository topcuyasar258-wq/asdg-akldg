"""WhatsApp rapor gönderimi.

İki yöntem desteklenir; ortam değişkenlerine göre otomatik seçilir:

1. CallMeBot (ücretsiz, kendi numaranıza mesaj):
   - WHATSAPP_TO        : Raporun gideceği numara (örn. +90532xxxxxxx)
   - CALLMEBOT_API_KEY  : callmebot.com'dan alınan anahtar
   Kurulum: https://www.callmebot.com/blog/free-api-whatsapp-messages/

2. Twilio WhatsApp API (kurumsal):
   - TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN
   - TWILIO_WHATSAPP_FROM (örn. whatsapp:+14155238886)
   - WHATSAPP_TO
"""

from __future__ import annotations

import logging
import os
import time

import requests

log = logging.getLogger(__name__)

# CallMeBot'un ücretsiz servisi uzun mesajları ~1000 karakter civarında
# kırpıyor; güvenli tarafta kalmak için raporu küçük parçalara böleriz.
MAX_MESSAGE_CHARS = 800
DELAY_BETWEEN_CHUNKS = 5  # saniye — sıralamanın karışmaması ve rate limit için


def send_report(text: str) -> bool:
    to = os.environ.get("WHATSAPP_TO", "").strip()
    if not to:
        log.warning("WHATSAPP_TO tanımlı değil — rapor gönderilemedi, konsola yazılıyor:\n%s", text)
        return False

    chunks = _split_message(text)
    total = len(chunks)
    if total > 1:
        chunks = [f"[{i}/{total}]\n{chunk}" for i, chunk in enumerate(chunks, 1)]

    sender = None
    if os.environ.get("CALLMEBOT_API_KEY"):
        sender = _send_callmebot
    elif os.environ.get("TWILIO_ACCOUNT_SID"):
        sender = _send_twilio
    else:
        log.warning("Ne CALLMEBOT_API_KEY ne TWILIO_ACCOUNT_SID tanımlı — rapor konsola yazılıyor:\n%s", text)
        return False

    ok = True
    for i, chunk in enumerate(chunks):
        if i > 0:
            time.sleep(DELAY_BETWEEN_CHUNKS)
        ok = sender(to, chunk) and ok
    return ok


def _split_message(text: str) -> list[str]:
    if len(text) <= MAX_MESSAGE_CHARS:
        return [text]
    chunks, current = [], ""
    for block in text.split("\n\n"):
        candidate = f"{current}\n\n{block}" if current else block
        if len(candidate) > MAX_MESSAGE_CHARS and current:
            chunks.append(current)
            current = block
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def _send_callmebot(to: str, text: str) -> bool:
    resp = requests.get(
        "https://api.callmebot.com/whatsapp.php",
        params={
            "phone": to,
            "text": text,
            "apikey": os.environ["CALLMEBOT_API_KEY"],
        },
        timeout=60,
    )
    ok = resp.status_code == 200 and "ERROR" not in resp.text.upper()
    if ok:
        log.info("WhatsApp raporu CallMeBot ile gönderildi (%d karakter)", len(text))
    else:
        log.error("CallMeBot hatası (%s): %s", resp.status_code, resp.text[:300])
    return ok


def _send_twilio(to: str, text: str) -> bool:
    sid = os.environ["TWILIO_ACCOUNT_SID"]
    token = os.environ.get("TWILIO_AUTH_TOKEN", "")
    from_number = os.environ.get("TWILIO_WHATSAPP_FROM", "")
    resp = requests.post(
        f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
        auth=(sid, token),
        data={"From": from_number, "To": f"whatsapp:{to}", "Body": text},
        timeout=60,
    )
    ok = resp.status_code in (200, 201)
    if ok:
        log.info("WhatsApp raporu Twilio ile gönderildi (%d karakter)", len(text))
    else:
        log.error("Twilio hatası (%s): %s", resp.status_code, resp.text[:300])
    return ok
