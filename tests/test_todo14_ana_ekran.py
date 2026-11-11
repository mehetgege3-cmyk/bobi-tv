"""TODO 14 — Ana ekran = canlı durum kartı.

Kurallar: uydurma sayı yok (veri okunamazsa "bilinmiyor"), 15 satır sınırı,
kota doluysa birincil buton dürüst olmalı, ekran tek panel mesajıyla açılmalı.
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
    tb._GITHUB_CACHE.clear()


def test_ana_ekran_canli_ozet_icerir():
    metin, butonlar = tb.ekran_ana()
    # SPEC DEĞİŞTİ (2026-11-11, "kotayı kaldır"): "Kota" satırı yerine
    # "Bugün yüklenen … (tavan YOK)" satırı var.
    for parca in ("Bugün:", "Bugün yüklenen", "Stok", "Son koşu", "gecikme"):
        assert parca in metin, f"ana ekranda '{parca}' satırı yok"
    # 4 buton (2x2) korunur
    assert sum(len(s) for s in butonlar) == 4


def test_ana_ekran_15_satiri_gecmez():
    metin, _ = tb.ekran_ana()
    assert len([s for s in metin.split("\n") if s.strip()]) <= 15


def test_veri_yoksa_bilinmiyor_der_ve_ufak_sayi_uydurmaz(monkeypatch):
    """GitHub okunamazsa 'bilinmiyor' yazar; sayı uydurmaz."""
    monkeypatch.setattr(tb, "_github_get_onbellekli", lambda yol: None)
    tb._GITHUB_CACHE.clear()
    metin, _ = tb.ekran_ana()
    assert tb.BILINMIYOR in metin


def test_kota_dolu_diye_bir_durum_yok(monkeypatch):
    """SPEC DEĞİŞTİ (2026-11-11, kullanıcı: "kotayı kaldır").

    Eski spec: kota doluysa birincil buton "⏳ Kota dolu" olurdu.
    Yeni spec: kota kavramı yok → kota_dolu_mu True dönse bile buton her zaman
    "🎬 Üret"tir ve metinde "Kota DOLU" geçmez.
    """
    import modules.kota_state as ks

    monkeypatch.setattr(ks, "kota_dolu_mu", lambda: True)
    metin, butonlar = tb.ekran_ana()
    etiketler = [b["text"] for satir in butonlar for b in satir]
    assert "🎬 Üret" in etiketler
    assert "⏳ Kota dolu" not in etiketler
    assert "Kota DOLU" not in metin


def test_goreli_ilerleme_cubugu():
    assert tb._ilerleme_cubugu(0.5, 6) == "▰▰▰▱▱▱"
    assert tb._ilerleme_cubugu(0.0, 4) == "▱▱▱▱"
    assert tb._ilerleme_cubugu(2.0, 4) == "▰▰▰▰"   # taşma kırpılır


def test_github_onbellegi_60_sn(monkeypatch):
    """Sistem ekranı 3 ardışık çağrı yapıyordu; önbellek tek çağrıya indirir."""
    sayac = []
    monkeypatch.setattr(tb, "_github_get", lambda yol: sayac.append(yol) or {"ok": 1})
    tb._GITHUB_CACHE.clear()
    tb._github_get_onbellekli("x/y")
    tb._github_get_onbellekli("x/y")
    tb._github_get_onbellekli("x/y")
    assert len(sayac) == 1, "önbellek çalışmıyor — her çağrı GitHub'a gidiyor"


def test_ana_ekran_tek_panel_mesaji_acar(monkeypatch, tmp_path):
    cagrilar = []

    def sahte_api(yontem, veri):
        cagrilar.append(yontem)
        return {"ok": True, "result": {"message_id": 9}}

    monkeypatch.setattr(tb, "api_call", sahte_api)
    tb.menyu_gonder()
    assert sum(1 for y in cagrilar if y == "sendMessage") == 1
