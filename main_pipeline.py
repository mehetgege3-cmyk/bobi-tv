"""
BOBİ TV — Ana Otonom Üretim ve Yayın Pipeline v6.0 PRO
Mimari:
1. Akıllı Kuyruk (bobi_tv/queue/): Önceki çalışmada YouTube kotasına takılan senaryo/video varsa önce onu işler.
2. Birleşik v6.0 Üretim: Arena AI Yönetmen (veya v6.0 Loop Şablon) -> Ahmet+Emel Çift Ses TTS ->
   Vektör Kartlı & Karaoke Altyazılı & SFX+BGM (-14 LUFS) Render -> Montserrat Kapak -> ffprobe QC
3. Akıllı Yükleme: YouTube + Otomatik İlk Yorum + Özel Kapak.
   YouTube uploadLimitExceeded dönerse iş boşa gitmez; bobi_tv/queue/ altına kaydedilir.
"""
import os
import sys
import json
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from modules.arena_uretici import arena_tam_uretim
from modules.tts_engine import senaryo_seslendir
from modules.video_render import video_render
from modules.kapak_uret import kapak_uret
from modules.telegram_notify import notify_error, send_message
from modules.youtube_upload import toplu_yukle

GUNLUK_HEDEF = int(os.environ.get("GUNLUK_HEDEF", "1"))
GUNLUK_MAKS = int(os.environ.get("GUNLUK_MAKS", "4"))
MOD = os.environ.get("MOD", "pik_saat")
YUKLEME_ATLA = os.environ.get("YUKLEME_ATLA", "0") == "1"

LOG_YOLU = Path("bobi_tv/logs")
ARSIV = Path("bobi_tv/archive/videos.json")
KUYRUK_YOLU = Path("bobi_tv/queue")


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
        return sum(
            1 for k in json.loads(ARSIV.read_text(encoding="utf-8"))
            if k.get("tarih", "")[:10] == bugun
        )
    except Exception:
        return 0


def kuyruga_kaydet(paket: dict):
    """YouTube kotasına takılan paketin hafif senaryo verisini bobi_tv/queue/ altına yazar."""
    KUYRUK_YOLU.mkdir(parents=True, exist_ok=True)
    kayit = {
        "video_no": paket.get("video_no", 1),
        "dosya_adi": paket["dosya_adi"],
        "baslik": paket["baslik"],
        "aciklama": paket.get("aciklama", ""),
        "final_video": paket.get("final_video", ""),
        "kapak_dosyasi": paket.get("kapak_dosyasi", ""),
        "senaryo": paket["senaryo"],
        "kaynak": paket.get("kaynak", "kuyruk"),
        "olusturuldu": paket.get("olusturuldu", datetime.now().isoformat()),
    }
    hedef = KUYRUK_YOLU / f"{paket['dosya_adi']}.json"
    hedef.write_text(json.dumps(kayit, ensure_ascii=False, indent=2), encoding="utf-8")
    log_yaz(f"⏳ Kuyruğa kaydedildi: {hedef}")


def kuyruktan_paket_hazirla() -> tuple[dict | None, Path | None]:
    """Kuyrukta bekleyen paket varsa videosunu doğrular (yoksa hızla yeniden render alır)."""
    if not KUYRUK_YOLU.exists():
        return None, None
    bekleyenler = sorted(KUYRUK_YOLU.glob("*.json"))
    if not bekleyenler:
        return None, None

    dosya = bekleyenler[0]
    try:
        paket = json.loads(dosya.read_text(encoding="utf-8"))
        fv = paket.get("final_video", "")
        if not fv or not Path(fv).exists():
            log_yaz(f"🔄 Kuyruktaki senaryo yeniden render ediliyor: {paket['baslik']}")
            paket = senaryo_seslendir(paket)
            video_render(paket)
            kapak_uret(paket)
        return paket, dosya
    except Exception as e:
        log_yaz(f"Bozuk kuyruk kaydı silindi ({dosya.name}): {e}", "WARN")
        dosya.unlink(missing_ok=True)
        return None, None


