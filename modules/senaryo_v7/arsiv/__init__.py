"""Yayın arşivi okuma, tekrar kontrolü ve kategori rotasyonu."""

from __future__ import annotations

import hashlib
import json
import random
from collections.abc import Sequence
from typing import Any

from ..ayarlar import Ayarlar
from ..exceptions import ArsivHatasi


class ArsivDeposu:
    """videos.json arşiviyle çalışmak için tek sorumluluklu depo."""

    def __init__(self, ayarlar: Ayarlar) -> None:
        """Depoyu yapılandırılmış arşiv yolu ile başlatır."""
        self._ayarlar = ayarlar

    def yukle(self) -> list[dict[str, Any]]:
        """Arşivi oku; dosya yoksa boş geçmiş, bozuk JSON'da ArsivHatasi döndür."""
        path = self._ayarlar.arsiv_yolu
        if not path.exists():
            return []
        try:
            raw: object = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ArsivHatasi(f"Video arşivi okunamadı ({path}): {exc}") from exc
        if not isinstance(raw, list) or not all(isinstance(row, dict) for row in raw):
            raise ArsivHatasi(f"Video arşivi JSON listesi olmalı ve kayıtları nesne olmalı: {path}")
        return raw

    def tekrar_mi(self, summary: str, history: Sequence[dict[str, Any]] | None = None) -> bool:
        """İlk 120 karakterden oluşturulan MD5 hash'i arşiv kayıtlarıyla karşılaştırır."""
        archive = self.yukle() if history is None else list(history)
        digest = hashlib.md5(summary[:120].encode("utf-8"), usedforsecurity=False).hexdigest()
        return any(row.get("hash") == digest for row in archive)

    def yakin_kategoriler(self, count: int | None = None) -> set[str]:
        """Son n yayının kategori slug'larını yeni/legacy kayıt biçimlerinden çıkarır."""
        limit = max(1, count or self._ayarlar.yakin_kategori_sayisi)
        history = self.yukle()
        result: set[str] = set()
        for row in reversed(history[-limit:]):
            category = _kategori_al(row)
            if category:
                result.add(category)
        return result

    def siradaki_kategori(self, categories: Sequence[str], rng: random.Random) -> str:
        """Son yayınlarda olmayan bir kategoriyi enjekte edilen RNG ile seçer."""
        pool = list(dict.fromkeys(categories))
        if not pool:
            return "absurt_komedi"
        recent = self.yakin_kategoriler()
        candidates = [item for item in pool if item not in recent]
        if not candidates:
            history = self.yukle()
            last_category = _kategori_al(history[-1]) if history else ""
            candidates = [item for item in pool if item != last_category] or pool
        return rng.choice(candidates)


def _kategori_al(row: dict[str, Any]) -> str:
    """Archive record'daki kategori veya eski dosya adından kategori çıkarır."""
    category = str(row.get("kategori") or "").strip()
    if category:
        return category
    parts = str(row.get("dosya_adi") or "").split("_", 2)
    if len(parts) != 3:
        return ""
    slug = parts[2]
    return slug[:-6] if slug.endswith("_arena") else slug
