"""
BOBİ TV — Arena AI Animasyon Üretim Modülü
Arena AI'ya bağlanıp kod tabanlı animasyon ürettirir.
Python + PIL kare kare animasyon → FFmpeg ile .mp4
"""
import os
import json
import subprocess
import tempfile
from pathlib import Path


RENDER_YOLU = Path("bobi_tv/production/render")
ARENA_SCRIPT = Path("arena-ask.mjs")


def arena_animasyon_uret(senaryo_paketi: dict) -> str:
    """
    Arena AI'ya senaryo göndererek animasyon kodu üret.
    Kod çalıştırılır ve video oluşturulur.
    Döner: video dosyası yolu veya None (başarısız olursa)
    """
    if not ARENA_SCRIPT.exists():
        print("[Arena Animasyon] arena-ask.mjs bulunamadı, atlanıyor.")
        return None

    cookies_json = os.environ.get("ARENA_COOKIES_JSON", "")
    if not cookies_json:
        print("[Arena Animasyon] ARENA_COOKIES_JSON yok, atlanıyor.")
        return None

    senaryo = senaryo_paketi["senaryo"]
    dosya_adi = senaryo_paketi["dosya_adi"]
    baslik = senaryo_paketi["baslik"]

    diyaloglar_str = "\n".join(
        f"[{d['karakter']}]: {d['metin']}"
        for d in senaryo.get("diyaloglar", [])
    )

    hook = senaryo.get("hook_metni", "BOBİ TV")
    sure = senaryo.get("toplam_sure", 8.0)

    prompt = (
        f"Python kodu yaz. PIL+ImageDraw ile {int(sure+2)} saniyelik "
        f"1080x1920 animasyon video üret. Hook: '{hook}'. "
        f"Diyaloglar: {diyaloglar_str[:200]}. "
        f"Koyu arka plan, sarı başlık metni, beyaz diyalog metni. "
        f"Çıktı: /tmp/arena_anim_{dosya_adi}.mp4. "
        f"Sadece çalışan Python kodu yaz, markdown yok."
    )

    try:
        import subprocess as sp
        result = sp.run(
            ["node", str(ARENA_SCRIPT), prompt],
            env={**os.environ, "ARENA_COOKIES_JSON": cookies_json},
            capture_output=True,
            text=True,
            timeout=180
        )

        output = result.stdout.strip()
        if not output:
            print("[Arena Animasyon] Boş cevap, atlanıyor.")
            return None

        # Python kodunu çıkar
        kod = _python_kodu_cikar(output)
        if not kod:
            print("[Arena Animasyon] Python kodu bulunamadı.")
            return None

        # Kodu çalıştır
        return _kodu_calistir(kod, dosya_adi)

    except subprocess.TimeoutExpired:
        print("[Arena Animasyon] Timeout.")
        return None
    except Exception as e:
        print(f"[Arena Animasyon] Hata: {e}")
        return None


def _python_kodu_cikar(metin: str) -> str:
    """Arena cevabından Python kodunu çıkar."""
    if "```python" in metin:
        return metin.split("```python")[1].split("```")[0].strip()
    if "```" in metin:
        return metin.split("```")[1].split("```")[0].strip()
    # Kod bloğu yoksa tüm metni dene
    if "import" in metin or "from PIL" in metin or "def " in metin:
        return metin
    return ""


