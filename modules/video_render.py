"""
BOBİ TV — Video Kurgu ve Render Modülü v2.0
Viralite odaklı: hook metni, karakter etiketleri (okunmaz), punchline efektleri, perfect loop.
Dikey 9:16 Shorts formatında final video üretir.
"""
import os
import json
import subprocess
import shutil
from pathlib import Path
from datetime import datetime


RENDER_YOLU = Path("bobi_tv/production/render")
OUTPUT_YOLU = Path("bobi_tv/output")

# Shorts teknik gereksinimleri
VIDEO_GENISLIK = 1080
VIDEO_YUKSEKLIK = 1920
VIDEO_FPS = 30
VIDEO_BITRATE = "6M"
AUDIO_BITRATE = "192k"

# Altyazı stili
ALTYAZI_FONT = "Arial"
ALTYAZI_FONT_BOYUTU = 58
ALTYAZI_RENK = "&H00FFFFFF"        # Beyaz
ALTYAZI_CERCEVE = "&H00000000"      # Siyah çerçeve
ALTYAZI_ARKAPLAN = "&HAA000000"     # Yarı saydam siyah
ALTYAZI_MARGIN_V = 120              # Alt kenardan boşluk

# Karakter etiketi stili (ekranda görünür, TTS okumaz)
ETIKET_FONT_BOYUTU = 36
ETIKET_RENK = "white@0.7"
ETIKET_MARGIN_V = 200                # Üst kenardan boşluk

# Hook metni stili
HOOK_FONT_BOYUTU = 72
HOOK_RENK = "white"


def ffmpeg_kurulu_mu() -> bool:
    result = subprocess.run(["which", "ffmpeg"], capture_output=True)
    return result.returncode == 0


def ses_birlestir(ses_dosyalari: list, cikis_dosyasi: str) -> float:
    """Birden fazla ses dosyasını sırayla birleştir. Boşluk olmadan."""
    if not ses_dosyalari:
        return 0.0

    if len(ses_dosyalari) == 1:
        shutil.copy(ses_dosyalari[0], cikis_dosyasi)
        return _ses_suresi(ses_dosyalari[0])

    # FFmpeg concat ile birleştir — gap yok
    liste_dosyasi = cikis_dosyasi + ".txt"
    with open(liste_dosyasi, "w") as f:
        for s in ses_dosyalari:
            f.write(f"file '{os.path.abspath(s)}'\n")

    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", liste_dosyasi,
        "-ar", "44100", "-ac", "1",
        cikis_dosyasi
    ], capture_output=True, check=True, timeout=120)

    os.remove(liste_dosyasi)
    return _ses_suresi(cikis_dosyasi)


def _ses_suresi(ses_dosyasi: str) -> float:
    """FFprobe ile ses süresi al."""
    try:
        result = subprocess.run([
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", ses_dosyasi
        ], capture_output=True, timeout=15)
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])
    except Exception:
        return 3.0


def arkaplan_uret(sure: float, cikis: str, efekt: str = None):
    """
    Gradient + hareketli arka plan üret.
    Punchline efektuna göre arka plan rengi değişebilir.
    """
    # BOBİ TV renk paleti: koyu lacivert → mor
    renk_baslangic = "0x0a0a1e"
    renk_bitis = "0x2a1a4e"

    if efekt == "siyah_beyaz_zoom":
        # Dramatik an için daha koyu
        renk_baslangic = "0x050508"
        renk_bitis = "0x1a1a2e"

    # Gradient arka plan
    gradient_filtresi = (
        f"gradients=s={VIDEO_GENISLIK}x{VIDEO_YUKSEKLIK}:"
        f"d={sure}:"
        f"c0={renk_baslangic}:c1={renk_bitis}:c2={renk_baslangic}:"
        f"x0=0:y0=0:x1={VIDEO_GENISLIK}:y1={VIDEO_YUKSEKLIK}:"
        f"speed=0.008"
    )

    try:
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", gradient_filtresi,
            "-t", str(sure),
            "-r", str(VIDEO_FPS),
            "-c:v", "libx264", "-preset", "fast",
            "-pix_fmt", "yuv420p",
            cikis
        ], capture_output=True, check=True, timeout=120)
        print(f"[Render] Gradient arka plan: {sure:.1f}sn")
    except Exception as e:
        print(f"[Render] Gradient hatası, düz renk: {e}")
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=c={renk_baslangic}:size={VIDEO_GENISLIK}x{VIDEO_YUKSEKLIK}:rate={VIDEO_FPS}",
            "-t", str(sure),
            "-c:v", "libx264", "-preset", "fast",
            cikis
        ], capture_output=True, check=True, timeout=120)


