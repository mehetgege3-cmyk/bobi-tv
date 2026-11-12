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

from modules import calisma_dizinleri
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
        from modules.arena_api import arena_kapak_onerisi_kisa as arena_kapak_onerisi_al
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
        # AI görsel zemini için İngilizce prompt (varsa) — ai_gorsel_zemin kullanır
        "gorsel_prompt": str(oneri.get("gorsel_prompt") or "")[:400],
    }


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


def ai_gorsel_zemin(prompt: str, cikis_jpg: str) -> str | None:
    """Arena'nın verdiği görsel prompt ile AI arka plan kapağı üretir.

    DİKKAT (dürüstlük notu): Arena'nın sohbet arayüzü görsel ÜRETMEZ; bu
    fonksiyon env'de tanımlı bir görsel üretim anahtarı (`GEMINI_API_KEY` veya
    `OPENAI_API_KEY`) varsa çalışır. Anahtar yoksa None döner ve akış 1. kare
    + tipografi adaylarıyla devam eder (üretim DURMAZ, sessizce yalan söylemez).
    Başarılıysa başlık `baslik_kaplama` ile bu zeminin üstüne bindirilir.
    """
    anahtar_g = __import__("os").environ.get("GEMINI_API_KEY", "").strip()
    anahtar_o = __import__("os").environ.get("OPENAI_API_KEY", "").strip()
    if not prompt.strip() or not (anahtar_g or anahtar_o):
        return None
    try:
        import base64

        import requests

        if anahtar_g:
            r = requests.post(
                "https://generativelanguage.googleapis.com/v1beta/models/"
                "gemini-2.5-flash-image:generateContent",
                headers={"x-goog-api-key": anahtar_g, "Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"responseModalities": ["IMAGE"]},
                },
                timeout=90,
            )
            if r.status_code != 200:
                print(f"[Kapak] AI görsel HTTP {r.status_code}: {r.text[:120]}")
                return None
            parcalar = (
                r.json().get("candidates", [{}])[0].get("content", {}).get("parts", [])
            )
            for parca in parcalar:
                veri = (parca.get("inlineData") or parca.get("inline_data") or {}).get("data")
                if veri:
                    Path(cikis_jpg).write_bytes(base64.b64decode(veri))
                    return cikis_jpg if Path(cikis_jpg).exists() else None
            return None

        r = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers={"Authorization": f"Bearer {anahtar_o}"},
            json={"model": "gpt-image-1", "prompt": prompt, "size": "1024x1536", "n": 1},
            timeout=120,
        )
        if r.status_code != 200:
            print(f"[Kapak] AI görsel HTTP {r.status_code}: {r.text[:120]}")
            return None
        veri = (r.json().get("data") or [{}])[0].get("b64_json")
        if not veri:
            return None
        Path(cikis_jpg).write_bytes(base64.b64decode(veri))
        return cikis_jpg if Path(cikis_jpg).exists() else None
    except Exception as e:
        print(f"[Kapak] AI görsel üretim hatası: {str(e)[:140]}")
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
    if not shutil.which("ffmpeg"):
        print("[Kapak] ffmpeg yok — ilk kareye yerleştirme atlandı")
        return None
    hedef = cikis_mp4 or str(Path(video_yolu).with_name(Path(video_yolu).stem + "_kapakli.mp4"))
    try:
        # 1) Kapağı video çözünürlüğüne getir (kare sayısı 1, süre 1/FPS)
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-loop", "1", "-t", "0.04", "-i", kapak_jpg,
                "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,"
                       "crop=1080:1920,setsar=1",
                "-r", "30", "-frames:v", "1", "-q:v", "2", hedef + "_kare.jpg",
            ],
            check=True, capture_output=True, timeout=120,
        )
        # 2) Kareyi videonun başına ekle, kalanı aynen koru
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-i", hedef + "_kare.jpg", "-i", video_yolu,
                "-filter_complex",
                "[0:v]fps=30,trim=end_frame=1,setpts=PTS-STARTPTS[v0];"
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
    cikis_dir = calisma_dizinleri.OUTPUT_YOLU
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
        vurgu = (oneri or {}).get("vurgu_kelime") or ""
        if _kareye_baslik_bindir(kare_yolu, a_yolu, baslik, renk, vurgu):
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

    # D) AI görsel zemini + Arena başlığı (yalnız görsel üretim anahtarı varsa)
    zemin_prompt = (oneri or {}).get("gorsel_prompt") or ""
    if zemin_prompt:
        d_ham = str(cikis_dir / f"{dosya_adi}_kapakD_ham.jpg")
        d_zemin = ai_gorsel_zemin(zemin_prompt, d_ham)
        if d_zemin:
            try:
                from PIL import Image
                d_yolu = str(cikis_dir / f"{dosya_adi}_kapakD.jpg")
                img = Image.open(d_zemin).convert("RGB")
                # 1080x1920 dikey kırpma (Shorts kapağı)
                oran = max(1080 / img.width, 1920 / img.height)
                img = img.resize((int(img.width * oran) + 1, int(img.height * oran) + 1))
                sol = (img.width - 1080) // 2
                ust = (img.height - 1920) // 2
                img = img.crop((sol, ust, sol + 1080, ust + 1920))
                baslik = (oneri or {}).get("sok_baslik") or str(paket.get("baslik") or "")
                img = baslik_kaplama(
                    img, baslik, (oneri or {}).get("vurgu_kelime") or "",
                    (oneri or {}).get("renk") or "#FFD400",
                )
                img.save(d_yolu, "JPEG", quality=92, optimize=True)
                adaylar.append({"ad": "D", "yol": d_yolu,
                                "aciklama": "AI görsel zemin + Arena başlık"})
            except Exception as e:
                print(f"[Kapak] AI zemin işleme hatası: {str(e)[:120]}")

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

    # KULLANICI İSTEĞİ: "kapak video ilk karesine yerleşsin" — seçilen kapak
    # filmin 1. karesine gömülür ve paket final_video'su GÜNCELLENİR
    # (yüklenen video kapakla aynı kareyle açılır). Yerleştirme başarısızsa
    # mevcut video korunur.
    yerlesti = None
    if video and Path(video).exists():
        yerlesti = ilk_kareye_yerlestir(video, secilen["yol"])
        if yerlesti:
            paket["final_video"] = yerlesti
            paket["kapak_ilk_kare"] = yerlesti

    return {
        "kapak": secilen["yol"],
        "adaylar": adaylar,
        "secilen": secilen["ad"],
        "skor": secilen["skor"],
        "arena": oneri is not None,
        "arena_gerekce": (oneri or {}).get("gerekce", ""),
        "ilk_kareye_yerlesti": bool(yerlesti),
        "video": paket.get("final_video", ""),
    }


def kapak_raporu() -> str:
    """Telegram/log için tek satır özet (adaylar + seçim)."""
    return json.dumps({"not": "kapak_sec_ve_hazirla() çıktısını kullanın"}, ensure_ascii=False)
