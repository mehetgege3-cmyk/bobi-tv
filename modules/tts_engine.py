"""
BOBİ TV — TTS Ses Üretim Modülü v3.0
edge-tts ile Türkçe karakter sesleri + WordBoundary zaman damgaları.
Karakter isimleri OKUNMAZ — sadece diyalog metni seslendirilir.
Çok katmanlı fallback: edge-tts → espeak-ng → sessiz WAV.
"""
import os
import json
import subprocess
import asyncio
import shutil
from pathlib import Path


TTS_YOLU = Path("bobi_tv/production/tts")
PIPER_MODEL_YOLU = Path("bobi_tv/config/piper_models")

# edge-tts Türkçe sesler — her karakter tipi için farklı ses
EDGE_SESLER = {
    # Erkek sesler
    "yavas_bikkin": {"voice": "tr-TR-AhmetNeural", "rate": "-15%", "volume": "-10%"},
    "yavas_dramatik": {"voice": "tr-TR-AhmetNeural", "rate": "-25%", "volume": "-5%", "pitch": "-10Hz"},
    "normal": {"voice": "tr-TR-AhmetNeural", "rate": "+0%", "volume": "+0%"},
    "ciddi": {"voice": "tr-TR-AhmetNeural", "rate": "-5%", "volume": "+0%"},
    "bikeyn": {"voice": "tr-TR-AhmetNeural", "rate": "-5%", "volume": "-10%"},
    "bikeyn_dramatik": {"voice": "tr-TR-AhmetNeural", "rate": "-20%", "volume": "-5%", "pitch": "-15Hz"},
    "uykulu": {"voice": "tr-TR-AhmetNeural", "rate": "-30%", "volume": "-20%", "pitch": "-20Hz"},
    "dusunceli": {"voice": "tr-TR-AhmetNeural", "rate": "-15%", "volume": "-10%", "pitch": "-10Hz"},
    "soğuk": {"voice": "tr-TR-AhmetNeural", "rate": "-10%", "volume": "-15%", "pitch": "-15Hz"},
    "gururlu": {"voice": "tr-TR-AhmetNeural", "rate": "+0%", "volume": "+5%", "pitch": "+5Hz"},
    # Robotik/toplanti sesi — hızlı, yüksek pitch
    "robotik": {"voice": "tr-TR-AhmetNeural", "rate": "+30%", "volume": "+10%", "pitch": "+50Hz"},
    "robotik_koro": {"voice": "tr-TR-AhmetNeural", "rate": "+30%", "volume": "+10%", "pitch": "+50Hz"},
    "enerjik": {"voice": "tr-TR-AhmetNeural", "rate": "+20%", "volume": "+10%", "pitch": "+10Hz"},
    "kesin": {"voice": "tr-TR-AhmetNeural", "rate": "+10%", "volume": "+5%"},
    "sinirli": {"voice": "tr-TR-AhmetNeural", "rate": "+40%", "volume": "+15%", "pitch": "+15Hz"},
    "endiseli": {"voice": "tr-TR-AhmetNeural", "rate": "+10%", "volume": "-10%", "pitch": "+10Hz"},
    "suprized": {"voice": "tr-TR-AhmetNeural", "rate": "+20%", "volume": "+5%", "pitch": "+30Hz"},
    "umutlu": {"voice": "tr-TR-AhmetNeural", "rate": "+5%", "volume": "+0%", "pitch": "+10Hz"},
    # Derin ses (evren/kader)
    "derin": {"voice": "tr-TR-AhmetNeural", "rate": "-10%", "volume": "+5%", "pitch": "-30Hz"},
    "derin_dramatik": {"voice": "tr-TR-AhmetNeural", "rate": "-30%", "volume": "+5%", "pitch": "-30Hz"},
    # Alarm — özel efekekt, normal TTS değil
    "alarm": {"voice": "tr-TR-AhmetNeural", "rate": "+50%", "volume": "+20%", "pitch": "+80Hz"},
}

VARSAYILAN_SES = {"voice": "tr-TR-AhmetNeural", "rate": "+0%", "volume": "+0%"}


def edge_tts_kurulu_mu() -> bool:
    """edge-tts Python paketi kurulu mu kontrol et."""
    result = subprocess.run(
        ["python", "-c", "import edge_tts; print('OK')"],
        capture_output=True, text=True
    )
    return "OK" in result.stdout


def ses_tonu_al(ses_tipi: str) -> dict:
    return EDGE_SESLER.get(ses_tipi, VARSAYILAN_SES)