def _kodu_calistir(kod: str, dosya_adi: str) -> str:
    """Python kodunu çalıştır, video dosyasını döndür."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(kod)
        tmp_py = f.name

    beklenen_cikti = f"/tmp/arena_anim_{dosya_adi}.mp4"

    try:
        result = subprocess.run(
            ["python3", tmp_py],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            print(f"[Arena Animasyon] Kod hatası: {result.stderr[:300]}")
            return None

        if Path(beklenen_cikti).exists() and Path(beklenen_cikti).stat().st_size > 1000:
            print(f"[Arena Animasyon] Video üretildi: {beklenen_cikti}")
            return beklenen_cikti

    except subprocess.TimeoutExpired:
        print("[Arena Animasyon] Kod çalıştırma timeout.")
    except Exception as e:
        print(f"[Arena Animasyon] Çalıştırma hatası: {e}")
    finally:
        Path(tmp_py).unlink(missing_ok=True)

    return None


def basit_animasyon_uret(senaryo_paketi: dict) -> str:
    """
    Arena AI olmadan basit PIL animasyon üret.
    Gradient arka plan + hook metni + diyalog metinleri kare kare.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
        import numpy as np
    except ImportError:
        print("[Animasyon] Pillow/numpy yok.")
        return None

    RENDER_YOLU.mkdir(parents=True, exist_ok=True)
    senaryo = senaryo_paketi["senaryo"]
    dosya_adi = senaryo_paketi["dosya_adi"]
    diyaloglar = senaryo.get("diyaloglar", [])
    hook = senaryo.get("hook_metni", "")
    hook_sure = senaryo.get("hook_suresi", 1.0)
    ses_dosyalari = senaryo_paketi.get("ses_dosyalari", [])

    FPS = 30
    W, H = 1080, 1920
    FONT_CANDIDATES = [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    def get_font(size):
        for p in FONT_CANDIDATES:
            if Path(p).exists():
                try:
                    return ImageFont.truetype(p, size)
                except Exception:
                    pass
        return ImageFont.load_default()

    kareler_yolu = RENDER_YOLU / f"{dosya_adi}_kareler"
    kareler_yolu.mkdir(exist_ok=True)

    frame_idx = 0

    def kare_olustur(metin_ana: str, metin_alt: str = "", ilerleme: float = 0.0):
        nonlocal frame_idx
        img = Image.new("RGB", (W, H))
        draw = ImageDraw.Draw(img)

        # Gradient arka plan
        for y in range(H):
            r = int(10 + 20 * (y / H))
            g = int(10 + 10 * (y / H))
            b = int(30 + 30 * (y / H))
            draw.line([(0, y), (W, y)], fill=(r, g, b))

        # Alt progress bar
        if ilerleme > 0:
            bar_w = int(W * ilerleme)
            draw.rectangle([0, H - 8, bar_w, H], fill=(255, 214, 10))

        # Ana metin
        if metin_ana:
            font = get_font(64)
            # Kelime kaydırma
            kelimeler = metin_ana.split()
            satirlar, satir = [], ""
            for k in kelimeler:
                deneme = f"{satir} {k}".strip()
                bb = draw.textbbox((0, 0), deneme, font=font)
                if bb[2] < W - 80:
                    satir = deneme
                else:
                    satirlar.append(satir)
                    satir = k
            if satir:
                satirlar.append(satir)

            toplam_y = len(satirlar) * 80
            y_start = H // 2 - toplam_y // 2
            for satir in satirlar:
                bb = draw.textbbox((0, 0), satir, font=font)
                x = (W - (bb[2] - bb[0])) // 2
                draw.text((x, y_start), satir, fill=(255, 255, 255),
                          font=font, stroke_width=4, stroke_fill=(0, 0, 0))
                y_start += 80

        # Alt etiket metni
        if metin_alt:
            font_kucuk = get_font(36)
            bb = draw.textbbox((0, 0), metin_alt, font=font_kucuk)
            x = (W - (bb[2] - bb[0])) // 2
            draw.text((x, 80), metin_alt, fill=(255, 214, 10),
                      font=font_kucuk, stroke_width=2, stroke_fill=(0, 0, 0))

        # BOBİ TV watermark
        font_wm = get_font(28)
        draw.text((W - 140, 30), "BOBI TV", fill=(255, 255, 255, 60), font=font_wm)

        kare_dosya = kareler_yolu / f"frame_{frame_idx:06d}.png"
        img.save(str(kare_dosya))
        frame_idx += 1
        return kare_dosya

    # Hook kareler
    hook_kareler = int(hook_sure * FPS)
    for i in range(hook_kareler):
        kare_olustur(hook, "BOBİ TV", i / hook_kareler)

    # Diyalog kareler
    toplam_diyalog_sure = sum(d.get("sure", 2.0) for d in diyaloglar)
    gecen = 0.0
    for idx, diyalog in enumerate(diyaloglar):
        metin = diyalog["metin"]
        karakter = diyalog["karakter"]
        diyalog_sure = diyalog.get("sure", 2.0)
        diyalog_kare = int(diyalog_sure * FPS)

        for i in range(diyalog_kare):
            ilerleme = (gecen + (i / FPS)) / toplam_diyalog_sure
            kare_olustur(metin, f"[{karakter}]", ilerleme)

        gecen += diyalog_sure

    # Karelerden video oluştur
    video_dosyasi = str(RENDER_YOLU / f"{dosya_adi}_anim.mp4")
    result = subprocess.run([
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", str(kareler_yolu / "frame_%06d.png"),
        "-c:v", "libx264", "-preset", "fast",
        "-pix_fmt", "yuv420p",
        "-crf", "23",
        video_dosyasi
    ], capture_output=True, timeout=120)

    # Kare dosyalarını temizle
    import shutil
    shutil.rmtree(str(kareler_yolu), ignore_errors=True)

    if result.returncode == 0 and Path(video_dosyasi).exists():
        boyut = Path(video_dosyasi).stat().st_size // 1024
        print(f"[Animasyon] PIL animasyon hazır: {video_dosyasi} ({boyut}KB)")
        return video_dosyasi

    print(f"[Animasyon] FFmpeg hatası: {result.stderr.decode()[:200]}")
    return None
