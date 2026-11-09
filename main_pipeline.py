"""
BOBİ TV — Ana Üretim Pipeline v5.0
Arena AI tam üretim: senaryo + animasyon + ses + render + kapak
Fallback: eski gTTS + FFmpeg pipeline
"""
import sys
import os
import json
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from modules.telegram_notify import notify_error, send_message
from modules.youtube_upload import toplu_yukle

GUNLUK_HEDEF = int(os.environ.get("GUNLUK_HEDEF", "1"))
MOD = os.environ.get("MOD", "saatlik")
LOG_YOLU = Path("bobi_tv/logs")
ARSIV = Path("bobi_tv/archive/videos.json")


def log_yaz(mesaj: str, seviye: str = "INFO"):
    LOG_YOLU.mkdir(parents=True, exist_ok=True)
    tarih = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    zaman = datetime.now(timezone.utc).strftime("%H:%M:%S")
    satir = f"[{zaman}] [{seviye}] {mesaj}\n"
    with open(LOG_YOLU / f"{tarih}.log", "a", encoding="utf-8") as f:
        f.write(satir)
    print(satir.strip())


def bugunki_video_sayisi() -> int:
    bugun = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not ARSIV.exists():
        return 0
    try:
        return sum(1 for k in json.loads(ARSIV.read_text())
                   if k.get("tarih", "")[:10] == bugun)
    except Exception:
        return 0


def video_uret_arena(video_no: int) -> dict | None:
    """Arena AI ile tam video üret."""
    try:
        from modules.arena_uretici import arena_tam_uretim
        return arena_tam_uretim(video_no)
    except Exception as e:
        log_yaz(f"Arena üretim hatası: {e}", "ERROR")
        return None


def pipeline_calistir():
    baslangic = datetime.now(timezone.utc)
    saat = baslangic.strftime("%H:00")

    log_yaz(f"=== BOBİ TV {saat} — Arena AI Üretimi Başladı ===")

    # Günlük limit kontrolü
    bugunki = bugunki_video_sayisi()
    if bugunki >= 24 and MOD == "saatlik":
        log_yaz(f"Günlük limit: {bugunki}/24. Atlanıyor.")
        sys.exit(0)

    log_yaz(f"Bugün: {bugunki}/24 video. {GUNLUK_HEDEF} video üretilecek.")

    hazir_paketler = []
    hatalar = []

    for i in range(1, GUNLUK_HEDEF + 1):
        video_no = bugunki + i
        log_yaz(f"Video #{video_no} üretimi (Arena AI)...")

        paket = video_uret_arena(video_no)

        if paket:
            log_yaz(f"✅ Arena AI başarılı: {paket['baslik']}")
            hazir_paketler.append(paket)
        else:
            hata = f"Video #{video_no} — Arena AI başarısız oldu."
            log_yaz(hata, "ERROR")
            hatalar.append(hata)
            notify_error("arena", hata)

    # YouTube yükleme
    yayinlanan = 0
    if hazir_paketler:
        log_yaz(f"{len(hazir_paketler)} video yükleniyor...")
        try:
            sonuclar, yukle_hatalari = toplu_yukle(hazir_paketler)
            yayinlanan = len(sonuclar)
            hatalar.extend(yukle_hatalari)

            for sonuc in sonuclar:
                log_yaz(f"🚀 Yayınlandı: {sonuc['url']}")
                send_message(
                    f"🎬 <b>BOBİ TV {saat}</b>\n"
                    f"🎥 {sonuc['baslik'][:60]}\n"
                    f"🔗 {sonuc['url']}\n"
                    f"📊 Bugün: {bugunki + yayinlanan}/24"
                )
        except Exception as e:
            hata = f"YouTube yükleme hatası: {e}"
            log_yaz(hata, "ERROR")
            notify_error("youtube_upload", hata, kritik=True)
            hatalar.append(hata)

    sure_sn = int((datetime.now(timezone.utc) - baslangic).total_seconds())
    log_yaz(f"=== Tamamlandı: {yayinlanan}/{GUNLUK_HEDEF} video, {sure_sn}sn ===")

    sys.exit(0 if yayinlanan >= GUNLUK_HEDEF else 1)


if __name__ == "__main__":
    pipeline_calistir()