async def _edge_tts_uret(metin: str, cikis_dosyasi: str, ses_tipi: str) -> list:
    """
    edge-tts ile ses üret ve WordBoundary zaman damgalarını topla.
    Döner: word_timestamps listesi
    """
    import edge_tts

    ton = ses_tonu_al(ses_tipi)
    voice = ton["voice"]
    rate = ton.get("rate", "+0%")
    volume = ton.get("volume", "+0%")
    pitch = ton.get("pitch", "+0Hz")

    communicate = edge_tts.Communicate(metin, voice, rate=rate, volume=volume, pitch=pitch)

    word_timestamps = []

    with open(cikis_dosyasi, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start_ms = round(chunk["offset"] / 10_000, 1)
                dur_ms = round(chunk["duration"] / 10_000, 1)
                word_timestamps.append({
                    "kelime": chunk["text"],
                    "baslangic": round(start_ms / 1000, 3),
                    "bitis": round((start_ms + dur_ms) / 1000, 3)
                })

    return word_timestamps


def metin_sese_cevir(metin: str, dosya_adi: str, ses_tipi: str = "normal") -> dict:
    """
    Metni sese çevirir. Karakter ismi OKUNMAZ.
    Döner: {ses_dosyasi, zamanlamalar, sure, metin, ses_tipi}
    """
    TTS_YOLU.mkdir(parents=True, exist_ok=True)
    ses_dosyasi = TTS_YOLU / f"{dosya_adi}.wav"

    # Türkçe diksiyon düzeltme
    metin = _sanitize_for_tts(metin)

    word_timestamps = []

    # Katman 1: edge-tts (en kaliteli, ama GitHub Actions'ta 403 olabilir)
    if edge_tts_kurulu_mu():
        try:
            word_timestamps = asyncio.run(
                _edge_tts_uret(metin, str(ses_dosyasi), ses_tipi)
            )
            if ses_dosyasi.exists() and ses_dosyasi.stat().st_size > 1024:
                print(f"[TTS] edge-tts: {metin[:40]}... (ses: {ses_tipi})")
            else:
                raise RuntimeError("edge-tts çıktı boş")
        except Exception as e:
            if "403" in str(e) or "Invalid response" in str(e):
                print(f"[TTS] edge-tts 403 (IP engeli), gTTS fallback")
            else:
                print(f"[TTS] edge-tts hatası, gTTS fallback: {e}")
            # Katman 2: gTTS (Google Translate TTS — GitHub Actions'ta çalışır)
            try:
                ses_dosyasi = _gtts_uret(metin, dosya_adi, ses_tipi)
            except Exception as e2:
                print(f"[TTS] gTTS de başarısız: {e2}")
                ses_dosyasi = _espeak_fallback(metin, dosya_adi, ses_tipi)
    else:
        # edge-tts yoksa direkt gTTS dene
        try:
            ses_dosyasi = _gtts_uret(metin, dosya_adi, ses_tipi)
        except Exception:
            ses_dosyasi = _espeak_fallback(metin, dosya_adi, ses_tipi)

    # Süre hesapla
    sure = _ses_suresi_hesapla(ses_dosyasi)

    # Zaman damgaları yoksa sahte üret
    if not word_timestamps:
        word_timestamps = _sahte_zamanlama(metin, sure)

    return {
        "ses_dosyasi": str(ses_dosyasi),
        "zamanlamalar": word_timestamps,
        "sure": sure,
        "metin": metin,
        "ses_tipi": ses_tipi
    }


def _sanitize_for_tts(metin: str) -> str:
    """Türkçe diksiyon düzeltme — TTS'nin yanlış okumasını engeller."""
    import re
    # M.Ö. → milattan önce
    metin = re.sub(r'\bM\.Ö\.\s*', 'milattan önce ', metin)
    metin = re.sub(r'\bMÖ\b', 'milattan önce', metin)
    # %50 → yüzde 50
    metin = re.sub(r'%(\d+)', r'yüzde \1', metin)
    # Binlik ayraç: 1.234 → 1234
    metin = re.sub(r'(\d)\.(\d{3})\b', r'\1\2', metin)
    # Ondalık: 1.5 → 1,5 (Türkçe)
    metin = re.sub(r'(\d)\.(\d)', r'\1,\2', metin)
    # Markdown temizle
    metin = re.sub(r'[#*_`]', '', metin)
    # Çoklu boşluk
    metin = re.sub(r'\s+', ' ', metin).strip()
    return metin


def _piper_calisiyor_mu() -> bool:
    result = subprocess.run(["which", "piper"], capture_output=True)
    return result.returncode == 0


def _gtts_uret(metin: str, dosya_adi: str, ses_tipi: str) -> Path:
    """
    gTTS (Google Translate TTS) ile Türkçe ses üret.
    GitHub Actions'ta çalışır (edge-tts 403 verdiğinde fallback).
    Ses tonuna göre atempo (hız) ve pitch ayarı uygular.
    """
    from gtts import gTTS
    import tempfile

    TTS_YOLU.mkdir(parents=True, exist_ok=True)
    ses_dosyasi = TTS_YOLU / f"{dosya_adi}.wav"
    ton = ses_tonu_al(ses_tipi)

    # gTTS ile MP3 üret
    tmp_mp3 = str(ses_dosyasi).replace(".wav", ".mp3")
    tts = gTTS(text=metin, lang="tr", slow=False)
    tts.save(tmp_mp3)

    # MP3 → WAV + pitch/speed ayarı (FFmpeg)
    ton = ses_tonu_al(ses_tipi)
    rate_str = ton.get("rate", "+0%")
    pitch_str = ton.get("pitch", "+0Hz")

    # Rate → atempo
    try:
        pct = int(rate_str.replace("%", "").replace("+", ""))
        atempo = 1.0 + (pct / 100.0)
    except Exception:
        atempo = 1.0

    # Pitch → asetrate (pitch değiştirme)
    try:
        hz_str = pitch_str.replace("Hz", "").replace("+", "")
        pitch_hz = int(hz_str) if hz_str else 0
        asetrate = 44100 * (1.0 + pitch_hz / 1000.0)
    except Exception:
        asetrate = 44100

    # Volume
    try:
        vol_str = ton.get("volume", "+0%").replace("%", "").replace("+", "")
        vol_pct = int(vol_str) if vol_str else 0
        volume = 1.0 + (vol_pct / 100.0)
    except Exception:
        volume = 1.0

    audio_filter = f"atempo={atempo},asetrate={asetrate},aresample=44100,volume={volume}"

    subprocess.run([
        "ffmpeg", "-y", "-i", tmp_mp3,
        "-af", audio_filter,
        "-ar", "44100", "-ac", "1",
        str(ses_dosyasi)
    ], capture_output=True, check=True, timeout=30)

    # MP3'ü sil
    if os.path.exists(tmp_mp3):
        os.remove(tmp_mp3)

    print(f"[TTS] gTTS: {metin[:40]}... (atempo: {atempo}, pitch: {pitch_str})")
    return ses_dosyasi


def _piper_uret(metin: str, dosya_adi: str, ses_tipi: str) -> Path:
    """Piper ile ses üret (fallback)."""
    TTS_YOLU.mkdir(parents=True, exist_ok=True)
    ses_dosyasi = TTS_YOLU / f"{dosya_adi}.wav"
    model_dosyasi = PIPER_MODEL_YOLU / "tr_TR-dfki-medium.onnx"

    if model_dosyasi.exists():
        try:
            subprocess.run(
                ["piper", "--model", str(model_dosyasi), "--output_file", str(ses_dosyasi)],
                input=metin.encode("utf-8"),
                capture_output=True, timeout=60
            )
            return ses_dosyasi
        except Exception:
            pass

    return _espeak_fallback(metin, dosya_adi, ses_tipi)


def _espeak_fallback(metin: str, dosya_adi: str, ses_tipi: str) -> Path:
    """espeak-ng ile Türkçe ses üret (son çare fallback)."""
    TTS_YOLU.mkdir(parents=True, exist_ok=True)
    ses_dosyasi = TTS_YOLU / f"{dosya_adi}.wav"
    ton = ses_tonu_al(ses_tipi)

    espeak_pitch = max(1, min(99, 50 + _pitch_to_espeak(ton.get("pitch", "+0Hz"))))
    espeak_speed = int(175 * _rate_to_espeak(ton.get("rate", "+0%")))
    espeak_volume = int(100 * _volume_to_espeak(ton.get("volume", "+0%")))

    try:
        subprocess.run([
            "espeak-ng", "-v", "tr",
            "-p", str(espeak_pitch),
            "-s", str(espeak_speed),
            "-a", str(espeak_volume),
            "-w", str(ses_dosyasi), metin
        ], capture_output=True, timeout=30)
        print(f"[TTS] espeak-ng: {metin[:40]}... (pitch: {espeak_pitch})")
    except Exception as e:
        print(f"[TTS] espeak-ng de başarısız: {e}")
        _bos_wav_olustur(ses_dosyasi)

    return ses_dosyasi


def _pitch_to_espeak(pitch: str) -> int:
    """+10Hz → +5, -20Hz → -10"""
    try:
        hz = int(pitch.replace("Hz", "").replace("+", ""))
        return hz // 2
    except Exception:
        return 0


def _rate_to_espeak(rate: str) -> float:
    """+30% → 1.3, -15% → 0.85"""
    try:
        pct = int(rate.replace("%", "").replace("+", ""))
        return 1.0 + (pct / 100.0)
    except Exception:
        return 1.0


def _volume_to_espeak(volume: str) -> float:
    """+10% → 1.1, -20% → 0.8"""
    try:
        pct = int(volume.replace("%", "").replace("+", ""))
        return 1.0 + (pct / 100.0)
    except Exception:
        return 1.0


def _bos_wav_olustur(dosya: Path):
    import wave
    with wave.open(str(dosya), 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        wf.writeframes(b'\x00\x00' * 44100)


def _ses_suresi_hesapla(ses_dosyasi: Path) -> float:
    try:
        import wave
        with wave.open(str(ses_dosyasi), 'r') as wf:
            return wf.getnframes() / float(wf.getframerate())
    except Exception:
        return 3.0


def _sahte_zamanlama(metin: str, toplam_sure: float) -> list:
    """edge-tts yoksa kelime sayısına göre eşit dağıt."""
    kelimeler = metin.split()
    if not kelimeler:
        return []
    kelime_suresi = toplam_sure / len(kelimeler)
    return [{
        "kelime": k,
        "baslangic": round(i * kelime_suresi, 3),
        "bitis": round((i + 1) * kelime_suresi, 3)
    } for i, k in enumerate(kelimeler)]


def ses_efekti_uret(efekt_tipi: str, sure: float = 1.0) -> str:
    """Ses efekti üret (ofis uğultusu, alarm, sessizlik, dramatik)."""
    TTS_YOLU.mkdir(parents=True, exist_ok=True)
    efekt_dosyasi = TTS_YOLU / f"efekt_{efekt_tipi}.wav"

    if efekt_tipi == "ofis_ugultusu":
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"anoisesrc=color=brown:amplitude=0.15:duration={sure}",
            "-af", "lowpass=f=500,highpass=f=100",
            str(efekt_dosyasi)
        ], capture_output=True, timeout=15)
    elif efekt_tipi == "alarm":
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", f"sine=frequency=800:duration={sure}",
            "-af", "tremolo=f=5:d=0.5",
            str(efekt_dosyasi)
        ], capture_output=True, timeout=15)
    elif efekt_tipi == "dramatik_drum":
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "sine=frequency=60:duration=0.3",
            "-af", "afade=t=out:st=0:d=0.3,volume=0.8",
            str(efekt_dosyasi)
        ], capture_output=True, timeout=15)
    elif efekt_tipi == "sessizlik":
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=mono", "-t", str(sure),
            str(efekt_dosyasi)
        ], capture_output=True, timeout=15)
    else:
        _bos_wav_olustur(efekt_dosyasi)

    return str(efekt_dosyasi) if efekt_dosyasi.exists() else None


