"""
BOBİ TV — TTS Ses Üretim Modülü v2.0
Sadece diyalog metnini okur. Karakter isimleri OKUNMAZ.
Farklı ses tonları için pitch ve hız parametreleri kullanır.
Ses tasarımı: ofis uğultusu, alarm, dramatik sessizlik efektleri.
"""
import os
import json
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime


TTS_YOLU = Path("bobi_tv/production/tts")
PIPER_MODEL_YOLU = Path("bobi_tv/config/piper_models")

PIPER_MODELLER = [
    "tr_TR-dfki-medium",
    "tr_TR-fgl-medium"
]

# Ses tonu ayarları — her karakter tipi için pitch ve hız
SES_TONLARI = {
    "yavas_bikkin": {"pitch": -30, "speed": 0.85, "volume": 0.8},
    "yavas_dramatik": {"pitch": -40, "speed": 0.75, "volume": 0.9},
    "robotik_koro": {"pitch": 0, "speed": 1.3, "volume": 1.0},
    "robotik": {"pitch": 5, "speed": 1.2, "volume": 1.0},
    "alarm": {"pitch": 50, "speed": 1.5, "volume": 1.0},
    "uykulu": {"pitch": -20, "speed": 0.7, "volume": 0.6},
    "derin": {"pitch": -50, "speed": 0.9, "volume": 1.0},
    "derin_dramatik": {"pitch": -50, "speed": 0.7, "volume": 1.0},
    "normal": {"pitch": 0, "speed": 1.0, "volume": 1.0},
    "enerjik": {"pitch": 20, "speed": 1.3, "volume": 1.0},
    "bikeyn": {"pitch": -10, "speed": 0.95, "volume": 0.8},
    "bikeyn_dramatik": {"pitch": -20, "speed": 0.8, "volume": 0.9},
    "ciddi": {"pitch": -5, "speed": 0.95, "volume": 1.0},
    "kesin": {"pitch": 5, "speed": 1.1, "volume": 1.0},
    "soğuk": {"pitch": -15, "speed": 0.9, "volume": 0.7},
    "endiseli": {"pitch": 10, "speed": 1.1, "volume": 0.8},
    "suprized": {"pitch": 30, "speed": 1.2, "volume": 0.9},
    "sinirli": {"pitch": 15, "speed": 1.4, "volume": 1.0},
    "gururlu": {"pitch": 10, "speed": 1.0, "volume": 1.0},
    "dusunceli": {"pitch": -10, "speed": 0.85, "volume": 0.8},
    "umutlu": {"pitch": 15, "speed": 1.05, "volume": 0.9}
}

# Varsayılan ses tonu
VARSAYILAN_SES = {"pitch": 0, "speed": 1.0, "volume": 1.0}


def piper_kurulu_mu() -> bool:
    result = subprocess.run(["which", "piper"], capture_output=True)
    return result.returncode == 0


def piper_model_mevcut_mu(model_adi: str = None) -> bool:
    if model_adi is None:
        model_adi = PIPER_MODELLER[0]
    model_dosyasi = PIPER_MODEL_YOLU / f"{model_adi}.onnx"
    return model_dosyasi.exists() and model_dosyasi.stat().st_size > 1000


def ses_tonu_al(ses_tipi: str) -> dict:
    return SES_TONLARI.get(ses_tipi, VARSAYILAN_SES)


def metin_sese_cevir(metin: str, dosya_adi: str, ses_tipi: str = "normal") -> dict:
    """
    Metni sese çevirir. Karakter ismi OKUNMAZ.
    Ses tonuna göre pitch ve hız ayarlanır.
    Döner: {ses_dosyasi, zamanlamalar, sure, metin}
    """
    TTS_YOLU.mkdir(parents=True, exist_ok=True)
    ses_dosyasi = TTS_YOLU / f"{dosya_adi}.wav"
    ton = ses_tonu_al(ses_tipi)

    model_adi = PIPER_MODELLER[0]
    model_dosyasi = PIPER_MODEL_YOLU / f"{model_adi}.onnx"

    # Piper ile ses üret
    if piper_kurulu_mu() and piper_model_mevcut_mu(model_adi):
        try:
            cmd = [
                "piper",
                "--model", str(model_dosyasi),
                "--output_file", str(ses_dosyasi)
            ]
            # Piper sentence_speed parametresi
            result = subprocess.run(
                cmd,
                input=metin.encode("utf-8"),
                capture_output=True,
                timeout=60
            )
            if result.returncode != 0:
                raise RuntimeError(f"Piper hata: {result.stderr.decode()}")

            # Pitch ayarı için ffmpeg post-process
            if ton["pitch"] != 0 or ton["speed"] != 1.0:
                tmp_file = str(ses_dosyasi) + ".tmp.wav"
                subprocess.run([
                    "ffmpeg", "-y", "-i", str(ses_dosyasi),
                    "-af", f"asetrate=44100*{ton['speed']},aresample=44100,atempo={1.0/ton['speed'] if ton['speed'] != 1.0 else 1.0}",
                    "-af", f"volume={ton['volume']}",
                    str(tmp_file)
                ], capture_output=True, timeout=30)
                import shutil
                shutil.move(tmp_file, str(ses_dosyasi))

            print(f"[TTS] Piper: {metin[:40]}... (ton: {ses_tipi})")
        except Exception as e:
            print(f"[TTS] Piper hatası, espeak fallback: {e}")
            ses_dosyasi = _espeak_fallback(metin, dosya_adi, ton)
    else:
        if not piper_kurulu_mu():
            print(f"[TTS] Piper binary yok, espeak-ng kullanılıyor.")
        elif not piper_model_mevcut_mu(model_adi):
            print(f"[TTS] Piper model yok ({model_adi}), espeak-ng kullanılıyor.")
        ses_dosyasi = _espeak_fallback(metin, dosya_adi, ton)

    sure = _ses_suresi_hesapla(ses_dosyasi)
    zamanlamalar = _zamanlama_uret(metin, sure)

    return {
        "ses_dosyasi": str(ses_dosyasi),
        "zamanlamalar": zamanlamalar,
        "sure": sure,
        "metin": metin,
        "ses_tipi": ses_tipi
    }


