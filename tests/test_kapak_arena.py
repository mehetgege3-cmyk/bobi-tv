"""Kapak hattı testleri — Arena AI destekli kapak (kullanıcı isteği 2026-11-11).

Kural: kapak hattı hiçbir koşulda pipeline'ı ÇÖKERTMEZ; Arena yoksa yerel
üreticiye düşer, o da yoksa kapak gönderilmez ("" döner).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules import kapak_arena as ka  # noqa: E402


def test_sinir_dikey_kapak_kabul_edilir(tmp_path):
    """1080x1920 (Shorts dikey) kapak REDDEDİLMEMELİ: kural 1280x720 YouTube
    standardıdır; dikeyde uzun kenar >=1280 ve kısa kenar >=720 aranır."""
    from PIL import Image

    jpg = tmp_path / "dikey.jpg"
    Image.new("RGB", (1080, 1920), (255, 0, 0)).save(jpg, quality=85)
    assert ka._sinirlara_uygun(str(jpg)) is True


def test_sinir_kucuk_kapak_reddedilir(tmp_path):
    from PIL import Image

    jpg = tmp_path / "kucuk.jpg"
    Image.new("RGB", (640, 480), (255, 0, 0)).save(jpg, quality=85)
    assert ka._sinirlara_uygun(str(jpg)) is False


def test_sinir_olmayan_dosya_reddedilir(tmp_path):
    assert ka._sinirlara_uygun(str(tmp_path / "yok.jpg")) is False


def test_ilk_kare_video_yoksa_none(tmp_path):
    assert ka.ilk_kare_cikar(str(tmp_path / "yok.mp4"), str(tmp_path / "k.jpg")) is None


def test_arena_yoksa_cokmez_ve_ciktilar_tutarli(tmp_path, monkeypatch):
    """Arena önerisi None gelse bile fonksiyon sözlük döner, paket anahtarları
    tutarlı kalır (kapak_dosyasi ya yol ya None)."""
    monkeypatch.setattr(ka, "arena_kapak_onerisi", lambda p: None)
    monkeypatch.chdir(tmp_path)
    paket = {"baslik": "Test", "final_video": str(tmp_path / "yok.mp4"), "dosya_adi": "t"}
    sonuc = ka.kapak_sec_ve_hazirla(paket)
    assert isinstance(sonuc, dict)
    assert "secelen" not in sonuc
    assert sonuc["arena"] is False
    assert paket.get("kapak_dosyasi") is None or paket.get("kapak_dosyasi") == sonuc["kapak"]


def test_secim_arena_varsa_ilk_kare_adayini_secer(tmp_path, monkeypatch):
    """Kullanıcı isteği: 'ilk kareye yerleştirip seçilsin'. Arena önerisi varsa
    A adayı (1. kare + Arena şok başlık) seçilir."""
    from PIL import Image

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        ka, "arena_kapak_onerisi",
        lambda p: {"sok_baslik": "KİMSE BEKLEMEDİ", "vurgu_kelime": "KİMSE",
                   "renk": "#FF2D55", "gerekce": "merak"},
    )
    kare = tmp_path / "kare.jpg"
    Image.new("RGB", (1080, 1920), (10, 10, 10)).save(kare, quality=90)
    monkeypatch.setattr(ka, "ilk_kare_cikar", lambda v, c: str(kare))
    # yerel üretici kapalı → yalnız A ve B adayları
    monkeypatch.setitem(sys.modules, "modules.kapak_uret", None)

    paket = {"baslik": "Test", "final_video": str(tmp_path / "v.mp4"), "dosya_adi": "a"}
    sonuc = ka.kapak_sec_ve_hazirla(paket)
    assert sonuc["arena"] is True
    assert sonuc["secilen"] == "A"
    assert Path(sonuc["kapak"]).exists()
    assert paket["kapak_dosyasi"] == sonuc["kapak"]


def test_json_ayiklayici_duz_metin_icinden_bulur():
    """Arena yanıtı JSON'u düz metin/kod bloğu içinde döndürebilir; kapak
    önerisi ayıklayıcısı bunu bulmalı (canlı koşuda 'JSON ayrıştırılamadı'
    hatası yaşandı — senaryo ayıklayıcısı 'diyaloglar' aradığı için bulamıyordu)."""
    from modules.arena_api import _json_nesnesi_ayikla

    metin = 'Elbette!\n```json\n{"sok_baslik":"SIR ÇIKTI","vurgu_kelime":"SIR","renk":"#FF2D55"}\n```'
    r = _json_nesnesi_ayikla(metin, ("sok_baslik", "vurgu_kelime", "renk"))
    assert r is not None and r["sok_baslik"] == "SIR ÇIKTI"


def test_json_ayiklayici_alakasiz_metinde_none():
    from modules.arena_api import _json_nesnesi_ayikla

    assert _json_nesnesi_ayikla("kapak öneremem", ("sok_baslik",)) is None
