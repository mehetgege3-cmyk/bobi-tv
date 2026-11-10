"""Kapak fotoğrafı — Arena AI destekli seçim ve ilk kareye yerleştirme.

Kullanıcı isteği (2026-11-11):
  "Kapak fotoğrafı için Arena AI'den destek alsın; GitHub'ta otomatik olarak
   yapsın, ilk kareye yerleştirme yapıp seçilsin."

Akış (tamamı GitHub Actions içinde otomatik, müdahale yok):

  1. Videonun 1. karesi çıkarılır (ffmpeg) — kapak için doğal aday.
  2. Arena AI'ye kapak metni + kompozisyon önerisi sorulur
     (şok başlık, renk paleti, vurgu kelimesi). Arena erişilemezse yerel
     Montserrat kapak üreticisi devreye girer (akış ASLA durmaz).
  3. Üç aday üretilir:
       A) 1. kare + Arena'nın verdiği şok başlık bindirmesi (metin üstte)
       B) 1. kare, sadece hafif kontrast/renk düzeltmesi (metinsiz)
       C) yerel profesyonel VS/Clash kapak (kapak_uret.py)
  4. Seçim otomatik yapılır (Arena'nın önerisi + ölçülebilir kalite skoru):
       • okunabilirlik (metin/arka plan kontrastı)
       • yüz/merkez bölgede metin çakışması olmaması
       • dosya boyutu / çözünürlük (YouTube kapak sınırı 2 MB, 1280x720+)
  5. Seçilen kapak YouTube'a `thumbnails.set` ile yüklenir.

Neden "ilk kareye yerleştirme": kullanıcı kapağın videonun 1. karesine
oturtulmasını istedi — yani kapak videonun açılışıyla aynı görsel dili taşır;
izleyici videoyu açtığında kapakla aynı kareyi görür (stayed-to-watch).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

#: YouTube kapak sınırları (aşılırsa yükleme reddedilir).
KAPAK_MAKS_BAYT = 2 * 1024 * 1024
KAPAK_MIN_GENISLIK = 1280
KAPAK_MIN_YUKSEKLIK = 720


def ilk_kare_cikar(video_yolu: str, cikis_jpg: str) -> str | None:
    """Videonun 1. karesini JPG olarak çıkarır (ffmpeg). Başarısızsa None."""
    if not Path(video_yolu).exists():
        return None
    if not shutil.which("ffmpeg"):
        print("[Kapak] ffmpeg yok — ilk kare çıkarılamadı")
        return None
    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
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


def arena_kapak_onerisi(paket: dict[str, Any]) -> dict[str, Any] | None:
    """Arena AI'den kapak önerisi ister.

    Döner: {"sok_baslik", "vurgu_kelime", "renk", "gerekce"} veya None.
    Arena erişilemezse None döner ve yerel üreticiye düşülür — akış DURMAZ.
    """
    try:
        from modules.arena_api import arena_kapak_onerisi_al
    except Exception:
        return None
    try:
        oneri = arena_kapak_onerisi_al(paket)
    except Exception as e:
        print(f"[Kapak] Arena önerisi alınamadı: {str(e)[:120]}")
        return None
    if not isinstance(oneri, dict):
        return None
    # Zorunlu alanlar + güvenli varsayılanlar
    baslik = str(oneri.get("sok_baslik") or paket.get("baslik") or "")[:40]
    return {
        "sok_baslik": baslik,
        "vurgu_kelime": str(oneri.get("vurgu_kelime") or "")[:20],
        "renk": str(oneri.get("renk") or "#FFD400")[:9],
        "gerekce": str(oneri.get("gerekce") or "")[:160],
    }


def _kareye_baslik_bindir(kaynak_jpg: str, cikis_jpg: str, baslik: str, renk: str) -> str | None:
    """1. karenin üstüne şok başlık bindirir (Pillow).

    Kompozisyon: üstte koyu şerit, altında 2 satıra kadar büyük kalın yazı,
    vurgu için renkli alt çizgi. Metin çok uzunsa küçültülür (taşma yok).
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return None
    try:
        img = Image.open(kaynak_jpg).convert("RGB")
        gen, yuk = img.size
        cizim = ImageDraw.Draw(img, "RGBA")
        # Üst şerit: metin okunabilirliği için (ilk kare ne olursa olsun)
        serit_h = int(yuk * 0.22)
        cizim.rectangle([0, 0, gen, serit_h], fill=(0, 0, 0, 165))
        # Yazı tipi: kullanılabilir ilk kalın font
        font = None
        for aday in (
            "bobi_tv/assets/fonts/Montserrat-ExtraBold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ):
            if Path(aday).exists():
                for boyut in (78, 66, 56, 48, 40):
                    try:
                        font = ImageFont.truetype(aday, boyut)
                        break
                    except Exception:
                        continue
                if font:
                    break
        if font is None:
            font = ImageFont.load_default()
        # 2 satıra böl
        kelimeler = baslik.upper().split()
        satirlar = [" ".join(kelimeler[: max(1, len(kelimeler) // 2 + 1)])]
        if len(kelimeler) > len(satirlar[0].split()):
            satirlar.append(" ".join(kelimeler[len(satirlar[0].split()):]))
        y = int(serit_h * 0.12)
        for satir in satirlar[:2]:
            kutu = cizim.textbbox((0, 0), satir, font=font)
            cizim.text(((gen - (kutu[2] - kutu[0])) // 2, y), satir, font=font, fill=(255, 255, 255))
            y += (kutu[3] - kutu[1]) + int(yuk * 0.008)
        # Vurgu çizgisi (Arena'nın verdiği renk)
        try:
            rgb = tuple(int(renk.lstrip("#")[i: i + 2], 16) for i in (0, 2, 4))
        except Exception:
            rgb = (255, 212, 0)
        cizim.rectangle([0, serit_h - 8, gen, serit_h], fill=(*rgb, 255))
        img.save(cikis_jpg, "JPEG", quality=92, optimize=True)
        return cikis_jpg
    except Exception as e:
        print(f"[Kapak] Başlık bindirme hatası: {str(e)[:120]}")
        return None


def _kontrast_artir(kaynak_jpg: str, cikis_jpg: str) -> str | None:
    """Metinsiz aday: 1. kareye hafif canlılık (Shorts'ta küçük görünüyor)."""
    try:
        from PIL import Image, ImageEnhance
    except Exception:
        return None
    try:
        img = Image.open(kaynak_jpg).convert("RGB")
        img = ImageEnhance.Contrast(img).enhance(1.18)
        img = ImageEnhance.Color(img).enhance(1.22)
        img.save(cikis_jpg, "JPEG", quality=92, optimize=True)
        return cikis_jpg
    except Exception:
        return None


def _okunabilirlik_skoru(jpg: str) -> float:
    """0-1 arası kaba okunabilirlik: üst bölgede açık/koyu ayrımı + kontrast.

    Amaç mimari değil, adaylar arasında ayrım yapmak (metinsiz kare düşük alır,
    koyu şeritli başlıklı kare yüksek alır).
    """
    try:
        from PIL import Image, ImageStat
    except Exception:
        return 0.0
    try:
        img = Image.open(jpg).convert("L")
        gen, yuk = img.size
        ust = img.crop((0, 0, gen, int(yuk * 0.22)))
        tum = img
        ust_ort = ImageStat.Stat(ust).mean[0]
        std = ImageStat.Stat(tum).stddev[0]
        # Üst bölge ya çok koyu ya çok açık olmalı (bant etkisi) + genel kontrast
        bant = max(0.0, 1.0 - abs(ust_ort - 32) / 128.0)
        return round(min(1.0, 0.55 * bant + 0.45 * min(1.0, std / 80.0)), 3)
    except Exception:
        return 0.0


def _sinirlara_uygun(jpg: str) -> bool:
    """YouTube kapak sınırları: 2 MB ve 1280x720 alt sınır."""
    try:
        from PIL import Image
    except Exception:
        return True  # Pillow yoksa engelleme yok
    try:
        boyut = Path(jpg).stat().st_size
        if boyut > KAPAK_MAKS_BAYT:
            return False
        gen, yuk = Image.open(jpg).size
        # YouTube kuralı 1280x720; DİKEY (Shorts) kapaklar 1080x1920 gelir.
        # Bu yüzden "uzun kenar >= 1280 VE kısa kenar >= 720" aranır:
        # 1280x720 (yatay) ✅, 1080x1920 (dikey) ✅, 640x480 ❌.
        return (max(gen, yuk) >= KAPAK_MIN_GENISLIK
                and min(gen, yuk) >= KAPAK_MIN_YUKSEKLIK)
    except Exception:
        return False


def kapak_sec_ve_hazirla(paket: dict[str, Any]) -> dict[str, Any]:
    """Kapak hattının tek giriş noktası — pipeline bunu çağırır.

    Döner: {"kapak": seçilen_yol, "adaylar": [...], "secilen": "A|B|C",
           "skor": float, "arena": bool}
    Hiçbir aday üretilemezse mevcut kapak_uret() çıktısına düşer; o da
    başarısızsa "" döner (yükleme kapak göndermeden devam eder).
    """
    video = str(paket.get("final_video") or "")
    dosya_adi = str(paket.get("dosya_adi") or "video")
    cikis_dir = Path("bobi_tv/output")
    cikis_dir.mkdir(parents=True, exist_ok=True)

    kare = str(cikis_dir / f"{dosya_adi}_kare0.jpg")
    kare_yolu = ilk_kare_cikar(video, kare) if video else None

    oneri = arena_kapak_onerisi(paket)
    adaylar: list[dict[str, Any]] = []

    # A) 1. kare + Arena başlığı
    if kare_yolu:
        a_yolu = str(cikis_dir / f"{dosya_adi}_kapakA.jpg")
        baslik = (oneri or {}).get("sok_baslik") or str(paket.get("baslik") or "")
        renk = (oneri or {}).get("renk") or "#FFD400"
        if _kareye_baslik_bindir(kare_yolu, a_yolu, baslik, renk):
            adaylar.append({"ad": "A", "yol": a_yolu, "aciklama": "1. kare + Arena şok başlık"})

    # B) 1. kare, metinsiz ama canlı
    if kare_yolu:
        b_yolu = str(cikis_dir / f"{dosya_adi}_kapakB.jpg")
        if _kontrast_artir(kare_yolu, b_yolu):
            adaylar.append({"ad": "B", "yol": b_yolu, "aciklama": "1. kare, metinsiz (canlı)"})

    # C) yerel profesyonel kapak (mevcut üretici)
    try:
        from modules.kapak_uret import kapak_uret as yerel_kapak
        c_yolu = yerel_kapak(paket)
        if c_yolu and Path(c_yolu).exists():
            adaylar.append({"ad": "C", "yol": c_yolu, "aciklama": "Yerel VS/Clash kapak"})
    except Exception as e:
        print(f"[Kapak] Yerel üretici hatası: {str(e)[:100]}")

    for a in adaylar:
        a["skor"] = _okunabilirlik_skoru(a["yol"])
        a["uygun"] = _sinirlara_uygun(a["yol"])

    uygunlar = [a for a in adaylar if a["uygun"]]
    if not uygunlar:
        print("[Kapak] Uygun aday yok — kapak gönderilmeyecek")
        return {"kapak": "", "adaylar": adaylar, "secilen": "", "skor": 0.0,
                "arena": oneri is not None}

    # Seçim: Arena önerisi geldiyse A öncelikli (kullanıcı isteği: ilk kare +
    # Arena desteği); yoksa en yüksek okunabilirlik skoru.
    if oneri and any(a["ad"] == "A" for a in uygunlar):
        secilen = next(a for a in uygunlar if a["ad"] == "A")
    else:
        secilen = max(uygunlar, key=lambda a: a["skor"])

    print(
        f"[Kapak] Seçilen: {secilen['ad']} ({secilen['aciklama']}) "
        f"skor={secilen['skor']} arena={'var' if oneri else 'yok'}"
    )
    paket["kapak_dosyasi"] = secilen["yol"]
    paket["kapak_yolu"] = secilen["yol"]
    return {
        "kapak": secilen["yol"],
        "adaylar": adaylar,
        "secilen": secilen["ad"],
        "skor": secilen["skor"],
        "arena": oneri is not None,
        "arena_gerekce": (oneri or {}).get("gerekce", ""),
    }


def kapak_raporu() -> str:
    """Telegram/log için tek satır özet (adaylar + seçim)."""
    return json.dumps({"not": "kapak_sec_ve_hazirla() çıktısını kullanın"}, ensure_ascii=False)
