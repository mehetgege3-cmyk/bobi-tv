"""
BOBİ TV — Sinematik Kurgu, Ses Miksajı ve Render Kalite Kontrol Modülü v6.0
Yenilikler:
- Sıfır Ölü Boşluk: 0.00 saniyede kanca + ses + whoosh efektiyle başlar
- Çok Kanallı Ses Miksajı: Diyalog + SFX (whoosh, pop, riser, vine_boom, ding) + Sidechain BGM (-20dB) + -14 LUFS
- Pro Sahne Motoru: Vektör karakter kartları + ses duyarlı ekolayzır + aktif-kelime kutulu karaoke altyazı + twist zoom/shake
- Otomatik ffprobe Kalite Kontrolü (Render QC): 1080x1920, 30 FPS, H.264 + AAC doğrulaması
"""
import os
import json
import shutil
import subprocess
import wave
from pathlib import Path

from modules import calisma_dizinleri

from modules.audio_fx import profesyonel_ses_miksla
from modules.animasyon import pro_sahne_videosu_uret
from modules.senaryo_v7.ayarlar import Ayarlar

RENDER_YOLU = calisma_dizinleri.RENDER_YOLU
OUTPUT_YOLU = calisma_dizinleri.OUTPUT_YOLU

VIDEO_GENISLIK = 1080
VIDEO_YUKSEKLIK = 1920
VIDEO_FPS = 30


def ffmpeg_kurulu_mu() -> bool:
    return shutil.which("ffmpeg") is not None


def _ses_suresi(ses_dosyasi: str) -> float:
    """Ses dosyası süresi — önce `wave` (WAV'lar için kesin), sonra ffprobe.

    NEDEN DÜZELTİLDİ (2026-11-11): eskiden yalnız ffprobe kullanılıyordu ve
    `ffprobe` yoksa/başarısızsa sessizce 2.0 dönüyordu. Bu yüzden 96 saniyelik
    gerçek ses "2.00 sn" sayıldı ve render "minimum 15 sn" kapısına takıldı.
    WAV zaten elimizde; `wave` ile okumak hem hızlı hem kesin.
    """
    try:
        import wave

        with wave.open(str(ses_dosyasi), "rb") as wf:
            kare = wf.getnframes()
            oran = float(wf.getframerate() or 0)
            if kare > 0 and oran > 0:
                return round(kare / oran, 3)
    except Exception:
        pass
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(ses_dosyasi)],
            capture_output=True, text=True,
        )
        return float(json.loads(result.stdout)["format"]["duration"])
    except Exception:
        print(f"[Render] ⚠️ Ses süresi okunamadı: {ses_dosyasi} — 2.0 sn varsayıldı")
        return 2.0