def senaryo_seslendir(senaryo_paketi: dict) -> dict:
    """
    Senaryo paketindeki diyalogları seslendirir.
    SADECE diyalog metnini okur — karakter isimleri OKUNMAZ.
    Her diyalog için edge-tts ile farklı ses tonu kullanılır.
    WordBoundary zaman damgaları toplanır.
    """
    senaryo = senaryo_paketi["senaryo"]
    dosya_adi_taslak = senaryo_paketi["dosya_adi"]
    ses_dosyalari = []
    diyaloglar = senaryo.get("diyaloglar", [])

    for sira, diyalog in enumerate(diyaloglar):
        metin = diyalog["metin"]
        ses_tipi = diyalog.get("ses", "normal")
        karakter = diyalog.get("karakter", "?")
        dosya_adi = f"{dosya_adi_taslak}_{sira:02d}"

        sonuc = metin_sese_cevir(metin, dosya_adi, ses_tipi)
        sonuc["karakter"] = karakter
        sonuc["sira"] = sira
        ses_dosyalari.append(sonuc)
        print(f"[TTS] [{karakter}] {metin} ({ses_tipi}, {sonuc['sure']:.1f}s, {len(sonuc['zamanlamalar'])} kelime)")

    senaryo_paketi["ses_dosyalari"] = ses_dosyalari
    return senaryo_paketi


if __name__ == "__main__":
    test = {
        "dosya_adi": "test_video",
        "senaryo": {
            "diyaloglar": [
                {"karakter": "KÖPEK", "metin": "Bugün çok yoruldum.", "ses": "yavas_bikkin"},
                {"karakter": "TOPLANTI", "metin": "Neden?", "ses": "robotik_koro"},
                {"karakter": "KÖPEK", "metin": "Var olmaktan.", "ses": "yavas_dramatik"},
                {"karakter": "TOPLANTI", "metin": "Normal.", "ses": "robotik_koro"}
            ]
        }
    }
    sonuc = senaryo_seslendir(test)
    for s in sonuc["ses_dosyalari"]:
        print(f"  [{s['karakter']}] {s['sure']:.1f}s — {len(s['zamanlamalar'])} kelime zaman damgası")
