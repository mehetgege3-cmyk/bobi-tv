"""
BOBİ TV — Ana Üretim Pipeline v4.0
Saatlik 1 video modu. Günde 24 video hedefi.
Senaryo → Animasyon (Arena AI / PIL) → TTS → Render → YouTube
"""
import sys
import os
import json
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from modules.telegram_notify import (
    notify_start, notify_video_ready, notify_video_published,
    notify_daily_report, notify_error
)
from modules.scenario import gun_senaryolari_uret
from modules.tts_engine import senaryo_seslendir
from modules.video_render import video_render
from modules.kapak_uret import kapak_uret as kapak_uret_pil
from modules.youtube_upload import toplu_yukle

GUNLUK_HEDEF = int(os.environ.get("GUNLUK_HEDEF", "1"))
MOD = os.environ.get("MOD", "saatlik")  # saatlik veya gunluk
LOG_YOLU = Path("bobi_tv/logs")
ARSIV = Path("bobi_tv/archive/videos.json")


def log_yaz(mesaj: str, seviye: str = "INFO"):
    LOG_YOLU.mkdir(parents=True, exist_ok=True)
    tarih = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_dosyasi = LOG_YOLU / f"{tarih}.log"
    zaman = datetime.now(timezone.utc).strftime("%H:%M:%S")
    satir = f"[{zaman}] [{seviye}] {mesaj}\n"
    with open(log_dosyasi, "a", encoding="utf-8") as f:
        f.write(satir)
    print(satir.strip())


def bugunki_video_sayisi() -> int:
    """Bugün yayınlanan video sayısını döndür."""
    bugun = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not ARSIV.exists():
        return 0
    try:
        kayitlar = json.loads(ARSIV.read_text())
        return sum(1 for k in kayitlar if k.get("tarih", "")[:10] == bugun)
    except Exception:
        return 0


def animasyon_dene(paket: dict) -> bool:
    """
    Animasyon üretmeyi dene. Başarılıysa paket'e 'animasyon_video' ekler.
    Önce Arena AI, başarısız olursa PIL fallback.
    """
    try:
        from modules.animasyon import arena_animasyon_uret, basit_animasyon_uret

        # Katman 1: Arena AI animasyon
        video = arena_animasyon_uret(paket)
        if video:
            paket["animasyon_video"] = video
            log_yaz(f"Arena AI animasyon başarılı: {video}")
            return True

        # Katman 2: PIL kare-kare animasyon
        video = basit_animasyon_uret(paket)
        if video:
            paket["animasyon_video"] = video
            log_yaz(f"PIL animasyon başarılı: {video}")
            return True

    except Exception as e:
        log_yaz(f"Animasyon modülü hatası: {e}", "WARNING")

    log_yaz("Animasyon üretilemedi, gradient arka plan kullanılacak.", "WARNING")
    return False


def pipeline_calistir():
    """Ana üretim pipeline — saatlik 1 video."""
    baslangic = datetime.now(timezone.utc)
    saat = baslangic.strftime("%H:00")

    log_yaz(f"=== BOBİ TV {saat} Üretimi Başladı ===")

    # Günlük limit kontrolü
    bugunki = bugunki_video_sayisi()
    if bugunki >= 24 and os.environ.get("MOD") == "saatlik":
        log_yaz(f"Günlük 24 video hedefine ulaşıldı ({bugunki}/24). Atlanıyor.")
        sys.exit(0)

    notify_start(saat)

    uretilen = 0
    yayinlanan = 0
    hazir_paketler = []
    hatalar = []

    # 1. Senaryo üret
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

    # 2. Her senaryo için: Animasyon + TTS → Render
    for i, paket in enumerate(paketler, 1):
        dosya_adi = paket["dosya_adi"]
        baslik = paket["baslik"]
        log_yaz(f"Video #{i}/{uretilen}: {baslik}")

        try:
            # Animasyon dene (Arena AI / PIL)
            log_yaz(f"[#{i}] Animasyon üretimi...")
            animasyon_dene(paket)

            # TTS seslendirme
            log_yaz(f"[#{i}] TTS seslendirme...")
            paket = senaryo_seslendir(paket)

            # Video render (animasyon + ses + altyazı)
            log_yaz(f"[#{i}] Video render...")
            video_render(paket)

            # Kapak üret
            log_yaz(f"[#{i}] Kapak üretimi...")
            kapak = kapak_uret_pil(paket)
            if kapak:
                paket["kapak_dosyasi"] = kapak

            notify_video_ready(baslik, i, uretilen)
            hazir_paketler.append(paket)
            log_yaz(f"[#{i}] Hazır: {paket.get('final_video')}")

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
                    sonuc["baslik"], sonuc["video_id"], j, len(sonuclar)
                )
                log_yaz(f"Yayınlandı: {sonuc['url']}")

        except Exception as e:
            hata = f"YouTube yükleme hatası: {e}"
            log_yaz(hata, "ERROR")
            notify_error("youtube_upload.py", hata, kritik=True)
            hatalar.append(hata)
    else:
        log_yaz("Yüklenecek video yok.", "WARNING")

    # 4. Rapor
    sure_dk = int((datetime.now(timezone.utc) - baslangic).total_seconds() // 60)
    yeni_toplam = bugunki + yayinlanan
    log_yaz(f"=== Tamamlandı. {yayinlanan}/{GUNLUK_HEDEF} video, {sure_dk}dk. Bugün toplam: {yeni_toplam}/24 ===")

    # Sadece saatlik modda kısa bildirim (günlük raporun gürültüsünü azalt)
    if MOD == "saatlik" and yayinlanan > 0:
        try:
            from modules.telegram_notify import send_message
            send_message(
                f"🎬 <b>BOBİ TV {saat}</b> — {yayinlanan} video yayınlandı\n"
                f"📊 Bugün toplam: {yeni_toplam}/24"
            )
        except Exception:
            pass

    if MOD != "saatlik":
        notify_daily_report(GUNLUK_HEDEF, uretilen, yayinlanan, hatalar)

    sys.exit(0 if yayinlanan >= GUNLUK_HEDEF else 1)


if __name__ == "__main__":
    pipeline_calistir()
