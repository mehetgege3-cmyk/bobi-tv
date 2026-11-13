"""Kapak MEKANİĞİ — yalnız mekanik yardımcılar (2026-11-12 sadeleştirme).

Kapak KARARI ve ÜRETİMİ burada DEĞİL:
    modules/kapak_gorsel.py → Arena'ya videonun TAM metni gider, görsel üretir
    modules/kapak_hatti.py  → görseli indirir, 1. kareye yerleştirir

Burada kalanlar (mekanik):
    1) ilk_kare_cikar          → videodan 1. kare (ffmpeg)
    2) baslik_kaplama / _kareye_baslik_bindir → bir görselin üstüne başlık
       (yalnız Arena görseli gelmediğinde kullanılan yedek yol)
    3) ilk_kareye_yerlestir    → kapağı videonun 1. karesine koyar

SİLİNENLER (kullanıcı: "mevcut tüm kuralları çöpe at"): Arena şok başlık JSON
şeması (sok_baslik/vurgu_kelime/renk), A/B/C/D aday yarışı, okunabilirlik
skoru, sınır testleri, AI zemin (GEMINI/OPENAI) kapısı, kapak_raporu.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from modules import calisma_dizinleri

def _video_boyutu(ff: str, video_yolu: str) -> tuple[int, int]:
    """Videonun genişlik/yüksekliğini okur. Okunamazsa 1080×1920 varsayar."""
    try:
        r = subprocess.run([ff, "-i", video_yolu], capture_output=True, text=True, timeout=60)
        import re as _re

        m = _re.search(r"Video:.*?,\s*(\d{2,5})x(\d{2,5})", r.stderr)
        if m:
            return int(m.group(1)), int(m.group(2))
    except Exception:
        pass
    return 1080, 1920


def ffmpeg_yolu() -> str | None:
    """ffmpeg çalıştırılabilirini bulur.

    KOŞU 43323078600: `shutil.which("ffmpeg")` boş döndüğü için kapak 1. kareye
    YERLEŞTİRİLEMEDİ (zincirin son adımı). Ama `imageio-ffmpeg` paketi kendi
    binary'sini getiriyor; onu da kabul et.
    """
    yol = shutil.which("ffmpeg")
    if yol:
        return yol
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def ilk_kare_cikar(video_yolu: str, cikis_jpg: str) -> str | None:
    """Videonun 1. karesini JPG olarak çıkarır (ffmpeg). Başarısızsa None."""
    if not Path(video_yolu).exists():
        return None
    _ff = ffmpeg_yolu()
    if not _ff:
        print("[Kapak] ffmpeg yok — ilk kare çıkarılamadı")
        return None
    try:
        subprocess.run(
            [
                _ff, "-y", "-loglevel", "error",
                "-i", video_yolu,
                "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
                "-frames:v", "1", "-q:v", "2", cikis_jpg,
            ],
            check=True, capture_output=True, timeout=120,
        )
        return cikis_jpg if Path(cikis_jpg).exists() else None
    except Exception as e:
        print(f"[Kapak] İlk kare çıkarma hatası: {str(e)[:120]}")
        return None



def _font(boyut: int):
    """Montserrat-ExtraBold → DejaVuSans-Bold → varsayılan; ilk bulunanı verir."""
    from PIL import ImageFont

    for aday in (
        "bobi_tv/assets/fonts/Montserrat-ExtraBold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ):
        if Path(aday).exists():
            try:
                return ImageFont.truetype(aday, boyut)
            except Exception:
                continue
    return ImageFont.load_default()



def baslik_kaplama(
    img,
    baslik: str,
    vurgu_kelime: str = "",
    renk: str = "#FFD400",
    serit_orani: float = 0.26,
):
    """Kapağın üstüne şok başlık bandı bindirir (yalnız Pillow).

    İyileştirmeler (2026-11-11):
      • YÜZ GÜVENLİ BÖLGE: ilk karenin kendi altyazıları/karakter yüzü üstte
        değilse bant üste; değilse alt şeride taşınabilir (serit_orani ile).
      • VURGU KELİMESİ: Arena'nın seçtiği kelime renkli boyanır (dikkat
        çekiciliği artırır, tüm başlığı renklendirmekten daha okunur).
      • Satır bölme: 4 kelimeye kadar tek satır, sonrası iki satır.
    """
    from PIL import ImageDraw

    gen, yuk = img.size
    cizim = ImageDraw.Draw(img, "RGBA")
    serit_h = int(yuk * serit_orani)
    cizim.rectangle([0, 0, gen, serit_h], fill=(8, 10, 22, 238))

    # Vurgu rengi (Arena'dan) — geçersizse marka sarısı
    try:
        rgb = tuple(int(renk.lstrip("#")[i: i + 2], 16) for i in (0, 2, 4))
    except Exception:
        rgb = (255, 212, 0)

    metin = str(baslik or "").strip().upper()
    kelimeler = metin.split()
    if not kelimeler:
        return img
    # 4 kelimeye kadar tek satır, üstü iki satıra bölünür
    if len(kelimeler) <= 4:
        satirlar = [" ".join(kelimeler)]
    else:
        orta = max(1, len(kelimeler) // 2 + 1)
        satirlar = [" ".join(kelimeler[:orta]), " ".join(kelimeler[orta:])]

    en_uzun = max(len(s) for s in satirlar)
    boyut = 80 if en_uzun <= 12 else 68 if en_uzun <= 16 else 56 if en_uzun <= 22 else 44
    font = _font(boyut)
    kutu_y = cizim.textbbox((0, 0), satirlar[0], font=font)
    satir_yuk = (kutu_y[3] - kutu_y[1]) + int(yuk * 0.012)
    y = max(6, (serit_h - satir_yuk * len(satirlar)) // 2 - int(yuk * 0.004))

    for satir in satirlar[:2]:
        kutu = cizim.textbbox((0, 0), satir, font=font)
        x = (gen - (kutu[2] - kutu[0])) // 2
        # Kelime kelime çiz: vurgu kelimesi renkli, kalanı beyaz
        imlec = x
        for kelime in satir.split():
            parca = kelime + " "
            vurgu_mu = bool(vurgu_kelime) and (
                kelime.strip(".,!?:;").lower() == vurgu_kelime.strip().lower()
            )
            cizim.text(
                (imlec, y), parca, font=font,
                fill=(*rgb, 255) if vurgu_mu else (255, 255, 255, 255),
            )
            imlec += cizim.textlength(parca, font=font)
        y += satir_yuk

    # Şerit altına yumuşak karartma geçişi (bandın keskin bitmemesi için)
    gecis_h = int(yuk * 0.06)
    for adim in range(gecis_h):
        oran = 1 - (adim / max(1, gecis_h))
        cizim.line(
            [(0, serit_h + adim), (gen, serit_h + adim)],
            fill=(8, 10, 22, int(190 * oran)),
        )
    # Vurgu çizgisi (Arena'nın verdiği renk)
    cizim.rectangle([0, serit_h - 8, gen, serit_h], fill=(*rgb, 255))
    return img



def _kareye_baslik_bindir(
    kaynak_jpg: str,
    cikis_jpg: str,
    baslik: str,
    renk: str,
    vurgu_kelime: str = "",
) -> str | None:
    """1. karenin üstüne şok başlık bindirir (Pillow) — `baslik_kaplama` sarmalayıcısı."""
    try:
        from PIL import Image
    except Exception:
        return None
    try:
        img = Image.open(kaynak_jpg).convert("RGB")
        img = baslik_kaplama(img, baslik, vurgu_kelime, renk)
        img.save(cikis_jpg, "JPEG", quality=92, optimize=True)
        return cikis_jpg
    except Exception as e:
        print(f"[Kapak] Başlık bindirme hatası: {str(e)[:120]}")
        return None



def ilk_kareye_yerlestir(video_yolu: str, kapak_jpg: str, cikis_mp4: str | None = None) -> str | None:
    """Kapak görselini videonun 1. karesine yerleştirir (kullanıcı isteği).

    Neden: "kapak video ilk karesine yerleşsin" → videoyu açan izleyici,
    kapakta gördüğü kareyle AYNI kareyi görür; kopukluk olmaz, ilk saniye
    kaybı azalır (stayed-to-watch).

    kapak_jpg 1080x1920'e ölçeklenir, videonun ilk karesiyle değiştirilir ve
    ses akışı KOPYALANIR (`-c:a copy`) — yeniden encode yok, kalite kaybı yok.
    Başarısızsa None döner ve akış normal videoyla devam eder.
    """
    if not (Path(video_yolu).exists() and Path(kapak_jpg).exists()):
        return None
    _ff = ffmpeg_yolu()
    if not _ff:
        print("[Kapak] ffmpeg yok — ilk kareye yerleştirme atlandı")
        return None
    hedef = cikis_mp4 or str(Path(video_yolu).with_name(Path(video_yolu).stem + "_kapakli.mp4"))

    # KÖK NEDEN (koşu 43323078600 / yerel ölçüm): kapak 1080×1920'e ölçekleniyordu
    # ama video 720×1280 ise concat "parameters do not match" ile PATLIYOR
    # (rc=234, çıktı 0 bayt). Kapak HER ZAMAN videonun kendi çözünürlüğüne
    # ölçeklenmeli. Ölçüyü ffprobe yerine ffmpeg -i çıktısından okuyoruz.
    gen, yuk = _video_boyutu(_ff, video_yolu)
    try:
        # 1) Kapağı video çözünürlüğüne getir (kare sayısı 1, süre 1/FPS)
        subprocess.run(
            [
                _ff, "-y", "-loglevel", "error",
                # SÜRE KUSURU (2026-11-13, yt-dlp kanıtı): kapak 1 kare = 33 ms
                # görünüyordu (ffprobe: kare0=0.000s, kare1=0.033s) → göz
                # yakalayamaz. KULLANICI KARARI: 1.5 saniye.
                "-loop", "1", "-t", "1.5", "-i", kapak_jpg,
                "-vf", f"scale={gen}:{yuk}:force_original_aspect_ratio=increase,"
                       f"crop={gen}:{yuk},setsar=1",
                "-r", "30", "-frames:v", "1", "-q:v", "2", hedef + "_kare.jpg",
            ],
            check=True, capture_output=True, timeout=120,
        )
        # 2) Kareyi videonun başına ekle, kalanı aynen koru
        subprocess.run(
            [
                _ff, "-y", "-loglevel", "error",
                "-i", hedef + "_kare.jpg", "-i", video_yolu,
                "-filter_complex",
                # 45 kare @ 30fps = 1.5 sn kapak süresi
                "[0:v]fps=30,trim=end_frame=45,setpts=PTS-STARTPTS[v0];"
                "[1:v]setpts=PTS-STARTPTS[v1];"
                "[v0][v1]concat=n=2:v=1:a=0[v]",
                "-map", "[v]", "-map", "1:a?",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-c:a", "copy", "-movflags", "+faststart", hedef,
            ],
            check=True, capture_output=True, timeout=600,
        )
        Path(hedef + "_kare.jpg").unlink(missing_ok=True)
        if Path(hedef).exists() and Path(hedef).stat().st_size > 10_000:
            print(f"[Kapak] Kapak videonun 1. karesine yerleştirildi: {hedef}")
            return hedef
    except Exception as e:
        print(f"[Kapak] İlk kareye yerleştirme hatası: {str(e)[:140]}")
        Path(hedef + "_kare.jpg").unlink(missing_ok=True)
    return None


def baslik_kaplama_jpg(
    kaynak_jpg: str, cikis_jpg: str, baslik: str, renk: str = "#FFD400"
) -> str | None:
    """Kare/görsel üstüne başlık bindirir (yalnız YEDEK yol; Arena görseli esas).

    Arena kapak GÖRSELİ üretirse bu fonksiyon hiç çağrılmaz — görselin içine
    yazı koymak yasak (bkz. kapak_gorsel.gorsel_promptu).
    """
    try:
        from PIL import Image

        img = Image.open(kaynak_jpg).convert("RGB")
        img = baslik_kaplama(img, baslik, "", renk)
        img.save(cikis_jpg, "JPEG", quality=92, optimize=True)
        return cikis_jpg if Path(cikis_jpg).exists() else None
    except Exception as e:
        print(f"[Kapak] Başlık bindirme hatası: {str(e)[:120]}")
        return None
