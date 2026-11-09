"""
BOBİ TV — Yüksek Kontrastlı Kapak (Thumbnail) Üretim Modülü v6.0
- Videonun en çarpıcı Twist karesini seçer (üst kanca kartı zaten videoda yer aldığı için üst üste yazı bindirmez!)
- Alt güvenli bölgeye yüksek kontrastlı 'SONUNU BEKLE!' rozeti ekler ve renk doygunluğunu artırır
"""
import os
import re
import subprocess
import tempfile
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageStat
except ImportError:
    Image = None

W, H = 1080, 1920
YELLOW = (255, 214, 10)
RED = (220, 24, 58)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

FONT_CANDIDATES = [
    "bobi_tv/assets/fonts/Montserrat-ExtraBold.ttf",
    "bobi_tv/assets/fonts/Montserrat-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def pick_font(size: int):
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def extract_candidate_frames(video_path, workdir):
    frames = []
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
            capture_output=True, text=True, timeout=15
        )
        duration = float(result.stdout.strip())
    except Exception:
        duration = 15.0

    # Twist bölgesi (%72-%84) öncelikli aday kareler
    for idx, r in enumerate((0.74, 0.78, 0.82, 0.45)):
        ts = round(duration * r, 2)
        target = workdir / f"frame_{idx}.jpg"
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-ss", str(ts), "-i", str(video_path),
                 "-frames:v", "1", "-q:v", "2", str(target)],
                capture_output=True, timeout=20
            )
            if target.exists() and target.stat().st_size > 1000:
                frames.append(target)
        except Exception:
            pass
    return frames


def pick_best_frame(frames):
    best = None
    for frame in frames:
        try:
            with Image.open(frame) as img:
                small = img.convert("L").resize((64, 114))
                std = ImageStat.Stat(small).stddev[0]
            if best is None or std > best[0]:
                best = (std, frame)
        except Exception:
            continue
    return best[1] if best else None


def kapak_uret(senaryo_paketi: dict) -> str | None:
    if Image is None:
        return None

    final_video = senaryo_paketi.get("final_video")
    if not final_video or not Path(final_video).exists():
        return None

    kapak_dosyasi = str(final_video).replace(".mp4", "_thumb.jpg")

    with tempfile.TemporaryDirectory() as tmp:
        frames = extract_candidate_frames(final_video, Path(tmp))
        best = pick_best_frame(frames)
        if not best:
            return None

        with Image.open(best) as raw:
            base_img = raw.convert("RGB").resize((W, H), Image.LANCZOS)

        base_img = ImageEnhance.Color(base_img).enhance(1.18)
        base_img = ImageEnhance.Contrast(base_img).enhance(1.10)

        draw = ImageDraw.Draw(base_img)
        cta_font = pick_font(48)
        cta_text = "SONUNU BEKLE!"
        bbox = draw.textbbox((0, 0), cta_text, font=cta_font)
        bw = (bbox[2] - bbox[0]) + 72
        bh = (bbox[3] - bbox[1]) + 38
        bx = (W - bw) // 2
        by = H - 320

        draw.rounded_rectangle([bx + 6, by + 8, bx + bw + 6, by + bh + 8], radius=24, fill=(0, 0, 0))
        draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=24, fill=RED, outline=YELLOW, width=5)
        draw.text((bx + 36, by + 15), cta_text, fill=WHITE, font=cta_font)

        base_img.save(kapak_dosyasi, "JPEG", quality=92, optimize=True)
        senaryo_paketi["kapak_dosyasi"] = kapak_dosyasi
        print(f"[Kapak] ✅ Yüksek kontrastlı kapak hazır: {kapak_dosyasi}")
        return kapak_dosyasi