def _espeak_fallback(metin: str, dosya_adi: str, ton: dict = None) -> Path:
    """espeak-ng ile Türkçe ses üret (fallback). Pitch ve hız uygula."""
    TTS_YOLU.mkdir(parents=True, exist_ok=True)
    ses_dosyasi = TTS_YOLU / f"{dosya_adi}.wav"

    if ton is None:
        ton = VARSAYILAN_SES

    # espeak pitch: 0-99 (varsayılan 50)
    espeak_pitch = max(1, min(99, 50 + ton["pitch"]))
    # espeak speed: kelimeler/dakika (varsayılan 175)
    espeak_speed = int(175 * ton["speed"])
    # espeak volume: 0-200 (varsayılan 100)
    espeak_volume = int(100 * ton["volume"])

    try:
        subprocess.run([
            "espeak-ng",
            "-v", "tr",
            "-p", str(espeak_pitch),
            "-s", str(espeak_speed),
            "-a", str(espeak_volume),
            "-w", str(ses_dosyasi),
            metin
        ], capture_output=True, timeout=30)
        print(f"[TTS] espeak-ng: {metin[:40]}... (pitch: {espeak_pitch}, speed: {espeak_speed})")
    except Exception as e:
        print(f"[TTS] espeak-ng de başarısız: {e}")
        _bos_wav_olustur(ses_dosyasi)

    return ses_dosyasi


def _bos_wav_olustur(dosya: Path):
    """44100Hz, mono, 1 saniyelik sessiz WAV oluştur."""
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
            frames = wf.getnframes()
            rate = wf.getframerate()
            return frames / float(rate)
    except Exception:
        return 3.0


def _zamanlama_uret(metin: str, toplam_sure: float) -> list:
    """Kelime bazlı zamanlama üret."""
    kelimeler = metin.split()
    if not kelimeler:
        return []
    kelime_suresi = toplam_sure / len(kelimeler)
    zamanlamalar = []
    for i, kelime in enumerate(kelimeler):
        baslangic = i * kelime_suresi
        bitis = baslangic + kelime_suresi
        zamanlamalar.append({
            "kelime": kelime,
            "baslangic": round(baslangic, 3),
            "bitis": round(bitis, 3)
        })
    return zamanlamalar


def ses_efekti_uret(efekt_tipi: str, sure: float = 1.0) -> str:
    """
    Ses efekti üret (ofis uğultusu, alarm, sessizlik).
    Döner: ses dosyası yolu
    """
    TTS_YOLU.mkdir(parents=True, exist_ok=True)
    efekt_dosyasi = TTS_YOLU / f"efekt_{efekt_tipi}.wav"

    if efekt_tipi == "ofis_ugultusu":
        # Beyaz gürültü + düşük frekans = ofis uğultusu
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"anoisesrc=color=brown:amplitude=0.15:duration={sure}",
            "-af", "lowpass=f=500,highpass=f=100",
            str(efekt_dosyasi)
        ], capture_output=True, timeout=15)
    elif efekt_tipi == "alarm":
        # Alarm sesi — yüksek frekans tekrar
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"sine=frequency=800:duration={sure}",
            "-af", "tremolo=f=5:d=0.5",
            str(efekt_dosyasi)
        ], capture_output=True, timeout=15)
    elif efekt_tipi == "sessizlik":
        # Sessizlik
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"anullsrc=r=44100:cl=mono",
            "-t", str(sure),
            str(efekt_dosyasi)
        ], capture_output=True, timeout=15)
    elif efekt_tipi == "dramatik_drum":
        # Dramatik davul vuruşu
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", "sine=frequency=60:duration=0.3",
            "-af", "afade=t=out:st=0:d=0.3,volume=0.8",
            str(efekt_dosyasi)
        ], capture_output=True, timeout=15)
    else:
        _bos_wav_olustur(efekt_dosyasi)

    return str(efekt_dosyasi) if efekt_dosyasi.exists() else None


def senaryo_seslendir(senaryo_paketi: dict) -> dict:
    """
    Senaryo paketindeki diyalogları seslendirir.
    SADECE diyalog metnini okur — karakter isimleri OKUNMAZ.
    Ses tonu her diyalog için ayrı ayarlanır.
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
        print(f"[TTS] [{karakter}] {metin} ({ses_tipi}, {sonuc['sure']:.1f}s)")

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
    print(f"\nToplam {len(sonuc['ses_dosyalari'])} ses dosyası üretildi.")
