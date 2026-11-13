"""YENİ kapak hattı testleri (2026-11-12 kullanıcı kararı).

Kullanıcı: "Mevcut tüm kuralları çöpe at. Arena'ya videonun tam metnini ver,
metni okusun, Short için profesyonel kapak fotoğrafı oluştursun; oluşturduğu
resmi indir ve videonun ilk karesine yerleştirilip seçilsin."

Eski hat (A/B/C/D adayları, okunabilirlik skoru, sok_baslik/vurgu/renk JSON'u,
1. kareden kapak türetme) SİLİNDİ. Bu testler yeni tek yolu kilitler.
"""
from __future__ import annotations

import sys

import pytest


def _paket() -> dict:
    return {
        "dosya_adi": "test_kapak",
        "baslik": "Ahtapotların Üç Kalbi Var #shorts",
        "senaryo": {
            "baslik": "Ahtapotların Üç Kalbi Var #shorts",
            "kapak_baslik": "ÜÇ KALP, BİRİ DURUYOR",
            "tam_metin": (
                "🧠 Günün Merak Uyandıran Sorusu\nAhtapotların kaç kalbi var?\n\n"
                "🔍 Cevabı Biliyor Muydun?\nAhtapotların üç kalbi vardır ve biri yüzerken durur."
            ),
        },
    }


def test_prompt_video_basligini_tasir():
    """KULLANICI (2026-11-13): istem = "<video başlığı> + sabit cümle".

    Eski "tam metin" ve 7 tasarım kuralı İPTAL edildi (kullanıcı: şablonu çöpe at).
    """
    from modules import kapak_gorsel

    paket = _paket()
    prompt = kapak_gorsel.gorsel_promptu(paket)
    baslik = str(paket.get("baslik") or paket.get("kapak_baslik") or "").strip()
    assert baslik and prompt.startswith(baslik)
    # Eski şema izleri ARTIK YOK
    assert "sok_baslik" not in prompt
    assert "vurgu_kelime" not in prompt
    assert "JSON" not in prompt
    assert "TASARIM KURALLARI" not in prompt


def test_prompt_kullanicinin_cumlesini_icerir():
    """İstem kullanıcının verdiği cümlenin TAMAMINI taşımalı."""
    from modules import kapak_gorsel

    prompt = kapak_gorsel.gorsel_promptu(_paket())
    assert "short video için kapak fotoğrafı istiyorum" in prompt
    assert "etkileşim ve izlenme rekorları kırması" in prompt
    assert "profesyonel şekilde tasarla" in prompt
    assert "merak edip tıklasın" in prompt
def test_kucuk_gorsel_kapak_olarak_kabul_edilmez(tmp_path):
    """Logo/ikon/avatar kapak sanılmasın: minimum 400x400."""
    from PIL import Image

    from modules import kapak_gorsel

    kucuk = tmp_path / "logo.png"
    Image.new("RGB", (64, 64), (255, 0, 0)).save(kucuk)
    assert kapak_gorsel._gorsel_yeterli(kucuk) is False

    buyuk = tmp_path / "kapak.png"
    Image.new("RGB", (900, 1600), (0, 0, 255)).save(buyuk)
    assert kapak_gorsel._gorsel_yeterli(buyuk) is True


def test_kapak_gorseli_1080x1920_kirpilir(tmp_path):
    from PIL import Image

    from modules import kapak_gorsel

    ham = tmp_path / "ham.png"
    Image.new("RGB", (1024, 1024), (10, 20, 30)).save(ham)
    hedef = tmp_path / "kapak.jpg"
    assert kapak_gorsel.gorseli_karesine_oturt(ham, hedef) == hedef
    with Image.open(hedef) as img:
        assert img.size == (1080, 1920)