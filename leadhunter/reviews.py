"""Google Maps yorumlarının analizi.

Yorum sayısı, ortalama puan ve yorum metinlerindeki şikayet sinyallerine
bakarak işletmenin itibar yönetimi ihtiyacını ölçer.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .places import Review

# Türkçe yorumlarda geçen olumsuzluk sinyalleri
NEGATIVE_KEYWORDS = (
    "kötü",
    "berbat",
    "rezalet",
    "hayal kırıklığı",
    "tavsiye etmem",
    "ilgisiz",
    "kaba",
    "pahalı",
    "hijyen",
    "pis",
    "bekletti",
    "geç geldi",
    "şikayet",
    "dolandır",
    "asla",
    "bir daha gelmem",
)


@dataclass
class ReviewReport:
    review_count: int = 0
    rating: float | None = None
    negative_review_count: int = 0
    negative_snippets: list[str] = field(default_factory=list)

    @property
    def needs_reputation_help(self) -> bool:
        low_rating = self.rating is not None and self.rating < 4.0
        return low_rating or self.negative_review_count >= 2


def analyze_reviews(rating: float | None, review_count: int, reviews: list[Review]) -> ReviewReport:
    report = ReviewReport(review_count=review_count, rating=rating)

    for review in reviews:
        text_lower = review.text.lower()
        is_negative = review.rating <= 2 or any(k in text_lower for k in NEGATIVE_KEYWORDS)
        if is_negative:
            report.negative_review_count += 1
            if review.text and len(report.negative_snippets) < 2:
                snippet = review.text.replace("\n", " ")[:120]
                report.negative_snippets.append(snippet)

    return report
