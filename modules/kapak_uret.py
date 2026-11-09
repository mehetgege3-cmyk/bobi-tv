"""
BOBİ TV — Kapak (Thumbnail) Üretim Modülü
infu projesinden transfer edilen PIL tabanlı kapak üretimi.
Videodan en kontrastli kareyi seçer, başlık + ABONE OL rozeti ekler.
"""
import os
import subprocess
import tempfile
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageStat
except ImportError:
    Image = None

W, H = 1080, 1920
YELLOW = (255, 214, 10)
RED = (214, 18, 28)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def pick_font(size: int):
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if bbox[2] - bbox[0] <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def extract_candidate_frames(video_path, workdir):
    """Videodan 5 aday kare al."""
    frames = []
    try:
        result = subprocess.run([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)
        ], capture_output=True, text=True, timeout=15)
        duration = float(result.stdout.strip())
    except Exception:
        duration = 5.0

    ratios = [0.22, 0.36, 0.5, 0.64, 0.78]
    timestamps = [round(duration * r, 2) for r in ratios]

    for idx, ts in enumerate(timestamps):
        target = workdir / f"frame_{idx}.jpg"
        try:
            subprocess.run([
                "ffmpeg", "-y", "-ss", str(ts), "-i", str(video_path),
                "-frames:v", "1", "-q:v", "3", str(target)
            ], capture_output=True, timeout=30)
            if target.exists() and target.stat().st_size > 500:
                frames.append(target)
        except Exception:
            pass

    return frames


def pick_best_frame(frames):
    """En kontrastli kareyi seç."""
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


def cover_crop(img, width, height):
    """1080x1920'e kırp."""
    src_ratio = img.width / img.height
    dst_ratio = width / height
    if src_ratio > dst_ratio:
        new_h = height
        new_w = int(height * src_ratio)
    else:
        new_w = width
        new_h = int(width / src_ratio)
    img = img.resize((max(new_w, 1), max(new_h, 1)), Image.LANCZOS)
    left = (img.width - width) // 2
    top = (img.height - height) // 2
    return img.crop((left, top, left + width, top + height))


