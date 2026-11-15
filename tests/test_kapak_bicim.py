"""Kapak biçimlendirme testleri — regresyonu bir daha yaşamamak için.

NİÇİN (2026-11-08): `kapak_olcekle()` 8f7398a commit'inde "cover" kırpmasına
çevrildi. 1:1 Gemini kapağı 9:16 tuvale oturtulurken metnin %44'ü kesildi —
kanalda "İNİZ", "DİNİ NASIL YİY" göründü. Bu testler o hatanın geri
dönmesini engeller.

ÜÇ KURAL:
  1. 9:16 sürüm metni KIRPMAZ (contain) — kenarlar bulanık dolgu olabilir.
  2. 16:9 sürüm metni KIRPMAZ — YouTube kapak alanı, ortada net görsel.
  3. Hiçbir sürüm 2 MB'ı geçmez (YouTube thumbnails.set sınırı).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.yeni_motor.motor import kapak_olcekle, kapak_youtube_surumu  # noqa: E402

BOYUTLAR = [(1024, 1024), (768, 1376), (1376, 768), (1080, 1920)]


def _kaynak(tmp_path: Path, w: int, h: int) -> str:
    """Köşeleri farklı renkli, ortasında metin benzeri şerit olan test görseli."""
    img = Image.new("RGB", (w, h), (30, 40, 60))
    # dört köşeye işaret koy — kırpma olursa kaybolur
    for (x, y), renk in {
        (0, 0): (255, 0, 0), (w - 20, 0): (0, 255, 0),
        (0, h - 20): (0, 0, 255), (w - 20, h - 20): (255, 255, 0),
    }.items():
        img.paste(Image.new("RGB", (20, 20), renk), (x, y))
    yol = tmp_path / f"kaynak_{w}x{h}.jpg"
    img.save(yol, quality=95)
    return str(yol)


@pytest.mark.parametrize("w,h", BOYUTLAR)
def test_dikey_kapak_metni_kirpmaz(tmp_path, w, h):
    """9:16 sürüm: köşe işaretleri KORUNMALI (contain, kırpma yok)."""
    kaynak = _kaynak(tmp_path, w, h)
    hedef = str(tmp_path / "dikey.jpg")
    kapak_olcekle(kaynak, hedef)

    im = Image.open(hedef)
    assert im.size == (1080, 1920), "dikey sürüm 1080x1920 olmalı"

    # Görselin ölçeklenmiş hâli tuvalin ortasında; köşe işaretleri
    # tuvalin içinde bir yerde olmalı (kırpılsaydı hiç olmazdı).
    px = im.convert("RGB").load()
    kirmizi = sum(
        1 for x in range(0, 1080, 3) for y in range(0, 1920, 3)
        if px[x, y][0] > 180 and px[x, y][1] < 90 and px[x, y][2] < 90
    )
    assert kirmizi > 0, f"sol üst işaret kayboldu → kırpma var ({w}x{h})"


@pytest.mark.parametrize("w,h", BOYUTLAR)
def test_youtube_kapak_16_9_ve_kirpmasiz(tmp_path, w, h):
    kaynak = _kaynak(tmp_path, w, h)
    hedef = str(tmp_path / "yt.jpg")
    kapak_youtube_surumu(kaynak, hedef)

    im = Image.open(hedef)
    assert im.size == (1280, 720), "YouTube kapağı 1280x720 olmalı"

    px = im.convert("RGB").load()
    kirmizi = sum(
        1 for x in range(0, 1280, 2) for y in range(0, 720, 2)
        if px[x, y][0] > 180 and px[x, y][1] < 90 and px[x, y][2] < 90
    )
    assert kirmizi > 0, "köşe işareti kayboldu → kırpma var"


@pytest.mark.parametrize("w,h", BOYUTLAR)
def test_kapak_2mb_altinda(tmp_path, w, h):
    kaynak = _kaynak(tmp_path, w, h)
    for fn, ad in ((kapak_olcekle, "dikey"), (kapak_youtube_surumu, "yt")):
        hedef = str(tmp_path / f"{ad}.jpg")
        fn(kaynak, hedef)
        assert Path(hedef).stat().st_size <= 2 * 1024 * 1024, \
            f"{ad} sürüm 2 MB sınırını aştı"


def test_kare_kapak_dikey_tuvale_sigar(tmp_path):
    """1:1 kapak 9:16 tuvale otururken ÜST/ALT bulanık dolgu olmalı.

    Ölçüm: tuvalin en üst 60 px'i ile ortasındaki 60 px'in ortalama
    parlaklığı farklı olmalı (dolgu vs görsel). Kırpma olsaydı üst şerit
    de görselin parçası olurdu.
    """
    kaynak = _kaynak(tmp_path, 1024, 1024)
    hedef = str(tmp_path / "dikey.jpg")
    kapak_olcekle(kaynak, hedef)

    im = Image.open(hedef).convert("L")
    ust = im.crop((0, 0, 1080, 60))
    orta = im.crop((0, 930, 1080, 990))
    fark = abs(
        sum(ust.getdata()) / (1080 * 60) - sum(orta.getdata()) / (1080 * 60)
    )
    assert fark > 1.0, "dolgu şeridi yok gibi — görsel tuvale kırpılmış olabilir"
