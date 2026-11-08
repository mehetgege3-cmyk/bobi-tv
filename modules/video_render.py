"""
BOBİ TV — Video Kurgu ve Render Modülü
FFmpeg ile animasyon karelerini, sesi ve altyazıyı birleştirir.
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
ASSETS_YOLU = Path("bobi_tv/production/assets")

# Shorts teknik gereksinimleri
VIDEO_GENISLIK = 1080
VIDEO_YUKSEKLIK = 1920
VIDEO_FPS = 30
VIDEO_BITRATE = "4M"
AUDIO_BITRATE = "192k"
ALTYAZI_FONT_BOYUTU = 52
ALTYAZI_RENK = "white"
ALTYAZI_ARKAPLAN = "black@0.6"


def ffmpeg_kurulu_mu() -> bool:
    result = subprocess.run(["which", "ffmpeg"], capture_output=True)
    return result.returncode == 0


def ses_birlestir(ses_dosyalari: list, cikis_dosyasi: str) -> float:
    """Birden fazla ses dosyasını sırayla birleştir."""
    if not ses_dosyalari:
        return 0.0

    if len(ses_dosyalari) == 1:
        shutil.copy(ses_dosyalari[0], cikis_dosyasi)
        return _ses_suresi(ses_dosyalari[0])

    # FFmpeg concat ile birleştir
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
        return 5.0


def arkaplan_kare_uret(renk: str, genislik: int, yukseklik: int, cikis: str):
    """Tek renkli arka plan karesi üret."""
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c={renk}:size={genislik}x{yukseklik}:rate=1",
        "-frames:v", "1",
        cikis
    ], capture_output=True, check=True, timeout=30)


def altyazi_oluştur(ses_dosyalari: list, cikis_srt: str):
    """
    TTS zamanlamalarından SRT altyazı dosyası oluştur.
    """
    satirlar = []
    zaman_oteleme = 0.0
    sira = 1

    for ses in ses_dosyalari:
        zamanlamalar = ses.get("zamanlamalar", [])
        if not zamanlamalar:
            # Tek blok altyazı
            sure = ses.get("sure", 3.0)
            bas = zaman_oteleme
            bit = zaman_oteleme + sure
            satirlar.append({
                "sira": sira,
                "baslangic": bas,
                "bitis": bit,
                "metin": ses.get("metin", ""),
            })
            sira += 1
            zaman_oteleme += sure
            continue

        # Kelime gruplarını altyazı satırlarına çevir (3-5 kelime per satır)
        grup_boyutu = 4
        for i in range(0, len(zamanlamalar), grup_boyutu):
            grup = zamanlamalar[i:i + grup_boyutu]
            bas = zaman_oteleme + grup[0]["baslangic"]
            bit = zaman_oteleme + grup[-1]["bitis"]
            metin = " ".join(k["kelime"] for k in grup)
            satirlar.append({
                "sira": sira,
                "baslangic": bas,
                "bitis": bit,
                "metin": metin,
            })
            sira += 1

        # Bir sonraki ses parçasının başlangıç zamanını ayarla
        if zamanlamalar:
            zaman_oteleme += zamanlamalar[-1]["bitis"]

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
    Döner: final video dosyası yolu.
    """
    RENDER_YOLU.mkdir(parents=True, exist_ok=True)
    OUTPUT_YOLU.mkdir(parents=True, exist_ok=True)

    dosya_adi = senaryo_paketi["dosya_adi"]
    ses_dosyalari = senaryo_paketi.get("ses_dosyalari", [])

    if not ffmpeg_kurulu_mu():
        raise RuntimeError("FFmpeg kurulu değil.")

    # 1. Sesleri birleştir
    birlesik_ses = str(RENDER_YOLU / f"{dosya_adi}_audio.wav")
    ses_yollari = [s["ses_dosyasi"] for s in ses_dosyalari if Path(s["ses_dosyasi"]).exists()]

    if ses_yollari:
        video_suresi = ses_birlestir(ses_yollari, birlesik_ses)
    else:
        video_suresi = 5.0
        # Sessiz ses oluştur
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"anullsrc=r=44100:cl=mono",
            "-t", str(video_suresi), birlesik_ses
        ], capture_output=True, timeout=30)

    # 2. Arka plan videosu oluştur (animasyon yoksa siyah arka plan)
    arkaplan = str(RENDER_YOLU / f"{dosya_adi}_bg.mp4")
    renk = "0x1a1a2e"  # BOBİ TV koyu lacivert
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c={renk}:size={VIDEO_GENISLIK}x{VIDEO_YUKSEKLIK}:rate={VIDEO_FPS}",
        "-t", str(video_suresi),
        "-c:v", "libx264", "-preset", "fast",
        arkaplan
    ], capture_output=True, check=True, timeout=120)

    # 3. Altyazı oluştur
    altyazi_srt = str(RENDER_YOLU / f"{dosya_adi}.srt")
    altyazi_oluştur(ses_dosyalari, altyazi_srt)

    # 4. Final video: arka plan + ses + altyazı
    final_video = str(OUTPUT_YOLU / f"{dosya_adi}.mp4")

    # Altyazı stilini ASS formatına çevir (daha iyi kontrol)
    altyazi_filtresi = (
        f"subtitles={altyazi_srt}:force_style='"
        f"FontName=Arial,FontSize={ALTYAZI_FONT_BOYUTU},"
        f"PrimaryColour=&H00FFFFFF,"
        f"OutlineColour=&H00000000,"
        f"BackColour=&H99000000,"
        f"Bold=1,Alignment=2,"
        f"MarginV=80'"
    )

    subprocess.run([
        "ffmpeg", "-y",
        "-i", arkaplan,
        "-i", birlesik_ses,
        "-vf", altyazi_filtresi,
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

    print(f"[Render] Video hazır: {final_video} ({Path(final_video).stat().st_size // 1024}KB, {video_suresi:.1f}s)")

    # 6. Geçici dosyaları temizle
    for gecici in [birlesik_ses, arkaplan]:
        if Path(gecici).exists():
            os.remove(gecici)

    senaryo_paketi["final_video"] = final_video
    senaryo_paketi["video_suresi"] = video_suresi
    return final_video


def kapak_uret(senaryo_paketi: dict) -> str:
    """
    Video kapağı (thumbnail) üret.
    FFmpeg ile video'nun ilk karesinden kapak al.
    """
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
    # Test
    test_paket = {
        "dosya_adi": "20261108_0001_test",
        "baslik": "BOBİ TV Test Video",
        "ses_dosyalari": []
    }
    try:
        video = video_render(test_paket)
        print(f"Test video: {video}")
    except Exception as e:
        print(f"Test hatası: {e}")