def draw_gradient_overlay(img):
    """Üst karartma + alt siyah band — yazı okunur, konu görünür."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    for y in range(0, 520):
        alpha = int(165 * (1 - y / 520))
        odraw.line([(0, y), (W, y)], fill=(0, 0, 0, alpha))
    for y in range(H - 760, H):
        alpha = int(235 * ((y - (H - 760)) / 760))
        odraw.line([(0, y), (W, y)], fill=(0, 0, 0, alpha))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def kapak_uret(senaryo_paketi: dict) -> str:
    """
    BOBİ TV video kapağı üret.
    1. Videodan en kontrastli kareyi al
    2. Gradient overlay uygula
    3. Sarı başlık + siyah kontur ekle
    4. Kırmızı ABONE OL rozeti ekle
    5. BOBİ TV rozeti ekle
    Döner: kapak dosyası yolu veya None
    """
    if Image is None:
        print("[Kapak] Pillow yok, kapak üretilemedi.")
        return None

    final_video = senaryo_paketi.get("final_video")
    baslik = senaryo_paketi.get("baslik", "BOBİ TV")
    kategori = senaryo_paketi.get("senaryo", {}).get("kategori", "")

    if not final_video or not Path(final_video).exists():
        print("[Kapak] Video yok, metin kartı üretiliyor.")
        return _metin_karti_uret(baslik, kategori, senaryo_paketi)

    kapak_dosyasi = final_video.replace(".mp4", "_thumb.jpg")

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        frames = extract_candidate_frames(final_video, tmpdir)

        if not frames:
            return _metin_karti_uret(baslik, kategori, senaryo_paketi)

        best = pick_best_frame(frames)
        if not best:
            return _metin_karti_uret(baslik, kategori, senaryo_paketi)

        with Image.open(best) as raw:
            base_img = cover_crop(raw.convert("RGB"), W, H)

        # Renk ve kontrast artır
        base_img = ImageEnhance.Color(base_img).enhance(1.12)
        base_img = ImageEnhance.Contrast(base_img).enhance(1.08)

        # Gradient overlay
        base_img = draw_gradient_overlay(base_img)

        # Yazı ekle
        draw = ImageDraw.Draw(base_img)

        # Başlık (sarı, siyah kontur)
        title_text = baslik.replace("#Shorts", "").strip()
        title_font = pick_font(72)
        lines = wrap_text(draw, title_text, title_font, W - 120)

        y = 80
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=title_font, stroke_width=5)
            tw = bbox[2] - bbox[0]
            x = (W - tw) // 2
            draw.text((x, y), line, fill=YELLOW, font=title_font, stroke_width=5, stroke_fill=BLACK)
            y += bbox[3] - bbox[1] + 22

        # ABONE OL rozeti (kırmızı)
        abone_font = pick_font(48)
        abone_text = "ABONE OL"
        bbox = draw.textbbox((0, 0), abone_text, font=abone_font)
        bw = bbox[2] - bbox[0] + 60
        bh = bbox[3] - bbox[1] + 30
        bx = (W - bw) // 2
        by = H - 350
        draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=15, fill=RED)
        draw.text((bx + 30, by + 15), abone_text, fill=WHITE, font=abone_font)

        # BOBİ TV rozeti (üst sağ)
        bobi_font = pick_font(36)
        bobi_text = "BOBİ TV"
        bbox = draw.textbbox((0, 0), bobi_text, font=bobi_font)
        bw2 = bbox[2] - bbox[0] + 30
        bh2 = bbox[3] - bbox[1] + 20
        draw.rounded_rectangle([W - bw2 - 30, 30, W - 30, 30 + bh2], radius=10, fill=(10, 10, 30))
        draw.text((W - bw2 - 15, 35), bobi_text, fill=YELLOW, font=bobi_font)

        # Kaydet
        base_img.save(kapak_dosyasi, "JPEG", quality=92)
        print(f"[Kapak] Kapak üretildi: {kapak_dosyasi}")
        return kapak_dosyasi


def _metin_karti_uret(baslik: str, kategori: str, senaryo_paketi: dict) -> str:
    """Video karesi yoksa metin kartı üret (gradient zemin)."""
    if Image is None:
        return None

    final_video = senaryo_paketi.get("final_video", "output")
    kapak_dosyasi = final_video.replace(".mp4", "_thumb.jpg")

    img = Image.new("RGB", (W, H), (8, 12, 25))
    draw = ImageDraw.Draw(img)

    # Gradient zemin
    for y in range(H):
        ratio = y / H
        draw.line([(0, y), (W, y)], fill=(
            int(8 + 18 * ratio),
            int(12 + 16 * ratio),
            int(25 + 22 * ratio)
        ))

    # Başlık
    title_text = baslik.replace("#Shorts", "").strip()
    title_font = pick_font(72)
    lines = wrap_text(draw, title_text, title_font, W - 120)
    y = H // 2 - 100
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=title_font, stroke_width=5)
        tw = bbox[2] - bbox[0]
        x = (W - tw) // 2
        draw.text((x, y), line, fill=YELLOW, font=title_font, stroke_width=5, stroke_fill=BLACK)
        y += bbox[3] - bbox[1] + 22

    # ABONE OL
    abone_font = pick_font(48)
    abone_text = "ABONE OL"
    bbox = draw.textbbox((0, 0), abone_text, font=abone_font)
    bw = bbox[2] - bbox[0] + 60
    bh = bbox[3] - bbox[1] + 30
    bx = (W - bw) // 2
    by = H - 350
    draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=15, fill=RED)
    draw.text((bx + 30, by + 15), abone_text, fill=WHITE, font=abone_font)

    img.save(kapak_dosyasi, "JPEG", quality=92)
    print(f"[Kapak] Metin kartı üretildi: {kapak_dosyasi}")
    return kapak_dosyasi


if __name__ == "__main__":
    print("kapak_uret.py yüklendi.")