def altyazi_olustur(ses_dosyalari: list, diyaloglar: list, cikis_srt: str):
    """
    TTS zamanlamalarından SRT altyazı dosyası oluştur.
    Karakter isimleri altyazıda yer almaz — sadece diyalog metni.
    """
    satirlar = []
    zaman_oteleme = 0.0
    sira = 1

    for i, ses in enumerate(ses_dosyalari):
        zamanlamalar = ses.get("zamanlamalar", [])
        metin = ses.get("metin", "")
        sure = ses.get("sure", 3.0)
        karakter = ses.get("karakter", "")

        if not zamanlamalar:
            bas = zaman_oteleme
            bit = zaman_oteleme + sure
            satirlar.append({
                "sira": sira,
                "baslangic": bas,
                "bitis": bit,
                "metin": metin,
                "karakter": karakter
            })
            sira += 1
            zaman_oteleme += sure
            continue

        # Kelime gruplarını altyazı satırlarına çevir (3-4 kelime per satır)
        grup_boyutu = 4
        for j in range(0, len(zamanlamalar), grup_boyutu):
            grup = zamanlamalar[j:j + grup_boyutu]
            bas = zaman_oteleme + grup[0]["baslangic"]
            bit = zaman_oteleme + grup[-1]["bitis"]
            metin_grup = " ".join(k["kelime"] for k in grup)
            satirlar.append({
                "sira": sira,
                "baslangic": bas,
                "bitis": bit,
                "metin": metin_grup,
                "karakter": karakter
            })
            sira += 1

        zaman_oteleme += sure

    # SRT formatında yaz
    def saniye_srt(sn: float) -> str:
        h = int(sn // 3600)
        m = int((sn % 3600) // 60)
        s = int(sn % 60)
        ms = int((sn % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    with open(cikis_srt, "w", encoding="utf-8") as f:
        for satir in satirlar:
            f.write(f"{satir['sira']}\n")
            f.write(f"{saniye_srt(satir['baslangic'])} --> {saniye_srt(satir['bitis'])}\n")
            f.write(f"{satir['metin']}\n\n")

    return cikis_srt


def video_render(senaryo_paketi: dict) -> str:
    """
    Senaryo paketinden tam Shorts videosu üretir.
    Hook metni → diyaloglar (karakter etiketleri ekranda) → punchline efekt → loop
    Döner: final video dosyası yolu.
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
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=mono",
            "-t", str(diyalog_suresi), birlesik_ses
        ], capture_output=True, timeout=30)

    # Toplam video süresi = hook + diyaloglar (loop için bekleme yok)
    video_suresi = hook_suresi + diyalog_suresi

    # 2. Arka plan videosu oluştur
    arkaplan = str(RENDER_YOLU / f"{dosya_adi}_bg.mp4")
    arkaplan_uret(video_suresi, arkaplan, punchline_efekt)

    # 3. Altyazı oluştur (karakter isimleri yok, sadece diyalog)
    altyazi_srt = str(RENDER_YOLU / f"{dosya_adi}.srt")
    altyazi_olustur(ses_dosyalari, diyaloglar, altyazi_srt)

    # 4. Final video: arka plan + ses + altyazı + hook + karakter etiketleri + watermark
    final_video = str(OUTPUT_YOLU / f"{dosya_adi}.mp4")

    # Kompleks filter graph oluştur
    filtre_parcalari = []

    # 4a. Altyazı
    altyazi_filtresi = (
        f"subtitles={altyazi_srt}:force_style='"
        f"FontName={ALTYAZI_FONT},FontSize={ALTYAZI_FONT_BOYUTU},"
        f"PrimaryColour={ALTYAZI_RENK},"
        f"OutlineColour={ALTYAZI_CERCEVE},"
        f"BackColour={ALTYAZI_ARKAPLAN},"
        f"Bold=1,Alignment=2,MarginV={ALTYAZI_MARGIN_V}'"
    )
    filtre_parcalari.append(altyazi_filtresi)

    # 4b. Hook metni — ilk saniyelerde büyük harflerle ortada
    if hook_metni:
        hook_filtresi = (
            f"drawtext=text='{hook_metni}':"
            f"fontcolor={HOOK_RENK}:fontsize={HOOK_FONT_BOYUTU}:"
            f"x=(w-tw)/2:y=(h-th)/2:"
            f"enable='between(t,0,{hook_suresi})':"
            f"shadowcolor=black@0.7:shadowx=3:shadowy=3:"
            f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        )
        filtre_parcalari.append(hook_filtresi)

    # 4c. Karakter etiketleri — ekranda görünür, okunmaz
    # Her diyalog sırasında o diyalogun karakteri sol üstte yazar
    zaman_oteleme = hook_suresi
    for i, (ses, diyalog) in enumerate(zip(ses_dosyalari, diyaloglar)):
        karakter = diyalog.get("karakter", "")
        diyalog_sure = ses.get("sure", 2.0)
        baslangic = zaman_oteleme
        bitis = baslangic + diyalog_sure

        if karakter:
            # Karakter etiketi sol üst köşede
            etiket_filtresi = (
                f"drawtext=text='[{karakter}]':"
                f"fontcolor={ETIKET_RENK}:fontsize={ETIKET_FONT_BOYUTU}:"
                f"x=40:y=50:"
                f"enable='between(t,{baslangic:.2f},{bitis:.2f})':"
                f"shadowcolor=black@0.5:shadowx=2:shadowy=2"
            )
            filtre_parcalari.append(etiket_filtresi)

        zaman_oteleme += diyalog_sure

    # 4d. BOBİ TV watermark — sağ üst köşede yarı saydam
    watermark_filtresi = (
        f"drawtext=text='BOBI TV':"
        f"fontcolor=white@0.25:fontsize=32:"
        f"x=w-tw-30:y=30:"
        f"shadowcolor=black@0.3:shadowx=1:shadowy=1"
    )
    filtre_parcalari.append(watermark_filtresi)

    # 4e. Punchline efekt — son diyalogdan önce zoom
    # Son diyalog'un başlangıç zamanı
    if len(ses_dosyalari) >= 2:
        punchline_baslangic = hook_suresi + sum(s.get("sure", 2.0) for s in ses_dosyalari[:-1])
        if punchline_efekt == "zoom_in":
            # Hızlı zoom in efekti
            zoom_filtresi = (
                f"zoompan=z='min(zoom+0.1,1.5)':d={VIDEO_FPS}:s={VIDEO_GENISLIK}x{VIDEO_YUKSEKLIK}:"
                f"fps={VIDEO_FPS}"
            )
            # Daha basit: crop ile scale
            filtre_parcalari.append(f"scale={int(VIDEO_GENISLIK*1.05)}:{int(VIDEO_YUKSEKLIK*1.05)},crop={VIDEO_GENISLIK}:{VIDEO_YUKSEKLIK}")

    komple_filtre = ",".join(filtre_parcalari)

    subprocess.run([
        "ffmpeg", "-y",
        "-i", arkaplan,
        "-i", birlesik_ses,
        "-vf", komple_filtre,
        "-c:v", "libx264", "-preset", "medium",
        "-b:v", VIDEO_BITRATE,
        "-c:a", "aac", "-b:a", AUDIO_BITRATE,
        "-shortest",
        "-movflags", "+faststart",
        final_video
    ], capture_output=True, check=True, timeout=300)

    # 5. Dosya varlığını doğrula
    if not Path(final_video).exists() or Path(final_video).stat().st_size < 1000:
        raise RuntimeError(f"Final video oluşturulamadı: {final_video}")

    video_boyut = Path(final_video).stat().st_size // 1024
    print(f"[Render] Video hazır: {final_video} ({video_boyut}KB, {video_suresi:.1f}sn)")

    # 6. Geçici dosyaları temizle
    for gecici in [birlesik_ses, arkaplan]:
        if Path(gecici).exists():
            os.remove(gecici)

    senaryo_paketi["final_video"] = final_video
    senaryo_paketi["video_suresi"] = video_suresi
    return final_video


def kapak_uret(senaryo_paketi: dict) -> str:
    """Video kapağı (thumbnail) üret — ilk kare."""
    final_video = senaryo_paketi.get("final_video")
    if not final_video or not Path(final_video).exists():
        return None

    kapak_dosyasi = final_video.replace(".mp4", "_thumb.jpg")
    subprocess.run([
        "ffmpeg", "-y",
        "-i", final_video,
        "-ss", "00:00:01",
        "-frames:v", "1",
        "-q:v", "2",
        kapak_dosyasi
    ], capture_output=True, timeout=30)

    return kapak_dosyasi if Path(kapak_dosyasi).exists() else None


if __name__ == "__main__":
    test_paket = {
        "dosya_adi": "test_render",
        "senaryo": {
            "hook_metni": "KURUMSAL HAYAT ÖZETİ",
            "hook_suresi": 1.0,
            "diyaloglar": [
                {"karakter": "KÖPEK", "metin": "Bugün çok yoruldum.", "ses": "yavas_bikkin"},
                {"karakter": "TOPLANTI", "metin": "Neden?", "ses": "robotik_koro"}
            ],
            "punchline_efekt": "zoom_in"
        },
        "ses_dosyalari": []
    }
    try:
        video = video_render(test_paket)
        print(f"Test video: {video}")
    except Exception as e:
        print(f"Test hatası: {e}")
