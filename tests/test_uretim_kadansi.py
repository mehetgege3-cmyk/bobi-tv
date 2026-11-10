"""Üretim kadansı testleri — "her 15 dakikada ÜRET + YÜKLE" (kullanıcı kararı).

Kullanıcı şikâyeti (2026-11-11): "Üret'e basıyorum, video çıkmıyor."
Kök neden: GUNLUK_HEDEF dolunca tur no-op oluyordu → gün boyunca ÜRETİM yoktu.
Bu testler o hatanın geri gelmesini engeller.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main_pipeline as mp  # noqa: E402


@pytest.fixture(autouse=True)
def _tavan(monkeypatch):
    monkeypatch.setattr(mp, "URETIM_TAVANI", 288)
    monkeypatch.setattr(mp, "TUR_BASINA_URETIM", 1)
    monkeypatch.setattr(mp, "GUNLUK_HEDEF", 4)
    monkeypatch.setattr(mp, "GUNLUK_MAKS", 6)


def test_gunluk_hedef_dolu_olsa_da_uretim_surer():
    """REGRESYON: hedef 4/4 doluyken tur no-op OLMAMALI (eski hata)."""
    assert mp.bu_tur_hesapla(bugunki=4, bugun_yuklenen=4) == 1


def test_kota_dolu_olsa_da_uretim_surer():
    """Kota (yükleme) dolu → video yine üretilir, stoğa yazılır."""
    assert mp.bu_tur_hesapla(bugunki=10, bugun_yuklenen=6) == 1


def test_tur_basina_birden_fazla_uretilmez():
    """15 dakikalık kadans: tek koşuda tek video (284 video denemesi olmaz)."""
    assert mp.bu_tur_hesapla(bugunki=0, bugun_yuklenen=0) == 1


def test_uretim_tavani_dolunca_durur():
    """Üretim tavanı (stok büyüklüğü) tek gerçek durdurucudur."""
    assert mp.bu_tur_hesapla(bugunki=288, bugun_yuklenen=0) == 0


def test_tavan_son_video_uretilir():
    assert mp.bu_tur_hesapla(bugunki=287, bugun_yuklenen=0) == 1


def test_kota_sayaci_stok_kayitlarini_saymaz(tmp_path, monkeypatch):
    """Kota YALNIZ yayına alınanları sayar; stokta bekleyen (kuyruk) kayıtlar
    kotayı tüketmiş gibi gösterilmemeli — eski hata buydu."""
    arsiv = tmp_path / "videos.json"
    import json

    bugun = mp.datetime.now(mp.timezone.utc).strftime("%Y-%m-%d")
    arsiv.write_text(
        json.dumps(
            {
                "a": {"tarih": f"{bugun}T10:00:00+00:00", "durum": "yayinda"},
                "b": {"tarih": f"{bugun}T10:05:00+00:00", "durum": "yayinda"},
                "c": {"tarih": f"{bugun}T10:10:00+00:00", "durum": "silindi_dusuk_izlenme"},
                "d": {"tarih": f"{bugun}T10:15:00+00:00", "durum": "kaldirildi"},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(mp, "ARSIV", arsiv)
    assert mp.bugunki_video_sayisi() == 4      # üretim tavanı: hepsi sayılır
    assert mp.bugun_yuklenen_sayisi() == 2     # kota: yalnız yayında olanlar
