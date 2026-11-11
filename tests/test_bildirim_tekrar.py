"""Bildirim tekrar koruması (kota fırtınası) — TODO 23/24 tamamlayıcısı.

Gözlenen: aynı "Kota dolu — videolar stoğa alındı" olayı 15 dakikalık kadansla
günde onlarca kez kuyruğa yazılıyordu (state dosyasında 50 satır spam).
Kural: aynı başlık+seviye TAZE penceresi içinde tekrar gelirse yutulur.
"""
from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import modules.bildirim as bd  # noqa: E402

SIMDI = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)  # TR 15:00 → sessiz saat dışı


@pytest.fixture(autouse=True)
def _ortam(monkeypatch, tmp_path):
    monkeypatch.setattr(bd, "DURUM_YOLU", tmp_path / "bildirim.json")
    monkeypatch.setattr(bd, "_gonder", lambda metin: True)
    return tmp_path


def _bekleyen() -> list[dict]:
    return bd.durum_oku().get("bekleyen") or []


def test_ayni_olay_taze_pencerede_tekrar_kuyruga_yazilmaz():
    bd.bildir("Kota dolu", "1 video stokta", seviye=bd.OZET, simdi=SIMDI)
    bd.bildir("Kota dolu", "1 video stokta", seviye=bd.OZET, simdi=SIMDI + timedelta(minutes=5))
    bd.bildir("Kota dolu", "1 video stokta", seviye=bd.OZET, simdi=SIMDI + timedelta(minutes=20))
    assert len(_bekleyen()) == 1, "aynı olay 30 dk içinde tek satır olmalı"


def test_pencere_dolunca_yeniden_yazilir():
    bd.bildir("Kota dolu", "", seviye=bd.OZET, simdi=SIMDI)
    bd.bildir(
        "Kota dolu", "", seviye=bd.OZET, simdi=SIMDI + timedelta(seconds=bd.TEKRAR_PENCERESI_SN + 5)
    )
    assert len(_bekleyen()) == 2


def test_farkli_baslik_ayri_satir():
    bd.bildir("Kota dolu", "", seviye=bd.OZET, simdi=SIMDI)
    bd.bildir("Yükleme başarısız", "", seviye=bd.OZET, simdi=SIMDI)
    assert len(_bekleyen()) == 2


def test_farkli_seviye_ayri_satir():
    """NORMAL gündüz anında gider; kuyruğa girmesi için sessiz saat kullanılır."""
    gece = datetime(2026, 11, 11, 2, 0, tzinfo=UTC)  # TR 05:00 → sessiz
    bd.bildir("Aynı başlık", "", seviye=bd.OZET, simdi=gece)
    bd.bildir("Aynı başlık", "", seviye=bd.NORMAL, simdi=gece)
    assert len(_bekleyen()) == 2


def test_sessiz_saatte_biriken_normal_tek_satir(monkeypatch):
    gece = datetime(2026, 11, 11, 2, 0, tzinfo=UTC)  # TR 05:00 → sessiz
    for dk in (0, 15, 30):
        bd.bildir("Kota dolu", "", seviye=bd.NORMAL, simdi=gece + timedelta(minutes=dk))
    assert len(_bekleyen()) == 1


def test_zaman_damgasi_yoksa_tekrar_sayilmaz():
    """Eski kayıtlarda zaman yoksa yutmayız (veri kaybı riski alınmaz)."""
    bd.durum_yaz({"bekleyen": [{"baslik": "X", "govde": "", "seviye": bd.OZET}]})
    assert bd._kuyruga_ekle("X", "", bd.OZET, SIMDI) == 1
    assert len(_bekleyen()) == 2


def test_kuyruk_50_ile_sinirli():
    for i in range(60):
        bd._kuyruga_ekle(f"olay {i}", "", bd.OZET, SIMDI + timedelta(seconds=i))
    assert len(_bekleyen()) == 50
