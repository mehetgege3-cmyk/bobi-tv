"""
BOBİ TV — Video Kurgu ve Render Modülü v3.0
Sinematik FFmpeg zinciri + ASS altyazı (pop animasyonu) + hook + karakter etiketleri.
Dikey 9:16 Shorts, tek geçişli encode, bellek dostu.
infu projesinden transfer edilen teknikler:
- ASS altyazı (Montserrat-Bold, sarı, pop animasyonu, MarginV=250)
- Sinematik FFmpeg: unsharp, eq, zoompan
- edge-tts WordBoundary zaman damgalarıyla altyazı senkronu
"""
import os
import json
import subprocess
import shutil
from pathlib import Path


RENDER_YOLU = Path("bobi_tv/production/render")
OUTPUT_YOLU = Path("bobi_tv/output")

VIDEO_GENISLIK = 1080
VIDEO_YUKSEKLIK = 1920
VIDEO_FPS = 30
VIDEO_BITRATE = "6M"
AUDIO_BITRATE = "192k"

# BOBİ TV renk paleti
RENK_BG_BASLANGIC = "0x0a0a1e"
RENK_BG_BITIS = "0x2a1a4e"


def ffmpeg_kurulu_mu() -> bool:
    result = subprocess.run(["which", "ffmpeg"], capture_output=True)
    return result.returncode == 0


def ses_birlestir(ses_dosyalari: list, cikis_dosyasi: str) -> float:
    """Ses dosyalarını gap olmadan birleştir."""
    if not ses_dosyalari:
        return 0.0
    if len(ses_dosyalari) == 1:
        shutil.copy(ses_dosyalari[0], cikis_dosyasi)
        return _ses_suresi(ses_dosyalari[0])

    liste_dosyasi = cikis_dosyasi + ".txt"
    with open(liste_dosyasi, "w") as f:
        for s in ses_dosyalari:
            f.write(f"file '{os.path.abspath(s)}'\n")

    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", liste_dosyasi, "-ar", "44100", "-ac", "1",
        cikis_dosyasi
    ], capture_output=True, check=True, timeout=120)

    os.remove(liste_dosyasi)
    return _ses_suresi(cikis_dosyasi)


def _ses_suresi(ses_dosyasi: str) -> float:
    try:
        result = subprocess.run([
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", ses_dosyasi
        ], capture_output=True, timeout=15)
        return float(json.loads(result.stdout)["format"]["duration"])
    except Exception:
        return 3.0


def arkaplan_uret(sure: float, cikis: str, efekt: str = None):
    """Gradient + hareketli arka plan üret (sinematik zoompan)."""
    renk1 = RENK_BG_BASLANGIC
    renk2 = RENK_BG_BITIS

    if efekt == "siyah_beyaz_zoom":
        renk1 = "0x050508"
        renk2 = "0x1a1a2e"

    gradient = (
        f"gradients=s={VIDEO_GENISLIK}x{VIDEO_YUKSEKLIK}:d={sure}:"
        f"c0={renk1}:c1={renk2}:c2={renk1}:"
        f"x0=0:y0=0:x1={VIDEO_GENISLIK}:y1={VIDEO_YUKSEKLIK}:speed=0.008"
    )

    try:
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", gradient,
            "-t", str(sure), "-r", str(VIDEO_FPS),
            "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
            cikis
        ], capture_output=True, check=True, timeout=120)
        print(f"[Render] Gradient arka plan: {sure:.1f}sn")
    except Exception:
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"color=c={renk1}:size={VIDEO_GENISLIK}x{VIDEO_YUKSEKLIK}:rate={VIDEO_FPS}",
            "-t", str(sure), "-c:v", "libx264", "-preset", "fast", cikis
        ], capture_output=True, check=True, timeout=120)


