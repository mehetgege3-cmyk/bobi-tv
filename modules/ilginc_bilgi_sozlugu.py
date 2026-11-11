"""İlginç bilgi formatı — süre/kelime bütçesi ve format sabitleri.

NEDEN (2026-11-11 kullanıcı talimatı):
  "YouTube'un güncel kuralları: maksimum 180 saniye (3 dakika), dikey 9:16,
   1080x1920. Sana bu kısıtlamayı dayatan kodları çöpe at."

Eski kod 59.5 sn tavanı koyuyordu — bu YouTube kuralı DEĞİLDİ ve bilgi
anlatımını 45-60 kelimeye sıkıştırıyordu. Artık:
  • üst sınır 180 sn (Shorts 3 dk)
  • kelime bütçesi süreden HESAPLANIR (tahmin değil)
  • senaryo metni hem videoda anlatılır hem YouTube açıklamasına yazılır
"""

from __future__ import annotations

#: YouTube Shorts üst sınırı (dikey, 9:16, ≤1080x1920).
SHORTS_MAKS_SN = 180
#: Anlatım için alt sınır (çok kısa videolar akışa girmiyor).
SHORTS_MIN_SN = 15
#: Türkçe TTS ~180 kelime/dk (mevcut üretim loglarından ölçüldü).
KELIME_DK = 180


def kelime_butcesi(saniye: float, kelime_dk: int = KELIME_DK) -> tuple[int, int]:
    """Verilen video süresi için (en az, en çok) kelime aralığı.

    %10 alt/üst pay bırakılır: TTS hızı replik uzunluğuna göre biraz değişir.
    """
    saniye = max(SHORTS_MIN_SN, min(float(saniye), SHORTS_MAKS_SN))
    temel = saniye / 60.0 * kelime_dk
    return int(temel * 0.9), int(temel * 1.1)


def tahmini_sure(kelime: int, kelime_dk: int = KELIME_DK) -> float:
    """Kelime sayısından tahmini konuşma süresi (saniye)."""
    return round(kelime / max(1, kelime_dk) * 60.0, 1)


#: Hedef süre -> içerik tipi eşlemesi (kullanıcının strateji tablosu).
SURE_PROFILLERI = {
    "viral_bilgi": (20, 35),
    "eglenceli": (25, 45),
    "hikaye_gizem": (45, 60),
    "ai_anlatim": (45, 90),
    "mini_belgesel": (90, 180),
}
