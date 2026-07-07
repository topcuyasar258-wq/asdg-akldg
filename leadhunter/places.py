"""Google Places API (New) istemcisi.

İşletmeleri metin aramasıyla bulur ve her biri için detay (telefon, web
sitesi, puan, yorumlar) çeker. Resmi API kullanıldığı için IP engeli /
bot koruması gibi sorunlar yaşanmaz.

Gerekli ortam değişkeni: GOOGLE_PLACES_API_KEY
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field

import requests

log = logging.getLogger(__name__)

SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

SEARCH_FIELDS = ",".join(
    f"places.{f}"
    for f in (
        "id",
        "displayName",
        "formattedAddress",
        "nationalPhoneNumber",
        "internationalPhoneNumber",
        "websiteUri",
        "rating",
        "userRatingCount",
        "googleMapsUri",
        "businessStatus",
        "reviews",
    )
)


@dataclass
class Review:
    rating: int
    text: str
    relative_time: str = ""


@dataclass
class Business:
    place_id: str
    name: str
    address: str = ""
    phone: str = ""
    website: str = ""
    rating: float | None = None
    review_count: int = 0
    maps_url: str = ""
    reviews: list[Review] = field(default_factory=list)


class PlacesClient:
    def __init__(self, api_key: str | None = None, language: str = "tr", region: str = "tr"):
        self.api_key = api_key or os.environ.get("GOOGLE_PLACES_API_KEY", "")
        if not self.api_key:
            raise RuntimeError(
                "GOOGLE_PLACES_API_KEY tanımlı değil. GitHub Secrets'a ekleyin."
            )
        self.language = language
        self.region = region
        self.session = requests.Session()

    def search(self, query: str, max_results: int = 20) -> list[Business]:
        """Metin aramasıyla işletmeleri bulur (sayfalama dahil)."""
        businesses: list[Business] = []
        page_token: str | None = None

        while len(businesses) < max_results:
            body: dict = {
                "textQuery": query,
                "languageCode": self.language,
                "regionCode": self.region.upper(),
                "pageSize": min(20, max_results - len(businesses)),
            }
            if page_token:
                body["pageToken"] = page_token

            resp = self.session.post(
                SEARCH_URL,
                json=body,
                headers={
                    "X-Goog-Api-Key": self.api_key,
                    "X-Goog-FieldMask": SEARCH_FIELDS + ",nextPageToken",
                },
                timeout=30,
            )
            if resp.status_code != 200:
                log.error("Places API hatası (%s): %s", resp.status_code, resp.text[:500])
                break

            data = resp.json()
            for place in data.get("places", []):
                if place.get("businessStatus") not in (None, "OPERATIONAL"):
                    continue
                businesses.append(self._parse_place(place))

            page_token = data.get("nextPageToken")
            if not page_token:
                break
            time.sleep(1)  # sayfa token'ının aktifleşmesi için kısa bekleme

        log.info("'%s' sorgusu: %d işletme bulundu", query, len(businesses))
        return businesses[:max_results]

    @staticmethod
    def _parse_place(place: dict) -> Business:
        reviews = [
            Review(
                rating=r.get("rating", 0),
                text=(r.get("text") or {}).get("text", ""),
                relative_time=r.get("relativePublishTimeDescription", ""),
            )
            for r in place.get("reviews", [])
        ]
        return Business(
            place_id=place.get("id", ""),
            name=(place.get("displayName") or {}).get("text", ""),
            address=place.get("formattedAddress", ""),
            phone=place.get("nationalPhoneNumber")
            or place.get("internationalPhoneNumber", ""),
            website=place.get("websiteUri", ""),
            rating=place.get("rating"),
            review_count=place.get("userRatingCount", 0),
            maps_url=place.get("googleMapsUri", ""),
            reviews=reviews,
        )
