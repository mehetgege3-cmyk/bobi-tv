"""Serbest değer girişi + stok (kota dışı hata) sözleşmesi — 2026-11-11.

Kullanıcı kararları:
  1. "Telegram ayarları tam özgür olsun, inputlar olsun, dayatma olmasın"
  2. "Yüklesin, başarısız olursa sebebine bakalım; gerçekten kotaysa stoğa al"
  3. "1 saatte 100 izlenme almayan video silinecek"
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))

import modules.telegram_bot as tb  # noqa: E402
from modules.ayar_katalogu import ayar_getir  # noqa: E402
from modules.youtube_upload import (  # noqa: E402
    STOK_SEBEP_GECICI,
    STOK_SEBEP_KALICI,
    STOK_SEBEP_KOTA,
    KotaDolduHatasi,
    hata_siniflandir,
)

# ---------- 1) Serbest giriş ----------


def test_sayi_ayarinda_deger_gir_dugmesi_var() -> None:
    """Sayı ayarlarında '✏️ Değer gir' düğmesi olmalı (hazır seçenek dayatması yok)."""
    for anahtar in ("MIN_IZLENME_ESIGI", "IZLENME_KONTROL_DK", "GUNLUK_MAKS"):
        _metin, butonlar = tb.ekran_ayar_detay(anahtar)
        cbs = [d["callback_data"] for satir in butonlar for d in satir]
        assert f"ay:gir:{anahtar}" in cbs, f"{anahtar}: serbest giriş düğmesi yok"


def test_serbest_deger_dogrulama_araligi() -> None:
    """Serbest giriş sınırsız DEĞİL: min/max korunur, sınır dışı reddedilir."""
    a = ayar_getir("MIN_IZLENME_ESIGI")
    assert tb._sayi_dogrula(a, "50") == ("50", "")
    assert tb._sayi_dogrula(a, "abc")[0] is None
    assert tb._sayi_dogrula(a, "-1")[0] is None
    assert tb._sayi_dogrula(a, "999999")[0] is None
    a2 = ayar_getir("IZLENME_KONTROL_DK")
    assert tb._sayi_dogrula(a2, "60") == ("60", "")
    assert tb._sayi_dogrula(a2, "5")[0] is None, "15 dk altı reddedilmeli"


def test_yazilan_sayi_ayara_uygulanir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Bekleyen giriş varken yazılan sayı doğrudan kaydedilir (riskli değilse)."""
    monkeypatch.setattr(tb, "MENU_STATE_YOLU", tmp_path / "menu.json")
    cagrilar = []

    def sahte_post(url, json=None, timeout=None):
        cagrilar.append(str(url).rsplit("/", 1)[-1])
        return type("R", (), {"status_code": 200, "json": lambda self: {"ok": True, "result": {}}})()

    monkeypatch.setattr("modules.telegram_bot.requests.post", sahte_post)
    uygulanan = {}
    monkeypatch.setattr(tb, "ayar_uygula", lambda k, d, u: (uygulanan.update({k: d}) or (True, "")))
    monkeypatch.setattr(tb, "ekran_ayar_detay", lambda k: ("detay", []))

    tb._bekleyen_giris_yaz("IZLENME_KONTROL_DK")
    assert tb._bekleyen_giris_oku() == "IZLENME_KONTROL_DK"
    tb.handle_message("90")
    assert uygulanan.get("IZLENME_KONTROL_DK") == "90", f"uygulanan: {uygulanan}"


