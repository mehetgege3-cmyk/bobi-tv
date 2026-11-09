"""v7 scenario package façade; eski `modules.scenario` API geriye dönük uyumludur.

Yeni kod `modules.senaryo_v7` altındadır. Bu modül yalnızca v6 çağrı imzalarını
korur; özellikle `senaryo_paketi_olustur(video_no)` çağrısı aynen çalışır.
"""

from __future__ import annotations

import hashlib
import random
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

from modules.senaryo_v7.arsiv import ArsivDeposu, _kategori_al
from modules.senaryo_v7.ayarlar import Ayarlar
from modules.senaryo_v7.dogrulama.migration import migrate
from modules.senaryo_v7.exceptions import ArsivHatasi, CiktiHatasi, KuyrukHatasi, SablonHatasi, SenaryoHatasi
from modules.senaryo_v7.models import (
    AltyaziStili,
    Diyalog,
    DiyalogRolu,
    Duygu,
    KameraHareketi,
    Karakter,
    Sablon,
    Senaryo,
    SenaryoPaketi,
)
from modules.senaryo_v7.sablonlar import load_konu_aciklamalari, load_sablonlar
from modules.senaryo_v7.service import SenaryoUretici
from modules.senaryo_v7.service import gun_senaryolari_uret as _gun_senaryolari_uret

_DEFAULTS = Ayarlar.ortamdan()
ARSIV_YOLU = _DEFAULTS.arsiv_yolu
SENARYO_YOLU = _DEFAULTS.senaryo_yolu
ARENA_KUYRUK_YOLU = _DEFAULTS.arena_kuyruk_yolu
SENARYO_SABLONLARI: list[dict[str, Any]] = [
    item.to_dict() for item in load_sablonlar(_DEFAULTS.dizi_sablon_yolu)
]
KONU_ACIKLAMALARI = load_konu_aciklamalari(_DEFAULTS.konu_aciklama_yolu)


def _ayarlar() -> Ayarlar:
    """Eski global path değişkenlerini ve ortam override'larını birleştirir."""
    configured = Ayarlar.ortamdan()
    return replace(
        configured,
        arsiv_yolu=Path(ARSIV_YOLU),
        senaryo_yolu=Path(SENARYO_YOLU),
        arena_kuyruk_yolu=Path(ARENA_KUYRUK_YOLU),
    )


def senaryo_dogrula_ve_zenginlestir(ham: dict[str, Any], video_no: int = 1) -> dict[str, Any]:
    """v6-compatible adapter: raw dict alır, v7-enriched dict döndürür."""
    service = SenaryoUretici(_ayarlar())
    return service.senaryo_dogrula_ve_zenginlestir(ham, video_no).to_dict()


def arsiv_yukle() -> list[dict[str, Any]]:
    """Legacy arşiv yükleyici; yoksa boş liste, bozuksa ArsivHatasi verir."""
    return ArsivDeposu(_ayarlar()).yukle()


def _arsiv_kategorisi(kayit: dict[str, Any]) -> str:
    """Legacy private helper için eski dosya adlarından kategori çıkarır."""
    return _kategori_al(kayit)


def siradaki_kategori(
    kategoriler: Sequence[str] | None = None,
    son_n: int = 6,
    rng: random.Random | None = None,
) -> str:
    """Legacy kategori API'sini v7 arşiv rotasyonuna yönlendirir."""
    settings = _ayarlar()
    service_rng = rng or random.Random()
    repository = ArsivDeposu(settings)
    if son_n != settings.yakin_kategori_sayisi:
        settings = replace(settings, yakin_kategori_sayisi=son_n)
        repository = ArsivDeposu(settings)
    pool = list(kategoriler or [item["kategori"] for item in SENARYO_SABLONLARI])
    return repository.siradaki_kategori(pool, service_rng)


def senaryo_tekrar_mi(senaryo_ozeti: str, arsiv: list[dict[str, Any]]) -> bool:
    """Legacy duplicate-check helper with v7 hashing semantics."""
    digest = hashlib.md5(senaryo_ozeti[:120].encode("utf-8"), usedforsecurity=False).hexdigest()
    return any(item.get("hash") == digest for item in arsiv)


def kuyruktan_arena_senaryosu_al(video_no: int) -> dict[str, Any] | None:
    """Legacy Arena queue API; returns a package mapping or None."""
    return SenaryoUretici(_ayarlar()).kuyruktan_arena_senaryosu_al(video_no)


def _pakete_sar(senaryo: dict[str, Any], video_no: int, kaynak: str = "sablon") -> dict[str, Any]:
    """Legacy pack helper retained for internal callers and downstream scripts."""
    service = SenaryoUretici(_ayarlar())
    validated = service.senaryo_dogrula_ve_zenginlestir(senaryo, video_no)
    return service._pakete_sar(validated, video_no, kaynak).to_dict()


def senaryo_paketi_olustur(
    video_no: int,
    *,
    seed: int | str | None = None,
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Backward-compatible package generation; the historical one-arg call is unchanged.

    `senaryo_paketi_olustur(video_no)` remains valid. Optional seed/rng enables
    deterministic tests or a caller-managed random stream.
    """
    service = SenaryoUretici(_ayarlar(), seed=seed, rng=rng)
    return service.senaryo_paketi_olustur(video_no)


def gun_senaryolari_uret(hedef: int = 4, *, seed: int | str | None = None) -> list[dict[str, Any]]:
    """Legacy batch API, now with one injected RNG and category rotation."""
    return _gun_senaryolari_uret(hedef, seed=seed, ayarlar=_ayarlar())


__all__ = [
    "ARSIV_YOLU",
    "ARENA_KUYRUK_YOLU",
    "SENARYO_YOLU",
    "SENARYO_SABLONLARI",
    "KONU_ACIKLAMALARI",
    "SenaryoHatasi",
    "KuyrukHatasi",
    "ArsivHatasi",
    "SablonHatasi",
    "CiktiHatasi",
    "Ayarlar",
    "Duygu",
    "AltyaziStili",
    "KameraHareketi",
    "DiyalogRolu",
    "Karakter",
    "Diyalog",
    "Senaryo",
    "SenaryoPaketi",
    "Sablon",
    "SenaryoUretici",
    "migrate",
    "arsiv_yukle",
    "gun_senaryolari_uret",
    "kuyruktan_arena_senaryosu_al",
    "senaryo_dogrula_ve_zenginlestir",
    "senaryo_paketi_olustur",
    "senaryo_tekrar_mi",
    "siradaki_kategori",
]


if __name__ == "__main__":
    from modules.senaryo_v7.cli import main

    raise SystemExit(main())
