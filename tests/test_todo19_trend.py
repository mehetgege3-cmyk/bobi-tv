"""TODO 19 — 7 günlük trend ekranı (Kaan).

Kurallar: tahmin açıkça "tahmin" etiketli, veri yoksa "bilinmiyor",
kota tavanı aşılsa bile ekran çökmez.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import modules.telegram_bot as tb  # noqa: E402


@pytest.fixture(autouse=True)
def _ortam(monkeypatch, tmp_path):
    monkeypatch.setattr(tb, "CHAT_ID", "123456789")
    monkeypatch.setattr(tb, "BOT_TOKEN", "fake:token")
    monkeypatch.setattr(tb, "MENU_STATE_YOLU", tmp_path / "menu.json")


def test_veri_yoksa_bilinmiyor_der(monkeypatch):
    monkeypatch.setattr(tb, "_son_7gun_seri", lambda: [0.0] * 7)
    metin, _ = tb.ekran_7gun()
    assert "Veri yok" in metin
    assert tb.BILINMIYOR in metin


def test_trend_sparkline_ve_toplam_gosterir(monkeypatch):
    monkeypatch.setattr(tb, "_son_7gun_seri", lambda: [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    metin, _ = tb.ekran_7gun()
    assert "▁" in metin and "█" in metin
    assert "21 video" in metin  # 0+1+2+3+4+5+6


def test_tahmin_kelimesi_acikca_yazilir(monkeypatch):
    """Kullanıcı tahmini gerçek veri sanmamalı."""
    monkeypatch.setattr(tb, "_son_7gun_seri", lambda: [1.0] * 7)
    monkeypatch.setattr(tb, "_bugun_arsiv_ozeti", lambda: (5, 3))
    metin, _ = tb.ekran_7gun()
    assert "Tahmin" in metin or "tahmin" in metin


def test_kalite_kaydi_yoksa_bilinmiyor(monkeypatch):
    monkeypatch.setattr(tb, "_son_7gun_seri", lambda: [1.0] * 7)
    metin, _ = tb.ekran_7gun()
    assert "Kalite geçme" in metin


def test_ekran_15_satiri_gecmez(monkeypatch):
    monkeypatch.setattr(tb, "_son_7gun_seri", lambda: [2.0] * 7)
    metin, _ = tb.ekran_7gun()
    assert len([s for s in metin.split("\n") if s.strip()]) <= 15


def test_rapor_ekranindan_trend_erisimi():
    _, butonlar = tb.ekran_performans()
    duz = [b["callback_data"] for satir in butonlar for b in satir]
    assert "rapor_7gun" in duz
