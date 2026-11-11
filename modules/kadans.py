"""Üretim kadansı — tek doğruluk kaynağı.

KADANS_DK = 480 → "8 saatte bir video üretilip kanala yüklensin" (günde 3).

KARAR (2026-11-11, kullanıcı): 15 dk kadans kanalı yaktı. Ölçüm: 1 saatte
silinen 21 videonun aldığı izlenme 0-4 aralığında (ortalama 0.8) — yani
Shorts akışına hiç girmiyorlardı. 15 dk'da bir yükleme + 1 saatte silme
YouTube'a "yükle-sil" spam sinyali veriyordu. Yeni rejim: günde 3 video,
sabit saatler (00:00 / 08:00 / 16:00 UTC).

Bu modül üç şeyi tutar ve hiçbir yerde kopyalanmaz:
  1. Hedef kadans (dakika) ve günlük koşu sayısı
  2. YouTube kotasının izin verdiği GERÇEK üst sınır
  3. İkisi çeliştiğinde ne olacağının açık açıklaması

ÖNEMLİ AYRIM (2026-11-11, kullanıcı kararı: "kotayı kaldır"):
  - KADANS = üretimin NE SIKLIKTA deneneceği (zamanlama, ücretsiz)
  - GÜNLÜK YÜKLEME TAVANI YOK → her üretilen video yüklenir.

Günlük yükleme tavanı (eski GUNLUK_MAKS = 6) KALDIRILDI: katalogdan, state'ten,
pipeline'dan ve panelden silindi. 8 saatlik kadans günde 3 fırsat yaratır
ve bu fırsatların tamamı yükleme yapabilir. Tek gerçek engel YouTube'un KENDİ
API hatasıdır (403 quotaExceeded): o an video stoğa yazılır, kota açılınca
(UTC 00:00) yüklenir — üretim durmaz.

Kod bu farkı gizlemez: log, panel ve doküman aynı cümleyi söyler.
"""

from __future__ import annotations

#: İstenen kadans (dakika). Kullanıcı kararı (2026-11-11): 8 saatte bir (480 dk).
KADANS_DK: int = 480

#: YouTube Data API günlük kota (birim). Google'ın sabiti — DEĞİŞTİRİLEMEZ.
YOUTUBE_GUNLUK_KOTA_BIRIM: int = 10_000

#: Tek bir videos.insert çağrısının yaklaşık maliyeti (birim).
VIDEO_INSERT_MALIYETI: int = 1_600

#: Google'ın günlük birim kotasının izin verdiği YUKARI SINIR (bilgi amaçlı;
#: UYGULANAN bir tavan DEĞİLDİR — uygulanan tavan yoktur, kullanıcı kararı
#: 2026-11-11). Panel/log bunu sınır gibi göstermez.
KOTA_MATEMATIGI_SINIRI: int = YOUTUBE_GUNLUK_KOTA_BIRIM // VIDEO_INSERT_MALIYETI

#: Geriye dönük uyumluluk adı (panel/kota_kapisi import eder). DEĞER 6'dır ama
#: UYGULANAN bir tavan DEĞİLDİR — kod hiçbir yerde yüklemeyi buna kırpmaz.
GUNLUK_YUKLEME_TAVANI: int = KOTA_MATEMATIGI_SINIRI

#: Bir günde kaç kadans fırsatı var (sadece zamanlama, yükleme sayısı DEĞİL).
GUNLUK_KADANS_SAYISI: int = (24 * 60) // KADANS_DK  # 3

#: Cron ifadesi — KADANS_DK ile tutarlı olmak ZORUNDA (test bunu doğrular).
#: Sabit saatler: günde 3 koşu (00:00, 08:00, 16:00 UTC). Algoritma için
#: "tahmin edilebilir yayın saati" düzensiz aralıktan iyidir.
KADANS_CRON: str = "0 */8 * * *"


def gercek_aralik_dk(gunluk_yukleme: int) -> int:
    """Verilen günlük yükleme sayısına düşen ortalama aralık (dakika).

    Args:
        gunluk_yukleme: Günlük yükleme sayısı (tavan YOK — değer kırpılmaz).

    Döner:
        İki yükleme arasındaki gerçek süre. Örn. 6 yükleme → 240 dk.
        Değer 0 veya negatifse 0 döner (yükleme yapılmayacak demektir).
    """
    if gunluk_yukleme <= 0:
        return 0
    return (24 * 60) // gunluk_yukleme


def kota_uyarisi(gunluk_yukleme: int) -> str:
    """Panel/log için tek cümlelik dürüst özet (tavan yok).

    Örn: "Kadans 480 dk (günde 3 fırsat) · günlük yükleme tavanı YOK ·
          hedef 3/gün → gerçekte 480 dakikada 1 video"
    """
    efective = gercek_aralik_dk(gunluk_yukleme)
    if efective == 0:
        return f"Kadans {KADANS_DK} dk · günlük yükleme 0 — üretim kapalı"
    return (
        f"Kadans {KADANS_DK} dk (günde {GUNLUK_KADANS_SAYISI} fırsat) · "
        f"günlük yükleme tavanı YOK · hedef {gunluk_yukleme}/gün → "
        f"gerçekte {efective} dakikada 1 video"
    )
