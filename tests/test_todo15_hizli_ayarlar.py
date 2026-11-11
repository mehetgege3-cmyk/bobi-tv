"""TODO 15 — Derinlik 3 → 2: Hızlı Ayarlar.

Kabul kriteri: günlük hedef değiştirme 3 dokunuştan 2'ye iner
(kök → hızlı ayarlar → ➕). Riskli ayar yine onaydan geçer.
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
    monkeypatch.setattr(tb, "_BEKLEYEN_YOLU", tmp_path / "bekleyen.json", raising=False)


def test_ayarlar_kokunde_hizli_ayarlar_butonu_var():
    metin, butonlar = tb.ekran_ayar_kok()
    duz = [b["callback_data"] for satir in butonlar for b in satir if "callback_data" in b]
    assert "ay:hizli" in duz, "kökten hızlı ayarlara giriş yok (derinlik 2'ye inmez)"
    assert butonlar[0][0]["callback_data"] == "ay:hizli", "hızlı ayarlar ilk buton olmalı"


def test_hizli_ayarlar_ekrani_onemli_ayarlari_gosterir():
    metin, butonlar = tb.ekran_hizli_ayarlar()
    for anahtar in tb.HIZLI_AYARLAR:
        a = tb.ayar_getir(anahtar)
        assert a["etiket"] in metin, f"{anahtar} hızlı ekranda yok"
    duz = " ".join(b["callback_data"] for satir in butonlar for b in satir)
    assert "ay:d:" in duz, "stepper butonu yok"
    assert "ay:t:" in duz, "toggle butonu yok"


def test_gunluk_hedef_iki_dokunusta_degisir(monkeypatch):
    """KÖK → HIZLI EKRAN → ➕ : toplam 2 dokunuş (eski yol 3 idi)."""
    kaydedilen = {}
    monkeypatch.setattr(tb, "ayar_uygula", lambda a, d, k: kaydedilen.update({a: d}) or (True, ""))
    monkeypatch.setattr(tb, "_deger_ve_kaynak", lambda a: ("4", "state"))
    monkeypatch.setattr(tb, "answer_callback", lambda *a, **k: True)
    monkeypatch.setattr(tb, "_ekran_goster", lambda *a, **k: True)
    tb._hizli_stepper("GUNLUK_HEDEF", +1, "cb")
    assert kaydedilen.get("GUNLUK_HEDEF") == "5"


def test_stepper_ust_sinirda_durur(monkeypatch):
    kaydedilen = {}
    monkeypatch.setattr(tb, "ayar_uygula", lambda a, d, k: kaydedilen.update({a: d}) or (True, ""))
    monkeypatch.setattr(tb, "_deger_ve_kaynak", lambda a: ("6", "state"))  # GUNLUK_HEDEF max 6
    monkeypatch.setattr(tb, "answer_callback", lambda *a, **k: True)
    monkeypatch.setattr(tb, "_ekran_goster", lambda *a, **k: True)
    tb._hizli_stepper("GUNLUK_HEDEF", +1, "cb")
    assert "GUNLUK_HEDEF" not in kaydedilen, "sınır aşıldı"


def test_riskli_ayar_hizli_yolda_da_onaya_gider(monkeypatch):
    """KOTA_DOLU_DAVRANIS riskli: hızlı ekrandan değişse bile ONAY ister."""
    kaydedilen = {}
    monkeypatch.setattr(tb, "ayar_uygula", lambda a, d, k: kaydedilen.update({a: d}) or (True, ""))
    monkeypatch.setattr(tb, "answer_callback", lambda *a, **k: True)
    monkeypatch.setattr(tb, "_ekran_goster", lambda *a, **k: True)
    monkeypatch.setattr(tb, "_bekleyen_giris_yaz", lambda x: True)
    onay_ekrani = []
    monkeypatch.setattr(tb, "ekran_onay_deger", lambda a, d: onay_ekrani.append((a, d)) or ("onay", []))
    tb._hizli_uygula("KOTA_DOLU_DAVRANIS", "1", "cb")
    assert onay_ekrani, "riskli ayar onay ekranı olmadan uygulandı!"
    assert not kaydedilen


def test_toggle_anahtar_ayari_tersine_cevirir(monkeypatch):
    kaydedilen = {}
    monkeypatch.setattr(tb, "ayar_uygula", lambda a, d, k: kaydedilen.update({a: d}) or (True, ""))
    monkeypatch.setattr(tb, "_deger_ve_kaynak", lambda a: ("0", "state"))
    monkeypatch.setattr(tb, "answer_callback", lambda *a, **k: True)
    monkeypatch.setattr(tb, "_ekran_goster", lambda *a, **k: True)
    tb._hizli_toggle("YUKLEME_ATLA", "cb")
    assert kaydedilen.get("YUKLEME_ATLA") == "1"


def test_stepper_tek_dokunusta_bir_adim_ilerler(monkeypatch, tmp_path):
    """CANLI BUG: hızlı ekranda ➕ basınca değer 4'ten 6'ya atladı.

    Sebep: `_hizli_stepper` mevcut değeri state'ten okuyordu; araya giren
    panel meta yazımı / katalog varsayılanı yüzünden iki adım attı.
    Kural: ➕ TEK dokunuşta TEK adım (GUNLUK_HEDEF için 1).
    """
    monkeypatch.setattr(tb, "MENU_STATE_YOLU", tmp_path / "m.json")
    monkeypatch.setattr(tb, "AYARLAR_STATE_YOLU", tmp_path / "a.json")
    monkeypatch.setattr(tb, "GECMIS_YOLU", tmp_path / "g.json")
    monkeypatch.setattr(tb, "answer_callback", lambda *a, **k: True)
    monkeypatch.setattr(tb, "panel_goster", lambda *a, **k: True)
    import modules.ayar_deposu as ad

    ad.kaydet({"GUNLUK_HEDEF": "4"}, tb.AYARLAR_STATE_YOLU)
    tb._hizli_stepper("GUNLUK_HEDEF", +1, "cb")
    assert ad.state_ham_ayarlari(tb.AYARLAR_STATE_YOLU).get("GUNLUK_HEDEF") == "5"


def test_stepper_tek_dokunusta_bir_adim_geri(monkeypatch, tmp_path):
    monkeypatch.setattr(tb, "MENU_STATE_YOLU", tmp_path / "m.json")
    monkeypatch.setattr(tb, "AYARLAR_STATE_YOLU", tmp_path / "a.json")
    monkeypatch.setattr(tb, "GECMIS_YOLU", tmp_path / "g.json")
    monkeypatch.setattr(tb, "answer_callback", lambda *a, **k: True)
    monkeypatch.setattr(tb, "panel_goster", lambda *a, **k: True)
    import modules.ayar_deposu as ad

    ad.kaydet({"GUNLUK_HEDEF": "4"}, tb.AYARLAR_STATE_YOLU)
    tb._hizli_stepper("GUNLUK_HEDEF", -1, "cb")
    assert ad.state_ham_ayarlari(tb.AYARLAR_STATE_YOLU).get("GUNLUK_HEDEF") == "3"
