"""Arena ön üretim senaryolarının sıralı okunması ve tüketilmesi."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..ayarlar import Ayarlar
from ..exceptions import KuyrukHatasi


class KuyrukDeposu:
    """`arena_*.json` dosyaları için tek sorumluluklu kuyruk deposu."""

    def __init__(self, ayarlar: Ayarlar) -> None:
        """Kuyruk dizinini ayarlardan alır."""
        self._ayarlar = ayarlar

    def bekleyenler(self) -> list[Path]:
        """Sıralı Arena JSON dosyalarını döndürür; dizin okunamıyorsa hata verir."""
        directory = self._ayarlar.arena_kuyruk_yolu
        if not directory.exists():
            return []
        try:
            return sorted(directory.glob("arena_*.json"))
        except OSError as exc:
            raise KuyrukHatasi(f"Arena kuyruğu listelenemedi ({directory}): {exc}") from exc

    def oku(self, path: Path) -> dict[str, Any]:
        """Bir kuyruk kaydını JSON nesnesi olarak okur ve anlamlı hata üretir."""
        try:
            raw: object = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise KuyrukHatasi(f"Kuyruk kaydı okunamadı ({path}): {exc}") from exc
        if not isinstance(raw, dict):
            raise KuyrukHatasi(f"Kuyruk kaydı JSON nesnesi olmalı ({path}).")
        return raw

    def tuket(self, path: Path) -> None:
        """İşlenen/bozuk kuyruk kaydını siler; silme hatasını KuyrukHatasi'ye sarar."""
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            raise KuyrukHatasi(f"Kuyruk kaydı tüketilemedi ({path}): {exc}") from exc
