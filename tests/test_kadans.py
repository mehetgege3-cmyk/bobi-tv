"""Üretim kadansı: 8 saatte bir (günde 3) — tek doğruluk kaynağı sözleşmesi.

Karar 2026-11-11. Kural: docs/BOBI_TV_V6_PRO_MIMARI_VE_KURALLAR.md Bölüm 5.
Bu testler üç yerdeki değerin AYNI kalmasını zorlar (kadans, cron, katalog).
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.kadans import (  # noqa: E402
    GUNLUK_KADANS_SAYISI,
    GUNLUK_YUKLEME_TAVANI,
    KADANS_CRON,
    KADANS_DK,
    VIDEO_INSERT_MALIYETI,
    YOUTUBE_GUNLUK_KOTA_BIRIM,
    gercek_aralik_dk,
    kota_uyarisi,
)

WORKFLOW = Path(".github/workflows/hourly_production.yml")


def _cronlar() -> list[str]:
    d = yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    return [str(k["cron"]) for k in d["on"]["schedule"]]


def test_kadans_8_saat() -> None:
    """KADANS_DK = 480 — kullanıcı kararı 2026-11-11 (15 dk kanalı yaktı).

    Ölçüm: 1 saatte silinen 21 videonun ortalama izlenmesi 0.8'di; videolar
    Shorts akışına hiç girmiyordu. 8 saat = günde 3 video.
    """
    assert KADANS_DK == 480


def test_workflow_cron_kadansla_ayni() -> None:
    """Workflow cron'u KADANS_CRON ile BİREBİR aynı olmalı (tek kaynak)."""
    assert _cronlar() == [KADANS_CRON], f"cron uyuşmuyor: {_cronlar()}"
    assert KADANS_CRON == "0 */8 * * *"


def test_gunluk_kadans_sayisi() -> None:
    """8 saat → günde 3 fırsat (zamanlama; yükleme sayısı DEĞİL)."""
    assert GUNLUK_KADANS_SAYISI == 3


def test_kota_tavani_google_sabiti() -> None:
    """Kota matematiği: 10000 // 1600 == 6 — değiştirilemez."""
    assert YOUTUBE_GUNLUK_KOTA_BIRIM == 10_000
    assert VIDEO_INSERT_MALIYETI == 1_600
    assert GUNLUK_YUKLEME_TAVANI == 6


def test_gercek_aralik_dakika() -> None:
    """Kota altında fiili yükleme aralığı: 6/gün → 240 dk, 4/gün → 360 dk."""
    assert gercek_aralik_dk(6) == 240
    assert gercek_aralik_dk(4) == 360
    assert gercek_aralik_dk(2) == 720
    assert gercek_aralik_dk(0) == 0


def test_kota_uyarisi_durust() -> None:
    """Panel/log cümlesi hem kadansı hem kota gerçeğini söyler."""
    metin = kota_uyarisi(3)
    assert "480 dk" in metin
    assert "3 fırsat" in metin
    assert "480 dakikada 1" in metin
    # "her 8 saatte bir video YAYINLANIR" iddiası kurulmamalı (kota engeli var)
    assert "8 saatte 1 video" not in metin


def test_katalogda_kadans_ayari_var() -> None:
    """Panelden görülebilir: katalogda KADANS_DK kaydı olmalı."""
    from modules.ayar_katalogu import KATALOG

    kayit = [a for a in KATALOG if a["anahtar"] == "KADANS_DK"]
    assert len(kayit) == 1
    a = kayit[0]
    assert a["secenekler"] == ["480", "240", "65"]
    assert a["varsayilan"] == "480"
    assert a["etkili"] is True
    # Cron'un workflow'da yaşadığını gizleme
    assert "cron" in a["aciklama"].lower()


def test_skill_ve_kural_dosyasi_kadansi_yazar() -> None:
    """SKILL.md ve bağlayıcı kural dosyası 15 dakikayı belgelemeli."""
    skill = Path("SKILL.md").read_text(encoding="utf-8")
    assert "8 SAATTE BİR" in skill or "8 saatte bir" in skill.lower()
    assert "modules/kadans.py" in skill

    kural = Path("docs/BOBI_TV_V6_PRO_MIMARI_VE_KURALLAR.md").read_text(encoding="utf-8")
    assert "Bölüm 5" in kural
    assert "0 */8 * * *" in kural
    assert "KADANS_DK" in kural

    kadans_doc = Path("docs/KADANS.md")
    assert kadans_doc.exists()
    icerik = kadans_doc.read_text(encoding="utf-8")
    assert "480" in icerik and "360" in icerik and "6 saat" in icerik
