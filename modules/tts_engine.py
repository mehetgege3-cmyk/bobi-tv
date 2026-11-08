"""
BOBİ TV — TTS Ses Üretim Modülü
Piper TTS ile Türkçe karakter sesleri ve altyazı zamanlamaları üretir.
Ses kalitesine göre en iyi ücretsiz TTS motorunu seçer.
"""
import os
import json
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime


TTS_YOLU = Path("bobi_tv/production/tts")
PIPER_MODEL_YOLU = Path("bobi_tv/config/piper_models")

# Türkçe Piper model adayları (kalite sırasıyla)
PIPER_MODELLER = [
    "tr_TR-dfki-medium",
    "tr_TR-fgl-medium",
]


def piper_kurulu_mu() -> bool:
    """Piper TTS kurulu mu kontrol et."""
    result = subprocess.run(["which", "piper"], capture_output=True)
    return result.returncode == 0


def piper_model_mevcut_mu(model_adi: str = None) -> bool:
    """Piper Türkçe model dosyası mevcut mu kontrol et."""
    if model_adi is None:
        model_adi = PIPER_MODELLER[0]
    model_dosyasi = PIPER_MODEL_YOLU / f"{model_adi}.onnx"
    return model_dosyasi.exists() and model_dosyasi.stat().st_size > 1000


def piper_model_indir(model_adi: str) -> bool:
    """Piper modelini indir."""
    PIPER_MODEL_YOLU.mkdir(parents=True, exist_ok=True)
    model_dosyasi = PIPER_MODEL_YOLU / f"{model_adi}.onnx"

    if model_dosyasi.exists():
        return True

    url = f"https://huggingface.co/rhasspy/piper-voices/resolve/main/tr/tr_TR/{model_adi.split('-')[2]}/{model_adi.split('-')[3]}/{model_adi}.onnx"
    config_url = f"{url}.json"

    try:
        import requests
        # Model indir
        resp = requests.get(url, timeout=120, stream=True)
        if resp.status_code != 200:
            return False
        with open(model_dosyasi, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        # Config indir
        resp2 = requests.get(config_url, timeout=30)
        if resp2.status_code == 200:
            with open(str(model_dosyasi) + ".json", "wb") as f:
                f.write(resp2.content)

        print(f"[TTS] Model indirildi: {model_adi}")
        return True
    except Exception as e:
        print(f"[TTS] Model indirme hatası: {e}")
        return False


def metin_sese_cevir(metin: str, dosya_adi: str, model_adi: str = None) -> dict:
    """
    Metni sese çevirir.
    Döner: {ses_dosyasi, zamanlamalar, sure}
    """
    TTS_YOLU.mkdir(parents=True, exist_ok=True)
    ses_dosyasi = TTS_YOLU / f"{dosya_adi}.wav"

    if not model_adi:
        model_adi = PIPER_MODELLER[0]

    model_dosyasi = PIPER_MODEL_YOLU / f"{model_adi}.onnx"

    # Piper ile ses üret
    if piper_kurulu_mu() and piper_model_mevcut_mu(model_adi):
        try:
            result = subprocess.run(
                ["piper", "--model", str(model_dosyasi), "--output_file", str(ses_dosyasi)],
                input=metin.encode("utf-8"),
                capture_output=True,
                timeout=60
            )
            if result.returncode != 0:
                raise RuntimeError(f"Piper hata: {result.stderr.decode()}")
            print(f"[TTS] Piper ile ses üretildi: {model_adi}")
        except Exception as e:
            print(f"[TTS] Piper hatası, fallback: {e}")
            ses_dosyasi = _espeak_fallback(metin, dosya_adi)
    else:
        if not piper_kurulu_mu():
            print(f"[TTS] Piper binary bulunamadı, espeak-ng kullanılıyor.")
        elif not piper_model_mevcut_mu(model_adi):
            print(f"[TTS] Piper model bulunamadı ({model_adi}), espeak-ng kullanılıyor.")
        ses_dosyasi = _espeak_fallback(metin, dosya_adi)

    # Süre ve zamanlama hesapla
    sure = _ses_suresi_hesapla(ses_dosyasi)
    zamanlamalar = _zamanlama_uret(metin, sure)

    return {
        "ses_dosyasi": str(ses_dosyasi),
        "zamanlamalar": zamanlamalar,
        "sure": sure,
        "metin": metin,
    }


def _espeak_fallback(metin: str, dosya_adi: str) -> Path:
    """espeak-ng ile Türkçe ses üret (fallback)."""
    TTS_YOLU.mkdir(parents=True, exist_ok=True)
    ses_dosyasi = TTS_YOLU / f"{dosya_adi}.wav"

    try:
        subprocess.run(
            ["espeak-ng", "-v", "tr", "-w", str(ses_dosyasi), metin],
            capture_output=True, timeout=30
        )
    except Exception as e:
        print(f"[TTS] espeak-ng de başarısız: {e}")
        # Boş wav oluştur (pipeline devam etsin)
        _bos_wav_olustur(ses_dosyasi)

    return ses_dosyasi


def _bos_wav_olustur(dosya: Path):
    """44100Hz, mono, 1 saniyelik sessiz WAV oluştur."""
    import struct
    import wave
    with wave.open(str(dosya), 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        wf.writeframes(b'\x00\x00' * 44100)


def _ses_suresi_hesapla(ses_dosyasi: Path) -> float:
    """WAV dosyasının süresini hesapla (saniye)."""
    try:
        import wave
        with wave.open(str(ses_dosyasi), 'r') as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            return frames / float(rate)
    except Exception:
        return 5.0  # Varsayılan


def _zamanlama_uret(metin: str, toplam_sure: float) -> list:
    """
    TTS çıktısından kelime bazlı zamanlama üret.
    Basit: kelimeleri eşit aralıklara dağıt.
    Piper'ın JSON çıktısı varsa ondan al (gelecek geliştirme).
    """
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
            "bitis": round(bitis, 3),
        })

    return zamanlamalar


def senaryo_seslendir(senaryo_paketi: dict) -> dict:
    """
    Senaryo paketindeki tüm diyalogları seslendirir.
    Her satır için ayrı ses dosyası üretir.
    """
    senaryo = senaryo_paketi["senaryo"]
    dosya_adi_taslak = senaryo_paketi["dosya_adi"]
    ses_dosyalari = []

    satirlar = [
        ("acilis", senaryo.get("acilis", "")),
        ("gelisme", senaryo.get("gelisme", "")),
        ("punchline", senaryo.get("punchline", "")),
    ]

    for sira, (bolum, metin) in enumerate(satirlar):
        if not metin.strip():
            continue
        dosya_adi = f"{dosya_adi_taslak}_{sira:02d}_{bolum}"
        sonuc = metin_sese_cevir(metin, dosya_adi)
        sonuc["bolum"] = bolum
        sonuc["sira"] = sira
        ses_dosyalari.append(sonuc)
        print(f"[TTS] {bolum} seslendirme tamamlandı ({sonuc['sure']:.1f}s)")

    senaryo_paketi["ses_dosyalari"] = ses_dosyalari
    return senaryo_paketi


if __name__ == "__main__":
    # Test
    test = {
        "dosya_adi": "test_video",
        "senaryo": {
            "acilis": "Bir bar. Adam içkisini dikeyken içiyor.",
            "gelisme": "Barmen sorar: Neden öyle içiyorsunuz? Adam: Doktor ayakta dur dedi.",
            "punchline": "Barmen hesabı getirir.",
        }
    }
    sonuc = senaryo_seslendir(test)
    print(f"Toplam {len(sonuc['ses_dosyalari'])} ses dosyası üretildi.")