def ass_altyazi_olustur(ses_dosyalari: list, diyaloglar: list, cikis_ass: str, hook_suresi: float = 1.0):
    """
    edge-tts WordBoundary zaman damgalarından ASS altyazı üret.
    Pop animasyonu, sarı renk, MarginV=250 (YouTube mobil buton altı).
    Karakter isimleri altyazıda yer almaz.
    """
    satirlar = []
    zaman_oteleme = hook_suresi  # Hook süresi kadar gecikme
    sira = 0

    for i, ses in enumerate(ses_dosyalari):
        zamanlamalar = ses.get("zamanlamalar", [])
        metin = ses.get("metin", "")
        sure = ses.get("sure", 2.0)

        if not zamanlamalar:
            bas = zaman_oteleme
            bit = zaman_oteleme + sure
            satirlar.append({"bas": bas, "bit": bit, "metin": metin})
            zaman_oteleme += sure
            continue

        # 2-3 kelimelik dinamik bloklar
        grup_boyutu = 3
        for j in range(0, len(zamanlamalar), grup_boyutu):
            grup = zamanlamalar[j:j + grup_boyutu]
            bas = zaman_oteleme + grup[0]["baslangic"]
            bit = zaman_oteleme + grup[-1]["bitis"]
            metin_grup = " ".join(k["kelime"] for k in grup)
            satirlar.append({"bas": bas, "bit": bit, "metin": metin_grup})

        zaman_oteleme += sure

    # ASS formatında yaz
    def saniye_ass(sn: float) -> str:
        h = int(sn // 3600)
        m = int((sn % 3600) // 60)
        s = int(sn % 60)
        cs = int((sn % 1) * 100)
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    ass_header = """[Script Info]
Title: BOBİ TV
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Montserrat-Bold,58,&H0000FFFF,&H0000FFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,5,3,2,60,60,250,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    with open(cikis_ass, "w", encoding="utf-8") as f:
        f.write(ass_header)
        for satir in satirlar:
            bas = saniye_ass(satir["bas"])
            bit = saniye_ass(satir["bit"])
            # Pop animasyonu: 88%'den 100%'e büyüme (85ms)
            metin = "{\\fscx88\\fscy88\\t(0,85,\\fscx100\\fscy100)}" + satir["metin"].replace("\n", " ")
            f.write(f"Dialogue: 0,{bas},{bit},Default,,0,0,0,,{metin}\n")

    return cikis_ass


def video_render(senaryo_paketi: dict) -> str:
    """
    Senaryo paketinden tam Shorts videosu üretir.
    Hook → diyaloglar → punchline efekt → loop
    Sinematik FFmpeg zinciri + ASS altyazı + karakter etiketleri + watermark
    """
    RENDER_YOLU.mkdir(parents=True, exist_ok=True)
    OUTPUT_YOLU.mkdir(parents=True, exist_ok=True)

    dosya_adi = senaryo_paketi["dosya_adi"]
    senaryo = senaryo_paketi["senaryo"]
    ses_dosyalari = senaryo_paketi.get("ses_dosyalari", [])
    diyaloglar = senaryo.get("diyaloglar", [])
    hook_metni = senaryo.get("hook_metni", "")
    hook_suresi = senaryo.get("hook_suresi", 1.0)
    punchline_efekt = senaryo.get("punchline_efekt", "zoom_in")

    if not ffmpeg_kurulu_mu():
        raise RuntimeError("FFmpeg kurulu değil.")

    # 1. Sesleri birleştir (gap yok)
    birlesik_ses = str(RENDER_YOLU / f"{dosya_adi}_audio.wav")
    ses_yollari = [s["ses_dosyasi"] for s in ses_dosyalari if Path(s["ses_dosyasi"]).exists()]

    if ses_yollari:
        diyalog_suresi = ses_birlestir(ses_yollari, birlesik_ses)
    else:
        diyalog_suresi = 5.0
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
            "-t", str(diyalog_suresi), birlesik_ses
        ], capture_output=True, timeout=30)

    video_suresi = hook_suresi + diyalog_suresi

    # 2. Arka plan
    arkaplan = str(RENDER_YOLU / f"{dosya_adi}_bg.mp4")
    arkaplan_uret(video_suresi, arkaplan, punchline_efekt)

    # 3. ASS altyazı (WordBoundary zaman damgalarıyla)
    altyazi_ass = str(RENDER_YOLU / f"{dosya_adi}.ass")
    ass_altyazi_olustur(ses_dosyalari, diyaloglar, altyazi_ass, hook_suresi)

    # 4. Final video
    final_video = str(OUTPUT_YOLU / f"{dosya_adi}.mp4")

    # Filter chain: altyazı + hook + karakter etiketleri + watermark
    filtre_parcalari = []

    # ASS altyazı
    filtre_parcalari.append(f"ass={altyazi_ass}")

    # Hook metni — ilk saniyede büyük harflerle ortada
    if hook_metni:
        fontfile = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        hook_filtresi = (
            f"drawtext=text='{hook_metni}':fontfile={fontfile}:"
            f"fontcolor=white:fontsize=72:"
            f"x=(w-tw)/2:y=(h-th)/2:"
            f"enable='between(t,0,{hook_suresi})':"
            f"shadowcolor=black@0.7:shadowx=3:shadowy=3"
        )
        filtre_parcalari.append(hook_filtresi)

    # Karakter etiketleri — ekranda görünür, TTS okumaz
    zaman_oteleme = hook_suresi
    for ses, diyalog in zip(ses_dosyalari, diyaloglar):
        karakter = diyalog.get("karakter", "")
        diyalog_sure = ses.get("sure", 2.0)
        baslangic = zaman_oteleme
        bitis = baslangic + diyalog_sure

        if karakter:
            etiket = (
                f"drawtext=text='[{karakter}]':fontfile={fontfile}:"
                f"fontcolor=white@0.7:fontsize=36:"
                f"x=40:y=50:"
                f"enable='between(t,{baslangic:.2f},{bitis:.2f})':"
                f"shadowcolor=black@0.5:shadowx=2:shadowy=2"
            )
            filtre_parcalari.append(etiket)

        zaman_oteleme += diyalog_sure

    # BOBİ TV watermark
    filtre_parcalari.append(
        f"drawtext=text='BOBI TV':fontfile={fontfile}:"
        f"fontcolor=white@0.25:fontsize=32:"
        f"x=w-tw-30:y=30"
    )

    komple_filtre = ",".join(filtre_parcalari)

    subprocess.run([
        "ffmpeg", "-y",
        "-i", arkaplan,
        "-i", birlesik_ses,
        "-vf", komple_filtre,
        "-c:v", "libx264", "-preset", "medium",
        "-b:v", VIDEO_BITRATE,
        "-c:a", "aac", "-b:a", AUDIO_BITRATE,
        "-shortest", "-movflags", "+faststart",
        final_video
    ], capture_output=True, check=True, timeout=300)

    if not Path(final_video).exists() or Path(final_video).stat().st_size < 1000:
        raise RuntimeError(f"Final video oluşturulamadı: {final_video}")

    boyut = Path(final_video).stat().st_size // 1024
    print(f"[Render] Video hazır: {final_video} ({boyut}KB, {video_suresi:.1f}sn)")

    # Geçici dosyaları temizle
    for gecici in [birlesik_ses, arkaplan]:
        if Path(gecici).exists():
            os.remove(gecici)

    senaryo_paketi["final_video"] = final_video
    senaryo_paketi["video_suresi"] = video_suresi
    return final_video


def kapak_uret(senaryo_paketi: dict) -> str:
    """Video kapağı üret — ilk kare + PIL ile kompozit."""
    final_video = senaryo_paketi.get("final_video")
    if not final_video or not Path(final_video).exists():
        return None

    kapak_dosyasi = final_video.replace(".mp4", "_thumb.jpg")
    subprocess.run([
        "ffmpeg", "-y", "-i", final_video, "-ss", "00:00:01",
        "-frames:v", "1", "-q:v", "2", kapak_dosyasi
    ], capture_output=True, timeout=30)

    return kapak_dosyasi if Path(kapak_dosyasi).exists() else None


if __name__ == "__main__":
    print("video_render.py v3.0 yüklendi.")
