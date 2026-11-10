"""
BOBİ TV — Otonom Üretim, Dönen Konular, En Az 15sn ve 15 Dakika Pipeline v6.4 PRO
Mimari:
1. Otomatik Performans Temizliği: Kanalda yayınlanalı >= 60 dk (1 saat) olmuş ve < 100 görüntüleme
   almış videoları YouTube Data API v3 ile otomatik siler (kanal algoritmasını yüksek izlenmeli tutar).
2. Akıllı Kuyruk (bobi_tv/queue/): Önceki çalışmada YouTube kotasına takılan senaryo/video varsa önce onu işler.
3. Birleşik v6.3 Üretim: Dönen kategori havuzu -> gerçek TTS süresi <15sn ise uzat -> Ahmet+Emel Çift Ses TTS ->
   1. Kareye (Frame 0) Profesyonel VS/Clash Kapak Gömme + İlk Kareden Kapak Seçme ->
   Vektör Kartlı & Karaoke Altyazılı & SFX+BGM (-14 LUFS) Render -> ffprobe QC
4. Kota Takibi: YouTube kotası dolduğunda state dosyasına yazar, workflow'u başarısız işaretler.
5. Her Saatte 1 Video Isındırma: YouTube + Otomatik İlk Yorum + 1. Kare Özel Kapak.
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
from modules.youtube_upload import (
    dusuk_izlenmeli_videolari_temizle,
    toplu_yukle,
    zaten_yuklendi_mi,
)
from modules.kota_state import kota_state_yaz
from modules.kota_kapisi import kota_dolu_cikis_kodu
from modules.ayar_katalogu import etkin_gunluk_maks

GUNLUK_HEDEF = int(os.environ.get("GUNLUK_HEDEF", "1"))
# TODO 10: GUNLUK_MAKS tavan savunması — env/state ne derse desin etkin değer ≤ 6
# (10000 birim / 1600 birim = 6 yükleme). Katalog varsayılanı 6'dır; 96 gibi eski
# sabitler artık köprüden gelmez, yine de gelen aşırı değer UYARIYLA kırpılır.
GUNLUK_MAKS = etkin_gunluk_maks(os.environ.get("GUNLUK_MAKS", "6"))
MOD = os.environ.get("MOD", "isindirma_saatlik")
YUKLEME_ATLA = os.environ.get("YUKLEME_ATLA", "0") == "1"
# TODO 10: kota dolunca davranış — sessiz_dur (varsayılan) → exit 0,
# hata → exit 1. Değer ayarlar.json'dan köprüyle gelir.
KOTA_DOLU_DAVRANIS = os.environ.get("KOTA_DOLU_DAVRANIS", "sessiz_dur")

OTOMATIK_SIL_AKTIF = os.environ.get("OTOMATIK_SIL_AKTIF", "1") == "1"
# Silme eşiği TEK KAYNAK (burada). hourly_production.yml artık override
# etmez; env var isteğe bağlı geçersiz kılma için kullanılabilir.
# Yaş eşiği 24 saat (1440 dk); izlenme eşiği 100 korunur.
MIN_IZLENME_ESIGI = int(os.environ.get("MIN_IZLENME_ESIGI", "100"))
# 2026-11-11 kullanıcı kuralı: 1 saatte 100 izlenme almayan video silinir.
IZLENME_KONTROL_DK = int(os.environ.get("IZLENME_KONTROL_DK", "60"))

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
    """Yüklenemeyen paketi STOĞA alır (kota / geçici / kalıcı sebep ayrımıyla).

    Kullanıcı kararı (2026-11-11): "yüklesin, başarısız olursa sebebine bakalım;
    eğer gerçekten kotaysa stok olsun." Stok kaydı MP4'ü (final_video) de saklar,
    böylece kota açıldığında YENİDEN RENDER alınmaz — sadece yükleme yapılır.
    """
    KUYRUK_YOLU.mkdir(parents=True, exist_ok=True)
    sebep = paket.get("stok_sebep") or "kota"
    mevcut = KUYRUK_YOLU / f"{paket['dosya_adi']}.json"
    deneme = 0
    if mevcut.exists():
        # Stokta bekleyen kayıt varsa deneme sayacını koru (tekrar tekrar ekleme).
        with suppress(Exception):
            deneme = int(json.loads(mevcut.read_text(encoding="utf-8")).get("deneme", 0))
    kayit = {
        "stok_sebep": sebep,
        "deneme": deneme,
        "son_hata": paket.get("son_hata", ""),
        "video_no": paket.get("video_no", 1),
        "dosya_adi": paket["dosya_adi"],
        "baslik": paket["baslik"],
        "aciklama": paket.get("aciklama", ""),
        "final_video": paket.get("final_video", ""),
        "kapak_dosyasi": paket.get("kapak_dosyasi") or paket.get("kapak_yolu", ""),
        "senaryo": paket["senaryo"],
        "kaynak": paket.get("kaynak", "kuyruk"),
        "olusturuldu": paket.get("olusturuldu", datetime.now(timezone.utc).isoformat()),
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

        # TODO 4b: bayat kuyruk koruması — paket zaten yayınlandıysa (kota dolarken
        # kuyruğa alınmış ve sonraki koşuda yüklenmiş ama silme commit'lenmemişse)
        # yeniden RENDER EDİLMEZ ve tekrar "Yayınlandı" denmez: kayıt tüketilir,
        # yeni üretim kotasını bloklamaz.
        mevcut_video_id = zaten_yuklendi_mi(paket.get("dosya_adi", ""))
        if mevcut_video_id:
            log_yaz(
                f"♻️ Kuyruktaki paket zaten yayında ({mevcut_video_id}) — bayat kayıt "
                f"tüketildi, render atlandı: {paket.get('dosya_adi', '?')}"
            )
            dosya.unlink(missing_ok=True)
            return None, None

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

    log_yaz(f"=== BOBİ TV v6.3 PRO ({saat} UTC) Başladı ===")

    # 1. ADIM: 1 saat (60 dk) içinde 100 görüntüleme almayan videoları otomatik temizle
    if not YUKLEME_ATLA and OTOMATIK_SIL_AKTIF:
        log_yaz(
            f"🔍 Performans kontrolü: {IZLENME_KONTROL_DK} dk sonunda "
            f"<{MIN_IZLENME_ESIGI} görüntüleme alan videolar denetleniyor..."
        )
        silinen_videolar = dusuk_izlenmeli_videolari_temizle(
            min_izlenme=MIN_IZLENME_ESIGI,
            kontrol_suresi_dk=IZLENME_KONTROL_DK,
        )
        for sv in silinen_videolar:
            log_yaz(
                f"🗑️ Otomatik silindi: {sv['video_id']} | '{sv['baslik'][:45]}' "
                f"({sv['yas_dk']} dk -> {sv['izlenme']} görüntüleme < {MIN_IZLENME_ESIGI})"
            )
            send_message(
                f"🗑️ <b>BOBİ TV — Düşük Performanslı Video Silindi</b>\n"
                f"🎥 {sv['baslik'][:65]}\n"
                f"👁️ Görüntüleme: {sv['izlenme']} (Hedef: {MIN_IZLENME_ESIGI}+)\n"
                f"⏱️ Geçen Süre: {sv['yas_dk']:.0f} dk"
            )

    bugunki = bugunki_video_sayisi()
    if bugunki >= GUNLUK_MAKS:
        log_yaz(f"Günlük üretim tavanına ulaşıldı ({bugunki}/{GUNLUK_MAKS}). Atlanıyor.")
        sys.exit(0)

    # ---------------------------------------------------------------------
    # 15 DAKİKA KADANSI + GÜNLÜK HEDEF DÜZELTMESİ (2026-11-11)
    #
    # ESKİ HATA: `for i in range(1, GUNLUK_HEDEF + 1)` — GUNLUK_HEDEF KOŞU BAŞINA
    # video sayısıydı. 15 dakikalık kadans günde 96 koşu yapar; hedef 4 kalsaydı
    # günde 384 video DENENİRDİ (kota 6'da keser, 378 koşu boşa giderdi).
    #
    # YENİ SÖZLEŞME: GUNLUK_HEDEF = GÜNLÜK TOPLAM hedef (kalan = hedef - bugün).
    # Bu turda üretilecek sayı = min(kalan_hedef, kota_tavanı - bugün).
    # Böylece kadans sıkılaşsa bile günlük yükleme sayısı DEĞİŞMEZ — yalnız
    # deneme sıklığı artar ve ilk fırsatta kota doldurulur.
    # ---------------------------------------------------------------------
    kalan_hedef = max(0, GUNLUK_HEDEF - bugunki)
    kalan_kota = max(0, GUNLUK_MAKS - bugunki)
    bu_tur = min(kalan_hedef, kalan_kota)

    log_yaz(
        f"Bugün üretilen: {bugunki}/{GUNLUK_MAKS} | "
        f"Günlük hedef: {GUNLUK_HEDEF} (kalan {kalan_hedef}) | "
        f"Bu turda: {bu_tur}"
    )
    if bu_tur == 0:
        if kalan_hedef == 0:
            log_yaz(f"✅ Günlük hedef tamamlandı ({bugunki}/{GUNLUK_HEDEF}). Bu tur no-op.")
        else:
            log_yaz(f"🚫 Kota tavanı dolu ({bugunki}/{GUNLUK_MAKS}). Bu tur no-op.")
        sys.exit(0)

    hazir_paketler = []
    kuyruk_kaynak_dosyalari = {}
    hatalar = []

    for i in range(1, bu_tur + 1):
        video_no = bugunki + i

        # Önce kuyrukta kota bekleyen iş var mı bak
        kuyruk_paketi, kuyruk_dosya = kuyruktan_paket_hazirla()
        if kuyruk_paketi:
            log_yaz(f"📦 Kuyruktan hazırlandı: {kuyruk_paketi['baslik']}")
            hazir_paketler.append(kuyruk_paketi)
            if kuyruk_dosya:
                kuyruk_kaynak_dosyalari[kuyruk_paketi["dosya_adi"]] = kuyruk_dosya
            continue

        log_yaz(f"🎬 Video #{video_no} v6.3 Pro konu rotasyonu + 15sn alt sınır kontrolüyle başlıyor...")
        paket = arena_tam_uretim(video_no)
        if paket and paket.get("final_video") and Path(paket["final_video"]).exists():
            sure_bilgi = paket.get("video_suresi", 0)
            log_yaz(f"✅ Pro Video + 1. Kare Kapak hazır: {paket['baslik']} ({sure_bilgi}sn)")
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
    yeni_kuyruga_alinan = 0

    if hazir_paketler:
        log_yaz(f"{len(hazir_paketler)} video YouTube'a yükleniyor...")
        try:
            sonuclar, yukle_hatalari, kota_paketleri = toplu_yukle(hazir_paketler)
            yayinlanan = len(sonuclar)
            hatalar.extend(yukle_hatalari)

            for sonuc in sonuclar:
                d_adi = sonuc["dosya_adi"]
                if d_adi in kuyruk_kaynak_dosyalari:
                    kuyruk_kaynak_dosyalari[d_adi].unlink(missing_ok=True)

                log_yaz(f"🚀 Yayınlandı: {sonuc['url']}")
                send_message(
                    f"🎬 <b>BOBİ TV v6.3 PRO (Dönen Konu + 15dk)</b>\n"
                    f"🎥 {sonuc['baslik'][:70]}\n"
                    f"🖼️ 1. Kare VS Kapak + Otomatik Yorum Aktif\n"
                    f"🔗 {sonuc['url']}"
                )

            for kp in kota_paketleri:
                d_adi = kp["dosya_adi"]
                if d_adi not in kuyruk_kaynak_dosyalari:
                    yeni_kuyruga_alinan += 1
                kuyruga_kaydet(kp)
                kuyruga_alinan += 1

            if yeni_kuyruga_alinan > 0:
                send_message(
                    f"⏳ <b>BOBİ TV v6.4 PRO — Kuyruğa Alındı</b>\n"
                    f"🎥 {kota_paketleri[0]['baslik'][:65]}\n"
                    f"YouTube yükleme limiti dolduğu için video kuyruğa kaydedildi; kota açıldığında otomatik yayınlanacak."
                )
                # Kota doldu işaretle
                kota_state_yaz(doldu=True, kalan_saat=24, video_sayisi=yayinlanan)
                log_yaz("⚠️ YouTube günlük kota doldu!", "WARN")
        except Exception as e:
            hata = f"YouTube yükleme hatası: {e}"
            log_yaz(hata, "ERROR")
            notify_error("youtube_upload", hata, kritik=True)
            hatalar.append(hata)

    gecen_sn = int((datetime.now(timezone.utc) - baslangic).total_seconds())
    log_yaz(
        f"=== Tamamlandı: {yayinlanan} yayınlandı, {kuyruga_alinan} kuyrukta ({gecen_sn}sn) ==="
    )

    # Kota kontrolü
    if kuyruga_alinan > 0 and yayinlanan == 0:
        log_yaz("❌ YouTube kotası dolu, hiçbir video yüklenemedi!", "ERROR")
        kota_state_yaz(doldu=True, kalan_saat=24, video_sayisi=0)
        # Telegram bildirimi
        send_message(
            f"🚫 <b>BOBİ TV — YouTube Kota Dolu</b>\n"
            f"Bugün hiç video yüklenemedi, {kuyruga_alinan} video kuyrukta bekliyor.\n"
            f"Kota açılana kadar yeni üretim duraklatılacak."
        )
        sys.exit(kota_dolu_cikis_kodu(KOTA_DOLU_DAVRANIS))  # TODO 10: sessiz_dur → 0, hata → 1

    # Başarılı yükleme varsa kota state'i güncelle
    if yayinlanan > 0:
        kota_state_yaz(doldu=False, kalan_saat=0, video_sayisi=yayinlanan)
    
    # Çıkış kodu GÜNLÜK TOPLAM hedefe göre (2026-11-11 düzeltmesi).
    # Eski hâli `basarili_toplam >= GUNLUK_HEDEF` idi: bu turda 1 video yüklenip
    # günlük hedef 4 ise koşu KIRMIZI oluyordu — 15 dakikalık kadansta günde 96
    # kırmızı tik + 96 otonom self-repair denemesi demek. Artık ölçü gün toplamı:
    # kota/hedef no-op turları YEŞİL döner (sessiz_dur felsefesiyle aynı).
    gun_toplam = bugunki_video_sayisi()
    if gun_toplam >= GUNLUK_HEDEF:
        log_yaz(f"✅ Günlük hedef tamam: {gun_toplam}/{GUNLUK_HEDEF}")
        sys.exit(0)

    if yayinlanan > 0:
        log_yaz(
            f"ℹ️ Bu tur {yayinlanan} yayınladı; günlük hedef sürüyor "
            f"({gun_toplam}/{GUNLUK_HEDEF}) — sonraki kadans devam edecek."
        )
        sys.exit(0)

    log_yaz(f"❌ Bu turda hiç yayın yok ({gun_toplam}/{GUNLUK_HEDEF})", "ERROR")
    sys.exit(1)


if __name__ == "__main__":
    pipeline_calistir()
