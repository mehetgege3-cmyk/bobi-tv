"""SİLİNDİ — 2026-11-12 kullanıcı kararı: "mevcut tüm kuralları çöpe at".

Eski kapak hattı (kapak_uret.py) kaldırıldı. Tek yol:
`modules/kapak_hatti.py` → Arena tam metni okur, kapak GÖRSELİ üretir,
görsel videonun 1. karesine yerleşir.

Bu dosya bilinçli olarak boş bırakıldı: eski import eden kod varsa
hemen hata versin, sessizce eski davranışa dönmesin.
"""

raise ImportError(
    "Eski kapak hattı silindi (2026-11-12). modules.kapak_hatti.kapak_uret_ve_yerlestir kullan."
)
