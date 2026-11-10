"""Üretim kadansı — tek doğruluk kaynağı.

KADANS_DK = 15 → "her 15 dakikada bir video üretilip kanala yüklensin".

Bu modül üç şeyi tutar ve hiçbir yerde kopyalanmaz:
  1. Hedef kadans (dakika) ve günlük koşu sayısı
  2. YouTube kotasının izin verdiği GERÇEK üst sınır
  3. İkisi çeliştiğinde ne olacağının açık açıklaması

ÖNEMLİ AYRIM (2026-11-11):
  - KADANS      = üretimin NE SIKLIKTA deneneceği (zamanlama, ücretsiz)
  - GUNLUK_MAKS = günde kaç YÜKLEME yapılacağı (kota tüketir)

Sadece "15 dakika" demek yükleme sayısını vermez: 15 dakikalık kadans
günde 96 fırsat yaratır ama YouTube kotası (10.000 birim / 1.600 birim)
günde en fazla 6 yükleme yapılabilir. Sistem, günün ilk 90 dakikasında
6 yüklemeyi yapar ve kalan 87 fırsatta sessizce bekler — atıl kapasite
DEĞİL, platformun sabit sınırıdır. İşte bu yüzden:

  Etkin üretim kadansı (fiili): günlük_hedef_gerçek bir yüklemeye düşen
  süre = 24 sa / GUNLUK_MAKS = 240 dakika (4 saatte bir yükleme).

Kod bu farkı gizlemez: log, panel ve doküman aynı cümleyi söyler.
"""

from __future__ import annotations

#: İstenen kadans (dakika). Kullanıcı isteği: her 15 dakikada bir.
KADANS_DK: int = 15

#: YouTube Data API günlük kota (birim). Google'ın sabiti — DEĞİŞTİRİLEMEZ.
YOUTUBE_GUNLUK_KOTA_BIRIM: int = 10_000

#: Tek bir videos.insert çağrısının yaklaşık maliyeti (birim).
VIDEO_INSERT_MALIYETI: int = 1_600

#: Kota matematiğinin izin verdiği günlük en fazla yükleme.
GUNLUK_YUKLEME_TAVANI: int = YOUTUBE_GUNLUK_KOTA_BIRIM // VIDEO_INSERT_MALIYETI  # 6

#: Bir günde kaç kadans fırsatı var (sadece zamanlama, yükleme sayısı DEĞİL).
GUNLUK_KADANS_SAYISI: int = (24 * 60) // KADANS_DK  # 96

#: Cron ifadesi — KADANS_DK ile tutarlı olmak ZORUNDA (test bunu doğrular).
KADANS_CRON: str = "*/15 * * * *"


def gercek_aralik_dk(gunluk_yukleme: int) -> int:
    """Kota sınırı altında fiili yükleme aralığı (dakika).

    Args:
        gunluk_yukleme: Kota tavanına kırpılmış günlük yükleme sayısı.

    Döner:
        İki yükleme arasındaki gerçek süre. Örn. 6 yükleme → 240 dk.
        Değer 0 veya negatifse 0 döner (yükleme yapılmayacak demektir).
    """
    if gunluk_yukleme <= 0:
        return 0
    return (24 * 60) // gunluk_yukleme


def kota_uyarisi(gunluk_yukleme: int) -> str:
    """Panel/log için tek cümlelik dürüst özet.

    Örn: "Kadans 15 dk (günde 96 fırsat) · kotaya göre fiili yükleme 6/gün
          → gerçekte 240 dakikada 1 video"
    """
    efective = gercek_aralik_dk(gunluk_yukleme)
    if efective == 0:
        return f"Kadans {KADANS_DK} dk · günlük yükleme 0 — üretim kapalı"
    return (
        f"Kadans {KADANS_DK} dk (günde {GUNLUK_KADANS_SAYISI} fırsat) · "
        f"kota tavanı {gunluk_yukleme}/gün → gerçekte {efective} dakikada 1 video"
    )
