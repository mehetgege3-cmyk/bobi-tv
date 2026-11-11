"""TODO 20 — Kuyruk ekranlarının PANEL kuralları ve callback akışı.

Kurallar: tek panel (edit-in-place), her callback'a answerCallbackQuery,
satır başına ≤3 buton, etiket ≤20 karakter, "← Geri" her ekranda,
riskli işlem onaydan geçer, callback_data ≤64 bayt + izinli prefix.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import modules.kuyruk_yonetimi as ky  # noqa: E402
import modules.telegram_bot as tb  # noqa: E402

EKRANLAR = {
    "kuyruk_liste": tb.ekran_kuyruk,
    "kuyruk_at_onay": tb.ekran_kuyruk_at_onay,
    "kuyruk_at_uygula": tb.ekran_kuyruk_at_uygula,
    "kuyruk_geri_al": tb.ekran_kuyruk_geri_al,
}


@pytest.fixture(autouse=True)
def _ortam(monkeypatch, tmp_path):
    monkeypatch.setattr(tb, "CHAT_ID", "123456789")
    monkeypatch.setattr(tb, "BOT_TOKEN", "fake:token")
    monkeypatch.setattr(tb, "MENU_STATE_YOLU", tmp_path / "menu.json")
    monkeypatch.setattr(ky, "KUYRUK_DIZINI", tmp_path / "queue")
    monkeypatch.setattr(ky, "ATILAN_DIZINI", tmp_path / "arsiv" / "atilan")
    (tmp_path / "queue").mkdir()


def _kayit(adi: str = "v1") -> None:
    veri = {"dosya_adi": adi, "baslik": "Deneme başlık", "stok_sebep": "kota"}
    (ky.KUYRUK_DIZINI / f"{adi}.json").write_text(json.dumps(veri), encoding="utf-8")


def _takip_et(monkeypatch) -> list[tuple[str, str]]:
    """answerCallbackQuery + panel gönderimini yakalar (gerçek ağ yok)."""
    cagrilar: list[tuple[str, str]] = []

    def sahte_answer(cb: str, metin: str = "") -> None:
        cagrilar.append(("answer", cb))

    def sahte_ekran(demet) -> None:
        cagrilar.append(("ekran", demet[0]))

    monkeypatch.setattr(tb, "answer_callback", sahte_answer)
    monkeypatch.setattr(tb, "_ekran_goster", sahte_ekran)
    return cagrilar


# --- Buton/etiket kuralları ----------------------------------------------


@pytest.mark.parametrize("ad", sorted(EKRANLAR))
def test_buton_kurallari(ad):
    metin, butonlar = EKRANLAR[ad]()
    assert metin.strip(), "ekran boş olmamalı"
    for satir in butonlar:
        assert len(satir) <= 3, f"{ad}: satır başına en fazla 3 buton"
        for b in satir:
            assert len(b["text"]) <= 20, f"{ad}: etiket 20 karakteri aşamaz — {b['text']}"
            assert len(b["callback_data"].encode()) <= 64
    duz = [b for satir in butonlar for b in satir]
    assert any(b["callback_data"] == "menu_main" for b in duz), f"{ad}: '← Geri/Menü' yok"


@pytest.mark.parametrize("ad", sorted(EKRANLAR))
def test_ekran_15_satiri_gecmez(ad):
    metin, _ = EKRANLAR[ad]()
    assert len([s for s in metin.split("\n") if s.strip()]) <= 15


def test_tum_kuyruk_callbackleri_kayitli():
    """CALLBACK_DERINLIK'te olmayan callback izinli sayılmaz (güvenlik)."""
    for ad in EKRANLAR:
        assert ad in tb.CALLBACK_DERINLIK, f"{ad} derinlik tablosunda yok"


def test_panel_kurali_secret_ve_token_gostermez(monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "ghp_gizli_token_123")
    for ad, fn in EKRANLAR.items():
        metin, _ = fn()
        assert "ghp_" not in metin, f"{ad}: token panelde görünmemeli"
        assert "Bearer" not in metin


# --- Akış ----------------------------------------------------------------


def test_dolu_kuyruk_at_oncesi_onay_ister():
    _kayit()
    _, butonlar = tb.ekran_kuyruk()
    duz = {b["callback_data"] for satir in butonlar for b in satir}
    assert "kuyruk_at_onay" in duz
    assert "kuyruk_at_uygula" not in duz, "onay ekranı atlanamaz"


def test_onay_ekrani_onay_ve_vazgec_sunar():
    _kayit()
    metin, butonlar = tb.ekran_kuyruk_at_onay()
    duz = {b["callback_data"] for satir in butonlar for b in satir}
    assert {"kuyruk_at_uygula", "kuyruk_liste"} <= duz
    assert "ONAY" in metin


def test_onay_ekrani_hicbir_sey_silmez():
    _kayit()
    tb.ekran_kuyruk_at_onay()
    assert (ky.KUYRUK_DIZINI / "v1.json").exists(), "onay ekranı yalnız OKUMALI"


def test_uygula_tasir_ve_mesaji_durust_yazar():
    _kayit()
    metin, _ = tb.ekran_kuyruk_at_uygula()
    assert "atıldı" in metin
    assert "SİLİNMEDİ" in metin
    assert not (ky.KUYRUK_DIZINI / "v1.json").exists()
    assert list(ky.ATILAN_DIZINI.glob("*.json"))


def test_uygula_bos_kuyrukta_yalan_soylemez():
    metin, _ = tb.ekran_kuyruk_at_uygula()
    assert "Atılacak kayıt yok" in metin
    assert "atıldı" not in metin


def test_geri_al_atilan_kaydi_dondurur():
    _kayit()
    tb.ekran_kuyruk_at_uygula()
    metin, _ = tb.ekran_kuyruk_geri_al()
    assert "geri alındı" in metin
    assert (ky.KUYRUK_DIZINI / "v1.json").exists()


def test_geri_al_bos_copte_durust():
    metin, _ = tb.ekran_kuyruk_geri_al()
    assert "Geri alınacak kayıt yok" in metin


# --- handle_callback entegrasyonu ---------------------------------------


@pytest.mark.parametrize("cb", sorted(EKRANLAR))
def test_callback_her_zaman_cevap_verir(monkeypatch, cb):
    """Kural: her callback answerCallbackQuery alır (buton 'dönüyor' kalmaz)."""
    cagrilar = _takip_et(monkeypatch)
    tb.handle_callback(cb, "cb-1")
    assert ("answer", "cb-1") in cagrilar
    assert any(c[0] == "ekran" for c in cagrilar)


def test_handle_callback_atmayi_onay_ve_uygulama_ile_ayirir(monkeypatch):
    _kayit()
    cagrilar = _takip_et(monkeypatch)
    tb.handle_callback("kuyruk_at_onay", "cb-a")
    metin_onay = [c[1] for c in cagrilar if c[0] == "ekran"][-1]
    assert "ONAY GEREKİYOR" in metin_onay
    assert (ky.KUYRUK_DIZINI / "v1.json").exists(), "onay adımı dosyaya dokunmamalı"

    tb.handle_callback("kuyruk_at_uygula", "cb-b")
    metin_sonuc = [c[1] for c in cagrilar if c[0] == "ekran"][-1]
    assert "atıldı" in metin_sonuc
    assert not (ky.KUYRUK_DIZINI / "v1.json").exists()
