"""TODO 25 — İmzalı + süreli callback (Emre / güvenlik).

Eski panel mesajındaki buton haftalar sonra çalışmamalı; kopyalanmış
callback_data başka sohbette işlem yapamamalı. 64 bayt sınırı korunur.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import modules.telegram_bot as tb  # noqa: E402


@pytest.fixture(autouse=True)
def _ortam(monkeypatch, tmp_path):
    monkeypatch.setattr(tb, "CHAT_ID", "123456789")
    monkeypatch.setattr(tb, "BOT_TOKEN", "fake:token")
    monkeypatch.setattr(tb, "MENU_STATE_YOLU", tmp_path / "menu.json")


def test_imzali_callback_64_bayti_asmaz():
    """Telegram callback_data sınırı: 64 BAYT. Aşılırsa buton hiç çalışmaz."""
    for aksiyon in tb.IMZALI_AKSIYONLAR:
        c = tb.imzali_callback(aksiyon)
        assert len(c.encode("utf-8")) <= 64, f"{aksiyon} → {len(c.encode())} bayt"


def test_gecerli_imza_dogrulanir():
    c = tb.imzali_callback("uret_onay")
    gecerli, aksiyon = tb.imza_dogrula(c)
    assert gecerli and aksiyon == "uret_onay"


def test_sahte_imza_reddedilir():
    gecerli, sebep = tb.imza_dogrula("uret_onay:1a2b3c:deadbeef00")
    assert not gecerli and "imza" in sebep


def test_suresi_gecmis_imza_reddedilir():
    eski = tb.imzali_callback("uret_onay", simdi=time.time() - tb.IMZA_GECERLILIK_SN - 10)
    gecerli, sebep = tb.imza_dogrula(eski)
    assert not gecerli and sebep == "süresi geçti"


def test_farkli_chat_ayni_imzayi_uretemez(monkeypatch):
    """Anahtar chat_id'ye bağlı: başka sohbetten kopyalanan buton çalışmaz."""
    c = tb.imzali_callback("uret_onay")
    monkeypatch.setattr(tb, "CHAT_ID", "999999999")
    gecerli, _ = tb.imza_dogrula(c)
    assert not gecerli, "chat_id değişince imza geçersiz olmalı"


def test_farkli_token_ayni_imzayi_uretemez(monkeypatch):
    c = tb.imzali_callback("uret_onay")
    monkeypatch.setattr(tb, "BOT_TOKEN", "baska:token")
    gecerli, _ = tb.imza_dogrula(c)
    assert not gecerli


def test_imza_gerekli_aksiyonlar():
    assert tb.imza_gerekli("uret_onay")
    assert tb.imza_gerekli("ay:onay")
    assert not tb.imza_gerekli("menu_main")
    assert not tb.imza_gerekli("rapor_goster")


def test_bayat_buton_calisinca_uyari_verir_ve_menu_doner(monkeypatch):
    cevaplar, ekranlar = [], []
    monkeypatch.setattr(tb, "answer_callback", lambda cid, t="", **k: cevaplar.append(t) or True)
    monkeypatch.setattr(tb, "_ekran_goster", lambda *a, **k: ekranlar.append(a) or True)
    tetiklendi = []
    monkeypatch.setattr(tb, "trigger_production_kontrollu", lambda: tetiklendi.append(1) or "ok")
    eski = tb.imzali_callback("uret_onay", simdi=time.time() - 10**5)
    tb._handle_callback_icerde(eski, "cb1", 1)
    assert tetiklendi == [], "bayat buton üretim tetikledi!"
    assert any("eskidi" in c for c in cevaplar)
    assert ekranlar, "menüye dönmedi"


def test_gecerli_buton_aksiyonu_calistirir(monkeypatch):
    monkeypatch.setattr(tb, "answer_callback", lambda *a, **k: True)
    monkeypatch.setattr(tb, "_ekran_goster", lambda *a, **k: True)
    tetiklendi = []
    monkeypatch.setattr(tb, "trigger_production_kontrollu", lambda: tetiklendi.append(1) or "ok")
    tb._handle_callback_icerde(tb.imzali_callback("uret_onay"), "cb2", 1)
    assert len(tetiklendi) == 1


def test_onay_ekrani_imzali_buton_uretir(monkeypatch, tmp_path):
    monkeypatch.setattr(tb, "_cooldown_dosyasi", lambda: tmp_path / "cd.json")
    _, butonlar = tb.ekran_uret_onay()
    cd = [b["callback_data"] for satir in butonlar for b in satir if "callback_data" in b]
    onay = next(c for c in cd if c.startswith("uret_onay"))
    assert onay.count(":") == 2, "onay butonu imza taşımıyor"
    assert tb.imza_dogrula(onay)[0] is True
