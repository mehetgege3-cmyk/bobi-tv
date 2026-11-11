"""8 kategori + kategori geçiş kuralı (12. kural: "günlük kategori geçişi").

KULLANICI TANIMI (2026-11-11): her paylaşımda **rastgele biri** seçilen 8 kategori.
Burada "rastgele" = tekrar etmeyen rastgele: son N videoda çıkan kategori
tekrar seçilmez (12. kural). Aksi hâlde şans eseri 3 gün üst üste "hayvanlar"
gelebilir ve kanal tek konulu görünür.
"""

from __future__ import annotations

import hashlib
import random

#: Kategori kimliği → (görünen ad, emoji, kapak/render renk paleti)
KATEGORILER: dict[str, dict] = {
    "bilim_teknoloji": {
        "ad": "Bilim ve Teknoloji",
        "emoji": "🔬",
        "renk": ("#1e3a8a", "#3b82f6", "#a5f3fc"),  # koyu mavi → camgöbeği
        "ornek_konular": ["ışık hızı", "uzay teleskopları", "yapay zekâ", "beyin bilimi"],
    },
    "tarih_medeniyet": {
        "ad": "Tarih ve Medeniyetler",
        "emoji": "🏛️",
        "renk": ("#78350f", "#d97706", "#fde68a"),  # toprak → altın
        "ornek_konular": ["antik kentler", "imparatorluklar", "kayıp yazılar", "arkeoloji"],
    },
    "doga_evren": {
        "ad": "Doğa ve Evren",
        "emoji": "🌌",
        "renk": ("#0f172a", "#6d28d9", "#c4b5fd"),  # gece → mor
        "ornek_konular": ["kara delikler", "okyanus derinlikleri", "volkanlar", "iklim"],
    },
    "hayvanlar": {
        "ad": "Hayvanlar ve Canlılar",
        "emoji": "🐙",
        "renk": ("#064e3b", "#10b981", "#bbf7d0"),  # orman → nane
        "ornek_konular": ["ahtapotlar", "göç yolları", "biyolüminesans", "böcek toplumları"],
    },
    "insan_vucudu": {
        "ad": "İnsan Vücudu ve Biyoloji",
        "emoji": "🧬",
        "renk": ("#7f1d1d", "#ef4444", "#fecaca"),  # koyu kırmızı → pembe
        "ornek_konular": ["bağışıklık", "uyku", "DNA", "beyin kimyası"],
    },
    "yiyecekler": {
        "ad": "Yiyecekler ve Beslenme",
        "emoji": "🍯",
        "renk": ("#713f12", "#f59e0b", "#fef3c7"),  # bal → sarı
        "ornek_konular": ["baharat tarihi", "fermantasyon", "bal", "kahve"],
    },
    "kulturler": {
        "ad": "Kültürler ve Gelenekler",
        "emoji": "🌍",
        "renk": ("#4c1d95", "#8b5cf6", "#ddd6fe"),  # mor
        "ornek_konular": ["bayramlar", "diller", "el sanatları", "mutfak kültürü"],
    },
    "gunluk_yasam": {
        "ad": "Günlük Yaşam ve İlginç Olaylar",
        "emoji": "🕰️",
        "renk": ("#164e63", "#0891b2", "#a5f3fc"),  # petrol → turkuaz
        "ornek_konular": ["icat hikâyeleri", "şehir efsaneleri", "günlük nesneler", "sıradışı rekorlar"],
    },
}

#: Kategori anahtarları (sıralı).
ANAHTARLAR: tuple[str, ...] = tuple(KATEGORILER.keys())

#: Son kaç videoda çıkan kategori tekrar edilmesin? (12. kural: günlük geçiş)
GECIS_PENCERESI = 8


def kategori_al(anahtar: str) -> dict:
    """Kategori sözlüğünü döndürür; bilinmeyen anahtar → gunluk_yasam."""
    return KATEGORILER.get(str(anahtar or "").lower(), KATEGORILER["gunluk_yasam"])


def kategori_adi(anahtar: str) -> str:
    return kategori_al(anahtar)["ad"]


def kategori_emojisi(anahtar: str) -> str:
    return kategori_al(anahtar)["emoji"]


def renk_paleti(anahtar: str) -> tuple[str, str, str]:
    return kategori_al(anahtar)["renk"]


def siradaki_kategori(
    son_kategoriler: list[str] | None = None,
    rng: random.Random | None = None,
    video_no: int | None = None,
) -> str:
    """Tekrar etmeyen rastgele kategori seçer.

    `son_kategoriler`: en yeniden eskiye son videoların kategorileri.
    `video_no` verilirse seçim deterministik olur (test/tekrar üretim için).

    Neden rastgele: kullanıcı kuralı "her paylaşımda rastgele biri".
    Neden tekrarsız: 12. kural "günlük kategori geçişi".
    """
    son = [str(k) for k in (son_kategoriler or [])][:GECIS_PENCERESI]
    adaylar = [k for k in ANAHTARLAR if k not in son]
    if not adaylar:  # pencere tüm kategorileri kapsıyorsa (pratikte olmaz)
        adaylar = list(ANAHTARLAR)

    if video_no is not None:
        # Deterministik: video_no'ya bağlı sabit sıra (hash ile kararlı)
        tohum = int(hashlib.md5(str(video_no).encode()).hexdigest()[:8], 16)
        return adaylar[tohum % len(adaylar)]

    secici = rng or random.Random()
    return secici.choice(adaylar)


def kategori_agirliklari(son_kategoriler: list[str] | None = None) -> dict[str, float]:
    """Panel için: her kategorinin son videolarda kaç kez geçtiği."""
    son = list(son_kategoriler or [])
    return {k: sum(1 for s in son if s == k) for k in ANAHTARLAR}
