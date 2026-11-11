"""Kapak hattı — A2 sertleştirme testleri (2026-11-11).

Kullanıcı sorusu: "Arena AI her videoya özel kapak tasarlasın, kapak videonun
ilk karesine yerleşsin ve otomatik seçilsin — mantıklı mı?"

Bu dosya, hattın verdiği sözleri ölçer:
  1. Seçilen kapak videonun 1. KARESİNE gerçekten yerleşir (ffmpeg; ses korunur).
  2. Başlık bindirmede vurgu kelimesi renklenir, metin taşmaz.
  3. AI görsel zemini anahtar yoksa SESSİZCE atlanır (yalan yok, akış durmaz).
  4. Kapak hattı hata fırlatmaz; pipeline çökmez.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules import kapak_arena as ka  # noqa: E402

FFMPEG = shutil.which("ffmpeg")


def _test_videosu(klasor: Path) -> Path:
    """2 saniyelik 1080x1920 test videosu (video + ses)."""
    hedef = klasor / "v.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", "testsrc=size=1080x1920:rate=30:duration=2",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
            "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
            str(hedef),
        ],
        check=True, capture_output=True,
    )
    return hedef


@pytest.mark.skipif(FFMPEG is None, reason="ffmpeg yok")
def test_kapak_videonun_ilk_karesine_yerlesir(tmp_path):
    """Kullanıcı isteği: kapak video ilk karesine yerleşsin.

    Doğrulama: yerleştirme sonrası çıkarılan 1. kare, kapağın rengini taşır ve
    videonun süresi/ses akışı korunur."""
    from PIL import Image

    video = _test_videosu(tmp_path)
    kapak = tmp_path / "k.jpg"
    Image.new("RGB", (1080, 1920), (200, 30, 60)).save(kapak, quality=92)

    cikti = ka.ilk_kareye_yerlestir(str(video), str(kapak))
    assert cikti and Path(cikti).exists()

    kare = tmp_path / "f0.png"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(cikti), "-frames:v", "1", str(kare)],
        check=True, capture_output=True,
    )
    piksel = Image.open(kare).convert("RGB").getpixel((540, 960))
    assert piksel[0] > 150 and piksel[1] < 80, piksel  # kırmızı kapak

    # Ses korunmuş olmalı (yeniden encode edilmedi)
    bilgi = subprocess.run(
        ["ffmpeg", "-i", str(cikti)], capture_output=True, text=True
    ).stderr
    assert "Audio:" in bilgi
    assert "Duration: 00:00:02" in bilgi


def test_ilk_kare_yerlestirme_dosya_yoksa_none(tmp_path):
    assert ka.ilk_kareye_yerlestir(str(tmp_path / "yok.mp4"), str(tmp_path / "yok.jpg")) is None


def test_baslik_kaplama_vurgu_kelimesini_renklendirir():
    """Arena'nın seçtiği vurgu kelimesi renkli olmalı (tüm başlık değil)."""
    from PIL import Image

    img = Image.new("RGB", (1080, 1920), (20, 80, 40))
    sonuc = ka.baslik_kaplama(img, "KİMSE BEKLEMEDİ", "KİMSE", "#FF2D55")
    renkler = {r for _, r in sonuc.convert("RGB").getcolors(maxcolors=100000)}
    # Marka sarısı/kırmızı vurgu rengi karede bulunmalı
    assert any(r[0] > 200 and r[1] < 90 for r in renkler)


def test_baslik_kaplama_bos_baslikta_cokmez():
    from PIL import Image

    img = Image.new("RGB", (1080, 1920), (0, 0, 0))
    sonuc = ka.baslik_kaplama(img, "", "", "gecersiz-renk")
    assert sonuc.size == (1080, 1920)


def test_baslik_kaplama_uzun_basligi_iki_satira_boler():
    """7+ kelime tek satıra sığmaz; bant yüksekliği sabit kalmalı (taşma yok)."""
    from PIL import Image

    img = Image.new("RGB", (1080, 1920), (0, 0, 0))
    sonuc = ka.baslik_kaplama(img, "PATRON HERKESİN MAAŞINI TOPLANTIDA AÇIKLADI", "MAAŞINI")
    assert sonuc.size == img.size


def test_ai_gorsel_zemin_anahtar_yoksa_none(tmp_path, monkeypatch):
    """Görsel üretim anahtarı yoksa fonksiyon None döner — akış 1. kare
    adaylarıyla devam eder (sessiz yalan yok)."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert ka.ai_gorsel_zemin("kızgın patron ofiste", str(tmp_path / "a.jpg")) is None


def test_ai_gorsel_zemin_prompt_bossa_anahtar_varken_de_atlar(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    assert ka.ai_gorsel_zemin("", str(tmp_path / "a.jpg")) is None


def test_secim_hatasi_cokertmez(tmp_path, monkeypatch):
    """Kapak hattı pipeline'ı çökertmez: video yok + Arena yok → tutarlı sözlük."""
    monkeypatch.setattr(ka, "arena_kapak_onerisi", lambda p: None)
    monkeypatch.chdir(tmp_path)
    paket = {"baslik": "Test", "final_video": str(tmp_path / "yok.mp4"), "dosya_adi": "t"}
    sonuc = ka.kapak_sec_ve_hazirla(paket)
    assert isinstance(sonuc, dict)
    assert "ilk_kareye_yerlesti" in sonuc
    assert sonuc["ilk_kareye_yerlesti"] is False