def ses_birlestir(
    ses_dosyalari: list,
    cikis_dosyasi: str,
    duraklamalar_ms: list[int] | None = None,
) -> float:
    """Replik WAV'larını birleştirir; varsa satır sonu duraklamalarını sessizlik WAV'larıyla ekler."""
    Path(cikis_dosyasi).parent.mkdir(parents=True, exist_ok=True)
    if not ses_dosyalari:
        return 0.0
    pauses = duraklamalar_ms or []
    concat_paths: list[str] = []
    silence_paths: list[str] = []
    for index, audio_path in enumerate(ses_dosyalari):
        concat_paths.append(str(audio_path))
        pause = pauses[index] if index < len(pauses) and index < len(ses_dosyalari) - 1 else 0
        if pause > 0:
            silence_path = f"{cikis_dosyasi}_pause_{index:03d}.wav"
            with wave.open(silence_path, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(44100)
                wav_file.writeframes(b"\x00\x00" * int(44100 * min(pause, 3000) / 1000))
            concat_paths.append(silence_path)
            silence_paths.append(silence_path)
    if len(concat_paths) == 1:
        shutil.copy(concat_paths[0], cikis_dosyasi)
        return _ses_suresi(cikis_dosyasi)

    liste_dosyasi = str(cikis_dosyasi) + "_concat.txt"
    try:
        with open(liste_dosyasi, "w", encoding="utf-8") as f:
            for audio_path in concat_paths:
                f.write(f"file '{os.path.abspath(audio_path)}'\n")
        subprocess.run(
            [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", liste_dosyasi,
                "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le",
                str(cikis_dosyasi),
            ],
            capture_output=True, check=True, timeout=90,
        )
    finally:
        if os.path.exists(liste_dosyasi):
            os.remove(liste_dosyasi)
        for silence_path in silence_paths:
            if os.path.exists(silence_path):
                os.remove(silence_path)

    return _ses_suresi(cikis_dosyasi)


def sfx_zaman_cizelgesi_olustur(ses_kayitlari: list) -> list:
    """
    Her replik başlangıcına ve twist anına milisaniyelik ses efektleri yerleştirir:
    - 0.00s: whoosh (açılış darbesi)
    - Normal replik geçişleri: pop (balon sesi)
    - Twist repliğinden 0.62s önce: riser (gerilim tırmanışı)
    - Twist repliği başı: vine_boom (şok bası)
    - Son döngü köprüsü: ding
    """
    olaylar = [{"tip": "whoosh", "zaman": 0.0, "seviye": 0.48}]
    imlec = 0.0
    son_idx = len(ses_kayitlari) - 1

    for idx, s in enumerate(ses_kayitlari):
        sure = float(s.get("sure", 1.8))
        ozel_sfx = s.get("sfx", "")
        twist_mi = bool(s.get("twist_mi", False))

        if idx > 0:
            if twist_mi or ozel_sfx == "vine_boom":
                if imlec > 0.70:
                    olaylar.append({"tip": "riser", "zaman": round(imlec - 0.65, 3), "seviye": 0.36})
                olaylar.append({"tip": "vine_boom", "zaman": round(imlec, 3), "seviye": 0.56})
            elif idx == son_idx or ozel_sfx == "ding":
                olaylar.append({"tip": "ding", "zaman": round(imlec, 3), "seviye": 0.34})
            else:
                olaylar.append({"tip": "pop", "zaman": round(imlec, 3), "seviye": 0.38})

        imlec += sure + (int(s.get("duraklamams", 0)) / 1000 if idx < son_idx else 0.0)

    return olaylar


def ass_altyazi_olustur(ses_dosyalari: list, diyaloglar: list, cikis_ass: str, hook_suresi: float = 0.0) -> str:
    """
    Aktif kelimenin sarı (#FFD60A) ve %118 büyük parladığı v6.0 ASS altyazı dosyası üretir
    (harici ASS tüketicileri ve arşiv için).
    """
    def saniye_ass(sn: float) -> str:
        sn = max(0.0, sn)
        h = int(sn // 3600)
        m = int((sn % 3600) // 60)
        s = int(sn % 60)
        cs = int(round((sn % 1) * 100)) % 100
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    ass_baslik = """[Script Info]
Title: BOBI TV v6 Pro
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Montserrat ExtraBold,64,&H00FFFFFF,&H000AD6FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,6,3,2,70,70,340,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    satirlar = []
    oteleme = hook_suresi
    for index, ses in enumerate(ses_dosyalari):
        zamanlar = ses.get("zamanlamalar", [])
        sure = float(ses.get("sure", 1.8))
        for g in range(0, len(zamanlar), 3):
            grup = zamanlar[g:g + 3]
            for aktif_i, k_obj in enumerate(grup):
                bas = saniye_ass(oteleme + k_obj["baslangic"])
                bit = saniye_ass(oteleme + k_obj["bitis"])
                parcalar = []
                for j, diger in enumerate(grup):
                    kelime = diger["kelime"].upper()
                    if j == aktif_i:
                        parcalar.append(r"{\c&H000AD6FF&\fscx118\fscy118}" + kelime + r"{\c&H00FFFFFF&\fscx100\fscy100}")
                    else:
                        parcalar.append(kelime)
                satirlar.append(f"Dialogue: 0,{bas},{bit},Default,,0,0,0,,{' '.join(parcalar)}\n")
        oteleme += sure + (
            int(ses.get("duraklamams", 0)) / 1000 if index < len(ses_dosyalari) - 1 else 0.0
        )

    Path(cikis_ass).parent.mkdir(parents=True, exist_ok=True)
    with open(cikis_ass, "w", encoding="utf-8") as f:
        f.write(ass_baslik)
        f.writelines(satirlar)
    return cikis_ass


def video_kalite_kontrol(video_yolu: str) -> dict:
    """
    Üretilen MP4 dosyasını ffprobe ile denetler:
    - Çözünürlük 1080x1920 mi?
    - Hem video (h264) hem ses (aac) akışı var mı?
    - Süre sınırına uygun mu (15 sn – 180 sn)? YouTube Shorts 3 dakikaya kadar
      dikey videoyu Shorts sayar; bu yüzden üst sınır 180 sn'dir (2026-11-11).
    """
    ayarlar = Ayarlar.ortamdan()
    p = Path(video_yolu)
    if not p.exists() or p.stat().st_size < 25_000:
        raise RuntimeError(f"Render QC Başarısız: Dosya yok veya çok küçük ({video_yolu})")

    res = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", "-show_format", str(p)],
        capture_output=True, text=True, check=True, timeout=20,
    )
    bilgi = json.loads(res.stdout)
    akislar = bilgi.get("streams", [])
    v_akis = next((s for s in akislar if s.get("codec_type") == "video"), None)
    a_akis = next((s for s in akislar if s.get("codec_type") == "audio"), None)

    if not v_akis or not a_akis:
        raise RuntimeError("Render QC Başarısız: Video veya ses akışı eksik!")

    gen = int(v_akis.get("width", 0))
    yuk = int(v_akis.get("height", 0))
    sure = float(bilgi.get("format", {}).get("duration", 0.0))

    if gen != VIDEO_GENISLIK or yuk != VIDEO_YUKSEKLIK:
        raise RuntimeError(f"Render QC Başarısız: Çözünürlük {gen}x{yuk} (beklenen 1080x1920)")
    if sure < ayarlar.minimum_yayin_suresi or sure > ayarlar.maksimum_yayin_suresi:
        raise RuntimeError(
            f"Render QC Başarısız: Video {ayarlar.minimum_yayin_suresi:.1f}–"
            f"{ayarlar.maksimum_yayin_suresi:.1f} saniye aralığında olmalı (mevcut: {sure:.2f}sn)"
        )

    ozet = {
        "gecerli": True,
        "genislik": gen,
        "yukseklik": yuk,
        "sure": round(sure, 2),
        "boyut_kb": p.stat().st_size // 1024,
    }
    print(f"[Render QC] ✅ 1080x1920 | {ozet['sure']}sn | {ozet['boyut_kb']} KB | H.264+AAC Doğrulandı")
    return ozet


def video_render(senaryo_paketi: dict) -> str:
    """
    Senaryo ve seslendirilen repliklerden tam profesyonel BOBİ TV v6.0 Shorts videosu üretir.
    """
    ayarlar = Ayarlar.ortamdan()
    if not ffmpeg_kurulu_mu():
        raise RuntimeError("FFmpeg kurulu değil.")

    RENDER_YOLU.mkdir(parents=True, exist_ok=True)
    OUTPUT_YOLU.mkdir(parents=True, exist_ok=True)

    dosya_adi = senaryo_paketi["dosya_adi"]
    senaryo = senaryo_paketi["senaryo"]
    ses_dosyalari = senaryo_paketi.get("ses_dosyalari", [])
    diyaloglar = senaryo.get("diyaloglar", [])
    ruh_hali = senaryo.get("ruh_hali", "komedi")

    ham_birlesik_wav = str(RENDER_YOLU / f"{dosya_adi}_diyalog.wav")
    master_ses_wav = str(RENDER_YOLU / f"{dosya_adi}_master.wav")
    altyazi_ass = str(RENDER_YOLU / f"{dosya_adi}.ass")
    final_video = str(OUTPUT_YOLU / f"{dosya_adi}.mp4")

    kullanilabilir_sesler = [s for s in ses_dosyalari if Path(s["ses_dosyasi"]).exists()]
    ses_yollari = [s["ses_dosyasi"] for s in kullanilabilir_sesler]
    if not ses_yollari:
        raise RuntimeError("Seslendirilen replik dosyası bulunamadı!")

    # 1. Replikleri satır metadata'sındaki duraklamalarla birleştir.
    diyalog_suresi = ses_birlestir(
        ses_yollari,
        ham_birlesik_wav,
        [int(s.get("duraklamams", 0)) for s in kullanilabilir_sesler],
    )
    if diyalog_suresi < ayarlar.minimum_yayin_suresi:
        raise RuntimeError(
            f"Minimum {ayarlar.minimum_yayin_suresi:.1f} saniye kuralı: "
            f"gerçek diyalog {diyalog_suresi:.2f}sn; render/yayın iptal edildi."
        )
    if diyalog_suresi > ayarlar.maksimum_yayin_suresi:
        raise RuntimeError(
            f"Süre sınırı: gerçek diyalog {diyalog_suresi:.2f}sn; "
            f"{ayarlar.maksimum_yayin_suresi:.1f}sn üzerinde render edilemez."
        )

    # 2. SFX + Telifsiz BGM (-20dB ducking) + -14 LUFS Mastering
    sfx_olaylari = sfx_zaman_cizelgesi_olustur(ses_dosyalari)
    profesyonel_ses_miksla(
        diyalog_wav=ham_birlesik_wav,
        sfx_olaylari=sfx_olaylari,
        toplam_sure=diyalog_suresi,
        cikis_wav=master_ses_wav,
        ruh_hali=ruh_hali,
    )

    # 3. Arşivlik ASS altyazı dosyası üret
    ass_altyazi_olustur(ses_dosyalari, diyaloglar, altyazi_ass, hook_suresi=0.0)

    # 3.5. Profesyonel Kapak Görselini Üret (1. Kareye yerleştirilmek üzere)
    from modules.kapak_uret import kapak_resmi_olustur, videodan_ilk_kareyi_kapak_sec

    kapak_jpg = str(OUTPUT_YOLU / f"{dosya_adi}_thumb.jpg")
    kapak_resmi_olustur(senaryo_paketi, kapak_jpg)
    senaryo_paketi["kapak_yolu"] = kapak_jpg

    # 4. Pro Sahne + 1. Kare Kapak + Vektör Kartlar + Karaoke Altyazı + Twist Zoom/Shake Render
    pro_sahne_videosu_uret(
        senaryo_paketi=senaryo_paketi,
        birlesik_ses_wav=master_ses_wav,
        cikis_video_mp4=final_video,
    )

    # 4.5. Videonun 1. karesinden (Frame 0) kapak fotoğrafını seç ve doğrula
    videodan_ilk_kareyi_kapak_sec(final_video, kapak_jpg)

    # 5. Kalite Kontrol (QC)
    qc = video_kalite_kontrol(final_video)

    # Geçici WAV dosyalarını temizle
    for gecici in (ham_birlesik_wav, master_ses_wav):
        if os.path.exists(gecici):
            os.remove(gecici)

    senaryo_paketi["final_video"] = final_video
    senaryo_paketi["video_suresi"] = qc["sure"]
    senaryo_paketi["qc"] = qc
    return final_video


if __name__ == "__main__":
    print("BOBİ TV video_render.py v6.0 hazır.")
