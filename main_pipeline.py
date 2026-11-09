"""
BOBİ TV — Ana Üretim Pipeline
Senaryo → TTS → Render → YouTube yükleme zincirini yönetir.
GitHub Actions tarafından günlük çalıştırılır.
"""
import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Modül yolunu ekle
sys.path.insert(0, str(Path(__file__).parent))

from modules.telegram_notify import (
    notify_start, notify_video_ready, notify_video_published,
    notify_daily_report, notify_error, notify_production_start_approval
)
from modules.scenario import gun_senaryolari_uret
from modules.tts_engine import senaryo_seslendir
from modules.video_render import video_render
from modules.kapak_uret import kapak_uret as kapak_uret_pil
from modules.youtube_upload import toplu_yukle

GUNLUK_HEDEF = int(os.environ.get("GUNLUK_HEDEF", "5"))
LOG_YOLU = Path("bobi_tv/logs")


def log_yaz(mesaj: str, seviye: str = "INFO"):
    LOG_YOLU.mkdir(parents=True, exist_ok=True)
    tarih = datetime.now().strftime("%Y-%m-%d")
    log_dosyasi = LOG_YOLU / f"{tarih}.log"
    zaman = datetime.now().strftime("%H:%M:%S")
    satir = f"[{zaman}] [{seviye}] {mesaj}\n"
    with open(log_dosyasi, "a", encoding="utf-8") as f:
        f.write(satir)
    print(satir.strip())


def pipeline_calistir():
    """Ana üretim pipeline'ını çalıştır."""
    baslangic = datetime.now()
    log_yaz("=== BOBİ TV Günlük Üretim Başladı ===")
    notify_start()

    uretilen = 0
    yayinlanan = 0
    hazir_paketler = []
    hatalar = []

    # 1. Senaryo üretimi
    log_yaz(f"Senaryo üretimi başlıyor. Hedef: {GUNLUK_HEDEF}")
    try:
        paketler = gun_senaryolari_uret(GUNLUK_HEDEF)
        uretilen = len(paketler)
        log_yaz(f"{uretilen} senaryo üretildi.")
    except Exception as e:
        hata = f"Senaryo üretim hatası: {e}"
        log_yaz(hata, "ERROR")
        notify_error("scenario.py", hata, kritik=True)
        notify_daily_report(GUNLUK_HEDEF, 0, 0, [hata])
        sys.exit(1)

    # 2. Her senaryo için TTS → Render
    for i, paket in enumerate(paketler, 1):
        dosya_adi = paket["dosya_adi"]
        baslik = paket["baslik"]
        log_yaz(f"Video #{i}/{uretilen}: {baslik}")

        try:
            # TTS
            log_yaz(f"[#{i}] TTS seslendirme...")
            paket = senaryo_seslendir(paket)

            # Render
            log_yaz(f"[#{i}] Video render...")
            video_render(paket)

            # Kapak üret (PIL tabanlı, infu projesinden transfer)
            log_yaz(f"[#{i}] Kapak üretimi...")
            kapak = kapak_uret_pil(paket)
            if kapak:
                paket["kapak_dosyasi"] = kapak

            notify_video_ready(baslik, i, uretilen)
            hazir_paketler.append(paket)
            log_yaz(f"[#{i}] Video hazır: {paket.get('final_video')}")

        except Exception as e:
            hata = f"Video #{i} ({dosya_adi}) üretim hatası: {e}"
            log_yaz(hata, "ERROR")
            notify_error("render", hata)
            hatalar.append(hata)

    # 3. YouTube yükleme
    if hazir_paketler:
        log_yaz(f"{len(hazir_paketler)} video YouTube'a yükleniyor...")
        try:
            sonuclar, yukle_hatalari = toplu_yukle(hazir_paketler)
            yayinlanan = len(sonuclar)
            hatalar.extend(yukle_hatalari)

            for j, sonuc in enumerate(sonuclar, 1):
                notify_video_published(
                    sonuc["baslik"],
                    sonuc["video_id"],
                    j, len(sonuclar)
                )
                log_yaz(f"Yayınlandı: {sonuc['url']}")

        except Exception as e:
            hata = f"YouTube yükleme hatası: {e}"
            log_yaz(hata, "ERROR")
            notify_error("youtube_upload.py", hata, kritik=True)
            hatalar.append(hata)
    else:
        log_yaz("Yüklenecek video yok.", "WARNING")

    # 4. Günlük rapor
    sure = (datetime.now() - baslangic).seconds // 60
    log_yaz(f"=== Pipeline tamamlandı. {yayinlanan}/{GUNLUK_HEDEF} video. Süre: {sure}dk ===")
    notify_daily_report(GUNLUK_HEDEF, uretilen, yayinlanan, hatalar)

    # Exit kodu: hedef tutmadıysa 1
    sys.exit(0 if yayinlanan >= GUNLUK_HEDEF else 1)


if __name__ == "__main__":
    pipeline_calistir()
