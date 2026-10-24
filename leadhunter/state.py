"""Daha önce raporlanan işletmelerin kaydı.

Günlük çalışmada aynı işletmenin tekrar tekrar WhatsApp'a düşmemesi için
place_id bazlı basit bir JSON durum dosyası tutulur. GitHub Actions
çalışması sonunda bu dosya repoya geri commitlenir.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

STATE_FILE = Path(__file__).resolve().parent.parent / "data" / "seen.json"


class SeenStore:
    def __init__(self, path: Path = STATE_FILE):
        self.path = path
        self._seen: dict[str, str] = {}
        if path.exists():
            try:
                self._seen = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                self._seen = {}

    def is_seen(self, place_id: str) -> bool:
        return place_id in self._seen

    def mark(self, place_id: str, business_name: str) -> None:
        self._seen[place_id] = f"{date.today().isoformat()} | {business_name}"

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._seen, ensure_ascii=False, indent=1, sort_keys=True),
            encoding="utf-8",
        )
