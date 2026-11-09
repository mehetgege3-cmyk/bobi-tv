"""Şablon verisini JSON'dan güvenle okuma ve temel şema doğrulama."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from ..exceptions import SablonHatasi
from ..models import Sablon


def load_sablonlar(path: str | Path) -> tuple[Sablon, ...]:
    """JSON dosyasını yükler; bozuk/eksik kayıtları SablonHatasi ile bildirir."""
    target = Path(path)
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SablonHatasi(f"Şablon dosyası okunamadı ({target}): {exc}") from exc
    if not isinstance(raw, list):
        raise SablonHatasi(f"Şablon dosyasının kökü liste olmalı: {target}")
    templates: list[Sablon] = []
    for index, item in enumerate(raw):
        if not isinstance(item, Mapping):
            raise SablonHatasi(f"{target} içindeki {index}. şablon nesne değil.")
        template = Sablon.from_dict(cast(Mapping[str, object], item))
        if not template.kategori or not template.baslik or len(template.diyaloglar) < 3:
            raise SablonHatasi(f"{target} içindeki {index}. şablonda kategori, başlık veya diyalog eksik.")
        templates.append(template)
    if not templates:
        raise SablonHatasi(f"Şablon listesi boş: {target}")
    return tuple(templates)


def load_konu_aciklamalari(path: str | Path) -> dict[str, str]:
    """Konu metadata JSON'unu yükler; yanlış yapılandırmada anlamlı hata verir."""
    target = Path(path)
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SablonHatasi(f"Konu açıklamaları okunamadı ({target}): {exc}") from exc
    if not isinstance(raw, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in raw.items()
    ):
        raise SablonHatasi(f"Konu açıklamaları string:string JSON nesnesi olmalı: {target}")
    return dict(raw)
