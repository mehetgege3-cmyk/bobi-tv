"""İlginç bilgi içerik hattı — eski kategori/diyalog formatının YERİNE geçer.

KULLANICI TALEBİ (2026-11-11, format devrimi):
  "Bu kategorileri, formatı ve konuların hepsini çöpe at. Hiçbir kullanıcı bu
   saçmalıklara zaman ayırmaz."

YENİ FORMAT (zorunlu):
  🧠 Günün Merak Uyandıran Sorusu
  🔍 Cevabı Biliyor Muydun?   (200-300 KELİME)
  💡 Şaşırtıcı Sonuç

8 KATEGORİ, her paylaşımda rastgele biri:
  1 bilim_teknoloji · 2 tarih_medeniyet · 3 doga_evren · 4 hayvanlar
  5 insan_vucudu · 6 yiyecekler · 7 kulturler · 8 gunluk_yasam

12 İÇERİK KURALI: `kurallar.py` (kural → denetim fonksiyonu eşlemesi).

MODÜLLER
  kategoriler  — 8 kategori tanımı, renk paleti, geçiş kuralı
  kurallar     — 12 kural + denetim (kelime sayısı, Türkçe, tekrar...)
  dogruluk     — kaynak zorunluluğu, tehlikeli iddia filtresi, çürütülmüş bilgi bankası
  etkilesim    — 7 güvenli taktik + rotasyon + hassas kategori yasakları
  uretici      — Arena diyaloğu → senaryo paketi (video_render uyumlu)
  kalite       — toplam kalite kapısı (12 kural + doğruluk + taktik)

TASARIM KARARI: video hattı (`video_render`, `tts_engine`, kapak, YouTube
yükleme) TEK SATIR DEĞİŞMEDEN çalışır. Yeni içerik, aynı `senaryo_paketi`
sözleşmesine çevrilir: **tek anlatıcı** (BOBİ), 3 bölümlü metin.
"""

from __future__ import annotations

__all__ = ["kategoriler", "kurallar", "dogruluk", "etkilesim", "uretici", "kalite"]