def test_riskli_deger_onaysiz_uygulanmaz(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """MIN_IZLENME_ESIGI riskli: yazılan değer ÖNCE onay ekranına gider."""
    monkeypatch.setattr(tb, "MENU_STATE_YOLU", tmp_path / "menu.json")
    monkeypatch.setattr(
        "modules.telegram_bot.requests.post",
        lambda url, json=None, timeout=None: type(
            "R", (), {"status_code": 200, "json": lambda self: {"ok": True, "result": {}}}
        )(),
    )
    uygulanan = {}
    monkeypatch.setattr(tb, "ayar_uygula", lambda k, d, u: (uygulanan.update({k: d}) or (True, "")))
    tb._bekleyen_giris_yaz("MIN_IZLENME_ESIGI")
    tb.handle_message("50")
    assert uygulanan == {}, "onay olmadan uygulanmamalı"
    assert tb._bekleyen_giris_oku() == "MIN_IZLENME_ESIGI#50", "değer onay için beklemeli"


def test_gecersiz_deger_kaydedilmez(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(tb, "MENU_STATE_YOLU", tmp_path / "menu.json")
    monkeypatch.setattr(
        "modules.telegram_bot.requests.post",
        lambda url, json=None, timeout=None: type(
            "R", (), {"status_code": 200, "json": lambda self: {"ok": True, "result": {}}}
        )(),
    )
    uygulanan = {}
    monkeypatch.setattr(tb, "ayar_uygula", lambda k, d, u: (uygulanan.update({k: d}) or (True, "")))
    tb._bekleyen_giris_yaz("IZLENME_KONTROL_DK")
    tb.handle_message("3")
    assert uygulanan == {}
    assert tb._bekleyen_giris_oku() == "IZLENME_KONTROL_DK", "bekleme sürmeli"


# ---------- 2) 1 saatte 100 izlenme kuralı ----------


def test_izlenme_kurali_1_saat() -> None:
    """Kullanıcı kuralı: 60 dk / 100 izlenme — hem katalog hem kod varsayılanı."""
    assert ayar_getir("IZLENME_KONTROL_DK")["varsayilan"] == "60"
    assert ayar_getir("MIN_IZLENME_ESIGI")["varsayilan"] == "100"
    kaynak = (KOK / "modules/youtube_upload.py").read_text(encoding="utf-8")
    assert "kontrol_suresi_dk: int = 60" in kaynak
    assert "kontrol_suresi_dk: int = 1440" not in kaynak


def test_etki_onizlemesi_uydurmuyor() -> None:
    """Silinecek sayı bilinmiyorsa 'bilinmiyor' der, sayı uydurmaz."""
    metin = tb.etki_onizlemesi("MIN_IZLENME_ESIGI", "100")
    assert "SİLİNİR" in metin
    assert ("BİLİNMİYOR" in metin) or ("silinecek" in metin.lower())


# ---------- 3) Kota dışı hata → stok ----------


@pytest.mark.parametrize(
    ("hata", "beklenen"),
    [
        (KotaDolduHatasi("kota"), STOK_SEBEP_KOTA),
        (RuntimeError("403 quotaExceeded"), STOK_SEBEP_KOTA),
        (RuntimeError("uploadLimitExceeded"), STOK_SEBEP_KOTA),
        (RuntimeError("503 backend error"), STOK_SEBEP_GECICI),
        (RuntimeError("read timeout"), STOK_SEBEP_GECICI),
        (RuntimeError("403 copyright claim"), STOK_SEBEP_KALICI),
        (RuntimeError("400 invalid metadata"), STOK_SEBEP_KALICI),
    ],
)
def test_hata_siniflandirma(hata: Exception, beklenen: str) -> None:
    assert hata_siniflandir(hata) == beklenen


def test_kota_disi_hata_videoyu_stoga_alir() -> None:
    """Eski hata: kota dışı hata sadece loglanıyor, render edilmiş MP4 kayboluyordu."""
    kaynak = (KOK / "modules/youtube_upload.py").read_text(encoding="utf-8")
    govde = kaynak.split("for idx, paket in enumerate(senaryo_paketleri):", 1)[1]
    kota_disi = govde.split("except Exception as e:", 1)[1][:600]
    assert "kuyruga_alinacaklar.append" in kota_disi, "kota dışı hata stoğa alınmalı"
    assert "stok_sebep" in kota_disi


def test_stok_kaydi_sebep_ve_deneme_tasir() -> None:
    kaynak = (KOK / "main_pipeline.py").read_text(encoding="utf-8")
    assert '"stok_sebep": sebep' in kaynak
    assert '"deneme": deneme' in kaynak