def pipeline_calistir():
    baslangic = datetime.now(timezone.utc)
    saat = baslangic.strftime("%H:%M")

    log_yaz(f"=== BOBİ TV v6.0 PRO ({saat} UTC) Başladı ===")

    bugunki = bugunki_video_sayisi()
    if bugunki >= GUNLUK_MAKS and MOD == "saatlik":
        log_yaz(f"Günlük kalite tavanına ulaşıldı ({bugunki}/{GUNLUK_MAKS}). Atlanıyor.")
        sys.exit(0)

    log_yaz(f"Bugün yayınlanan: {bugunki}/{GUNLUK_MAKS} | Üretilecek hedef: {GUNLUK_HEDEF}")

    hazir_paketler = []
    kuyruk_kaynak_dosyalari = {}
    hatalar = []

    for i in range(1, GUNLUK_HEDEF + 1):
        video_no = bugunki + i

        # Önce kuyrukta kota bekleyen iş var mı bak
        kuyruk_paketi, kuyruk_dosya = kuyruktan_paket_hazirla()
        if kuyruk_paketi:
            log_yaz(f"📦 Kuyruktan hazırlandı: {kuyruk_paketi['baslik']}")
            hazir_paketler.append(kuyruk_paketi)
            if kuyruk_dosya:
                kuyruk_kaynak_dosyalari[kuyruk_paketi["dosya_adi"]] = kuyruk_dosya
            continue

        log_yaz(f"🎬 Video #{video_no} v6.0 Pro üretimi başlıyor...")
        paket = arena_tam_uretim(video_no)
        if paket and paket.get("final_video") and Path(paket["final_video"]).exists():
            sure_bilgi = paket.get("video_suresi", 0)
            log_yaz(f"✅ Pro Video hazır: {paket['baslik']} ({sure_bilgi}sn)")
            hazir_paketler.append(paket)
        else:
            hata = f"Video #{video_no} üretimi başarısız oldu."
            log_yaz(hata, "ERROR")
            hatalar.append(hata)
            notify_error("pro_render", hata)

    if YUKLEME_ATLA:
        log_yaz(f"YUKLEME_ATLA=1 aktif: {len(hazir_paketler)} video yerel olarak üretildi.")
        sys.exit(0 if hazir_paketler else 1)

    yayinlanan = 0
    kuyruga_alinan = 0

    if hazir_paketler:
        log_yaz(f"{len(hazir_paketler)} video YouTube'a yükleniyor...")
        try:
            sonuclar, yukle_hatalari, kota_paketleri = toplu_yukle(hazir_paketler)
            yayinlanan = len(sonuclar)
            hatalar.extend(yukle_hatalari)

            # Başarıyla yüklenenlerin kuyruk dosyasını temizle
            for sonuc in sonuclar:
                d_adi = sonuc["dosya_adi"]
                if d_adi in kuyruk_kaynak_dosyalari:
                    kuyruk_kaynak_dosyalari[d_adi].unlink(missing_ok=True)

                log_yaz(f"🚀 Yayınlandı: {sonuc['url']}")
                send_message(
                    f"🎬 <b>BOBİ TV v6.0 PRO</b>\n"
                    f"🎥 {sonuc['baslik'][:70]}\n"
                    f"🔗 {sonuc['url']}\n"
                    f"📊 Bugün: {bugunki + yayinlanan}/{GUNLUK_MAKS}"
                )

            # Kotaya takılanları kuyruğa kaydet (iş kaybolmaz!)
            for kp in kota_paketleri:
                kuyruga_kaydet(kp)
                kuyruga_alinan += 1

            if kuyruga_alinan > 0:
                send_message(
                    f"⏳ <b>BOBİ TV v6.0 PRO — Kuyruğa Alındı</b>\n"
                    f"🎥 {kota_paketleri[0]['baslik'][:65]}\n"
                    f"YouTube 24 saatlik yükleme limiti dolduğu için video kuyruğa kaydedildi; kota açıldığında otomatik yayınlanacak."
                )
        except Exception as e:
            hata = f"YouTube yükleme hatası: {e}"
            log_yaz(hata, "ERROR")
            notify_error("youtube_upload", hata, kritik=True)
            hatalar.append(hata)

    gecen_sn = int((datetime.now(timezone.utc) - baslangic).total_seconds())
    log_yaz(
        f"=== Tamamlandı: {yayinlanan} yayınlandı, {kuyruga_alinan} kuyruğa alındı ({gecen_sn}sn) ==="
    )

    basarili_toplam = yayinlanan + kuyruga_alinan
    sys.exit(0 if basarili_toplam >= GUNLUK_HEDEF else 1)


if __name__ == "__main__":
    pipeline_calistir()
