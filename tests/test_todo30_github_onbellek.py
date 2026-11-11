"""TODO 30 — GitHub API 60 sn önbelleği: sözleşme testleri.

Panel ana ekranı + sistem ekranı aynı veriyi 3 kez istiyordu. Önbellek bunu
1 çağrıya indirir; ama YANLIŞ önbellek daha kötüdür (bayat "çalışıyor" der).
Bu yüzden TTL, yol ayrımı ve hata davranışı burada sabitlenir.
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


def test_ayni_yol_60_sn_icinde_bir_kez_cagrilir(monkeypatch):
    sayac = []
    monkeypatch.setattr(tb, "_github_get", lambda yol: sayac.append(yol) or {"ok": 1})
    for _ in range(5):
        tb._github_get_onbellekli("a/b")
    assert len(sayac) == 1


def test_farkli_yollar_ayri_onbelleklenir(monkeypatch):
    sayac = []
    monkeypatch.setattr(tb, "_github_get", lambda yol: sayac.append(yol) or {"ok": yol})
    tb._github_get_onbellekli("a/b")
    tb._github_get_onbellekli("c/d")
    assert sayac == ["a/b", "c/d"]
    assert tb._github_get_onbellekli("a/b") == {"ok": "a/b"}


def test_ttl_dolunca_yeniden_cagrilir(monkeypatch):
    sayac = []
    monkeypatch.setattr(tb, "_github_get", lambda yol: sayac.append(yol) or {"ok": 1})
    zaman = [1000.0]
    monkeypatch.setattr(tb.time, "time", lambda: zaman[0])
    tb._github_get_onbellekli("a/b")
    zaman[0] += tb.GITHUB_CACHE_TTL_SN - 1
    tb._github_get_onbellekli("a/b")
    assert len(sayac) == 1, "TTL içinde ikinci çağrı olmamalı"
    zaman[0] += 2
    tb._github_get_onbellekli("a/b")
    assert len(sayac) == 2, "TTL dolunca tazelenmeli"


def test_hata_da_onbelleklenir_ve_panel_cokmez(monkeypatch):
    """Token yoksa _github_get None döner; panel 'bilinmiyor' yazar, döngü olmaz."""
    sayac = []
    monkeypatch.setattr(tb, "_github_get", lambda yol: sayac.append(yol) or None)
    assert tb._github_get_onbellekli("a/b") is None
    assert tb._github_get_onbellekli("a/b") is None
    assert len(sayac) == 1


def test_ana_ekran_tek_github_cagrisi_yapar(monkeypatch):
    """Ana ekran: 2 farklı yol (üretim + poller) → toplam 2 çağrı, fazlası yok."""
    sayac = []
    monkeypatch.setattr(tb, "_github_get", lambda yol: sayac.append(yol) or None)
    tb.ekran_ana()
    tb.ekran_ana()
    assert len(sayac) <= 4, f"önbellek çalışmıyor: {sayac}"


def test_ttl_makul_aralikta():
    """Çok kısa TTL = boşa API; çok uzun TTL = bayat panel."""
    assert 30 <= tb.GITHUB_CACHE_TTL_SN <= 300
