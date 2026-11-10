"""BOBİ TV — Ayar Kataloğu (tek doğruluk kaynağı — TODO 1).

Her ayarın kimliği, tipi, seçenekleri, varsayılanı, env adı, riski ve
etkililiği BURADA tanımlanır. Panel (telegram_bot.py), state deposu
(ayar_deposu.py) ve workflow köprüsü (hourly_production.yml) bu katalogdan
beslenir.

Alanlar:
    anahtar      panel/state anahtarı (callback_data'da kimlik olarak taşınır)
    etiket       panelde görünen ad (≤20 karakter hedefi)
    grup         tetikleme | uretim_kota | temizlik | sistem
    tip          secim | sayi | anahtar | sadece_goruntule
    secenekler   secim için seçenek listesi; sayi için ön ayar düğmeleri;
                 anahtar ve sadece_goruntule için None
    varsayilan   katalog varsayılanı (secret'lar için asla None değil — YOK)
    min / max    sayi tipi aralığı; diğerlerinde None
    env_adi      pipeline'a köprülenen ortam değişkeni adı (her ayarda DOLU)
    risk         dusuk | orta | yuksek (yuksek → panelde onay ekranı)
    kalici       state'e yazılıp yazılmayacağı (force tek kullanımlıktır: False)
    etkili       değerin pipeline'ı gerçekten etkileyip etkilemediği
                 (temizlik grubu = False; H1 — dürüstlük kuralı)
    secret       True ise değeri ASLA görüntülenmez; yalnız tanımlı/eksik

Kataloğa ALINMAYAN ayarlar (gerekçeleriyle — yalan ayar eklememek için):
    TETIK_DK       GitHub cron fiilen güvenilir çalışmıyor (bugün 16+ saat koşu
                   yok); "10 dk tetikleme" ayarı yalan olurdu. Tetikleyici
                   sağlığı Grup 4'te gözlemlenir.
    SESSIZ_SAAT    zaman dilimi + cron güvenilmezliği birleşince doğrulanamaz;
                   dış tetikleyici kurulduktan sonra eklenir.
    OTOMATIK_URETIM  repository_dispatch'i çağıran dış tetikleyici yok;
                   kapatma düğmesi işlevsiz olurdu.
"""

from __future__ import annotations

from typing import Any

GRUPLAR: tuple[str, ...] = ("tetikleme", "uretim_kota", "temizlik", "sistem")
TIPLER: tuple[str, ...] = ("secim", "sayi", "anahtar", "sadece_goruntule")
RISKLER: tuple[str, ...] = ("dusuk", "orta", "yuksek")

# P4 — kota matematiği: YouTube 10.000 birim/gün, videos.insert ≈ 1.600 birim.
YOUTUBE_GUNLUK_KOTA_BIRIM: int = 10_000
VIDEO_INSERT_MALIYETI: int = 1_600
KOTA_TAVANI: int = YOUTUBE_GUNLUK_KOTA_BIRIM // VIDEO_INSERT_MALIYETI  # 6

# TODO 11 — Grup 3'ün ZORUNLU dürüstlük metni (panel bu metni aynen gösterir).
TEMIZLIK_UYARI: str = (
    "⚠️ Bu değeri değiştirmek otomatik temizlemeyi ETKİLEMEZ. "
    "Temizleme workflow'u kendi sabitini kullanıyor "
    "(cleanup_low_views.yml → if views &lt; 100). "
    "Bilinen sorun (H1), ayrı görevde çözülecek."
)

KATALOG: list[dict[str, Any]] = [
    # ---------- Grup 1 — tetikleme ----------
    {
        "anahtar": "YUKLEME_ATLA",
        "etiket": "Render testi",
        "grup": "tetikleme",
        "tip": "anahtar",
        "secenekler": None,
        "varsayilan": "0",
        "min": None,
        "max": None,
        "env_adi": "YUKLEME_ATLA",
        "risk": "dusuk",
        "kalici": True,
        "etkili": True,
        "secret": False,
        "aciklama": "1 iken videolar yalnızca yerel üretilir, YouTube'a YÜKLEME YAPILMAZ. "
        "Render testi düğmesi bunu geçici olarak zorlar.",
    },
    {
        "anahtar": "MOD",
        "etiket": "Üretim modu",
        "grup": "tetikleme",
        "tip": "secim",
        "secenekler": ["isindirma_saatlik", "normal"],
        "varsayilan": "isindirma_saatlik",
        "min": None,
        "max": None,
        "env_adi": "MOD",
        "risk": "dusuk",
        "kalici": True,
        "etkili": True,
        "secret": False,
        "aciklama": "isindirma_saatlik: dönen konu havuzu + 15sn alt sınır; normal: sıradan üretim.",
    },
    {
        "anahtar": "force",
        "etiket": "Kota kapısını atla",
        "grup": "tetikleme",
        "tip": "anahtar",
        "secenekler": None,
        "varsayilan": "0",
        "min": None,
        "max": None,
        "env_adi": "force",
        "risk": "yuksek",
        "kalici": False,
        "etkili": True,
        "secret": False,
        "aciklama": "1 iken kota kapısı bu koşuda devre dışı kalır. Tek kullanımlıktır: "
        "üretim workflow'u tükettikten sonra otomatik 0'a çeker.",
    },
    # ---------- Grup 2 — uretim_kota ----------
    {
        "anahtar": "GUNLUK_HEDEF",
        "etiket": "Günlük hedef",
        "grup": "uretim_kota",
        "tip": "secim",
        "secenekler": ["1", "2", "4"],
        "varsayilan": "1",
        "min": None,
        "max": None,
        "env_adi": "GUNLUK_HEDEF",
        "risk": "dusuk",
        "kalici": True,
        "etkili": True,
        "secret": False,
        "aciklama": "Her koşuda hedeflenen yükleme sayısı. Kota tavanını (6) aşamaz.",
    },
    {
        "anahtar": "GUNLUK_MAKS",
        "etiket": "Günlük üst sınır",
        "grup": "uretim_kota",
        "tip": "secim",
        "secenekler": ["2", "5", "6"],
        "varsayilan": "6",
        "min": None,
        "max": None,
        "env_adi": "GUNLUK_MAKS",
        "risk": "orta",
        "kalici": True,
        "etkili": True,
        "secret": False,
        "aciklama": "Günlük yükleme tavanı. Kota matematiği: 10000/1600 = 6 — "
        "7 ve üzeri seçenek bilinçli olarak YOK; kod ayrıca min(değer, 6) savunması yapar.",
    },
    {
        "anahtar": "KOTA_DOLU_DAVRANIS",
        "etiket": "Kota dolunca",
        "grup": "uretim_kota",
        "tip": "secim",
        "secenekler": ["sessiz_dur", "hata"],
        "varsayilan": "sessiz_dur",
        "min": None,
        "max": None,
        "env_adi": "KOTA_DOLU_DAVRANIS",
        "risk": "yuksek",
        "kalici": True,
        "etkili": True,
        "secret": False,
        "aciklama": "sessiz_dur: koşu exit(0) ile biter (kırmızı tik yok — self-repair "
        "fırtınası önlenir). hata: exit(1) — kırmızı tik + self-repair tetiklenebilir.",
    },
    {
        "anahtar": "KOTA_REZERV",
        "etiket": "Kota rezerv eşiği",
        "grup": "uretim_kota",
        "tip": "sayi",
        "secenekler": [0, 250, 500, 1000, 1500, 2000],
        "varsayilan": 500,
        "min": 0,
        "max": 2000,
        "env_adi": "KOTA_REZERV",
        "risk": "dusuk",
        "kalici": True,
        "etkili": True,
        "secret": False,
        "aciklama": "Birim cinsinden rezerv eşiği (0-2000). Panelde gösterim bilgi amaçlıdır; "
        "kota birimi workflow'a rapor edilene kadar etkin kullanımı 'bilinmiyor' görünür.",
    },
    # ---------- Grup 3 — temizlik (SADECE GÖRÜNTÜLE, etkili=False) ----------
    {
        "anahtar": "OTOMATIK_SIL_AKTIF",
        "etiket": "Otomatik silme",
        "grup": "temizlik",
        "tip": "sadece_goruntule",
        "secenekler": None,
        "varsayilan": None,
        "min": None,
        "max": None,
        "env_adi": "OTOMATIK_SIL_AKTIF",
        "risk": "yuksek",
        "kalici": False,
        "etkili": True,
        "secret": False,
        "mevcut": "1",
    
        "aciklama": (
            "KİLİTLİ — bu ayar KANALDA GERÇEK VİDEO SİLER: main_pipeline.py "
            "dusuk_izlenmeli_videolari_temizle() çağrısına geçirilir ve "
            "youtube_upload.py videos.delete ile siler. Değiştirmek için kod "
            "değişikliği gerekir (kaza koruması). İKİNCİ silme mekanizması "
            "cleanup_low_views.yml kendi sabitini kullanır (H1) — ayrı sorun."
        ),
    },
    {
        "anahtar": "MIN_IZLENME_ESIGI",
        "etiket": "Min izlenme eşiği",
        "grup": "temizlik",
        "tip": "sadece_goruntule",
        "secenekler": None,
        "varsayilan": None,
        "min": None,
        "max": None,
        "env_adi": "MIN_IZLENME_ESIGI",
        "risk": "yuksek",
        "kalici": False,
        "etkili": True,
        "secret": False,
        "mevcut": "100",
    
        "aciklama": (
            "KİLİTLİ — bu ayar KANALDA GERÇEK VİDEO SİLER: main_pipeline.py "
            "dusuk_izlenmeli_videolari_temizle() çağrısına geçirilir ve "
            "youtube_upload.py videos.delete ile siler. Değiştirmek için kod "
            "değişikliği gerekir (kaza koruması). İKİNCİ silme mekanizması "
            "cleanup_low_views.yml kendi sabitini kullanır (H1) — ayrı sorun."
        ),
    },
    {
        "anahtar": "IZLENME_KONTROL_DK",
        "etiket": "İzlenme kontrolü",
        "grup": "temizlik",
        "tip": "sadece_goruntule",
        "secenekler": None,
        "varsayilan": None,
        "min": None,
        "max": None,
        "env_adi": "IZLENME_KONTROL_DK",
        "risk": "dusuk",
        "kalici": False,
        "etkili": True,
        "secret": False,
        "mevcut": "1440",
        "aciklama": (
            "KİLİTLİ — bu ayar KANALDA GERÇEK VİDEO SİLER: main_pipeline.py "
            "dusuk_izlenmeli_videolari_temizle() çağrısına geçirilir ve "
            "youtube_upload.py videos.delete ile siler. Değiştirmek için kod "
            "değişikliği gerekir (kaza koruması). İKİNCİ silme mekanizması "
            "cleanup_low_views.yml kendi sabitini kullanır (H1) — ayrı sorun."
        ),
    },
    # ---------- Grup 4 — sistem (SADECE GÖRÜNTÜLE, değer asla yazdırılmaz) ----------
    {
        "anahtar": "YOUTUBE_TOKEN",
        "etiket": "YouTube token",
        "grup": "sistem",
        "tip": "sadece_goruntule",
        "secenekler": None,
        "varsayilan": None,
        "min": None,
        "max": None,
        "env_adi": "YOUTUBE_TOKEN",
        "risk": "yuksek",
        "kalici": False,
        "etkili": True,
        "secret": True,
    },
    {
        "anahtar": "YOUTUBE_CLIENT_SECRET",
        "etiket": "YouTube client secret",
        "grup": "sistem",
        "tip": "sadece_goruntule",
        "secenekler": None,
        "varsayilan": None,
        "min": None,
        "max": None,
        "env_adi": "YOUTUBE_CLIENT_SECRET",
        "risk": "yuksek",
        "kalici": False,
        "etkili": True,
        "secret": True,
    },
    {
        "anahtar": "ARENA_COOKIES_JSON",
        "etiket": "Arena cookies",
        "grup": "sistem",
        "tip": "sadece_goruntule",
        "secenekler": None,
        "varsayilan": None,
        "min": None,
        "max": None,
        "env_adi": "ARENA_COOKIES_JSON",
        "risk": "yuksek",
        "kalici": False,
        "etkili": True,
        "secret": True,
    },
    {
        "anahtar": "PEXELS_API_KEY",
        "etiket": "Pexels API",
        "grup": "sistem",
        "tip": "sadece_goruntule",
        "secenekler": None,
        "varsayilan": None,
        "min": None,
        "max": None,
        "env_adi": "PEXELS_API_KEY",
        "risk": "orta",
        "kalici": False,
        "etkili": True,
        "secret": True,
    },
    {
        "anahtar": "GH_TOKEN",
        "etiket": "GitHub token",
        "grup": "sistem",
        "tip": "sadece_goruntule",
        "secenekler": None,
        "varsayilan": None,
        "min": None,
        "max": None,
        "env_adi": "GH_TOKEN",
        "risk": "yuksek",
        "kalici": False,
        "etkili": True,
        "secret": True,
    },
    {
        "anahtar": "TELEGRAM_BOT_TOKEN",
        "etiket": "Telegram bot token",
        "grup": "sistem",
        "tip": "sadece_goruntule",
        "secenekler": None,
        "varsayilan": None,
        "min": None,
        "max": None,
        "env_adi": "TELEGRAM_BOT_TOKEN",
        "risk": "yuksek",
        "kalici": False,
        "etkili": True,
        "secret": True,
    },
]


def tumu() -> list[dict[str, Any]]:
    """Kataloğun tamamı (sıra korunur)."""
    return KATALOG


def anahtarlar() -> tuple[str, ...]:
    return tuple(str(a["anahtar"]) for a in KATALOG)


def ayar_getir(anahtar: str) -> dict[str, Any] | None:
    """Anahtarla arar; yoksa None (asla exception fırlatmaz)."""
    for a in KATALOG:
        if a["anahtar"] == anahtar:
            return a
    return None


def grup_ayarlari(grup: str) -> list[dict[str, Any]]:
    """Grubun ayar listesi; bilinmeyen grup → boş liste."""
    return [a for a in KATALOG if a["grup"] == grup]


def degistirilebilir_mi(ayar: dict[str, Any]) -> bool:
    """sadece_goruntule tipler değiştirilemez (temizlik + sistem)."""
    return bool(ayar["tip"] != "sadece_goruntule")


def etkin_gunluk_maks(ham_deger: int | str | None) -> int:
    """GUNLUK_MAKS tavan savunması (TODO 10): değer ne olursa olsun ≤ KOTA_TAVANI.

    Kota matematiği: 10000 birim / 1600 birim = 6 yükleme/gün. Tavanı aşan
    değer sessizce değil, LOG uyarısıyla kırpılır. Bozuk/negatif değer → tavan.
    """
    try:
        ham = int(str(ham_deger).strip())
    except (TypeError, ValueError):
        print(f"::warning::GUNLUK_MAKS bozuk ({ham_deger!r}) — tavan {KOTA_TAVANI} kullanılıyor")
        return KOTA_TAVANI
    etkin = max(0, min(ham, KOTA_TAVANI))
    if ham > KOTA_TAVANI:
        print(
            f"::warning::GUNLUK_MAKS={ham} kota tavanını aşıyor — "
            f"etkin değer {etkin} yapıldı (10000/1600 = {KOTA_TAVANI})"
        )
    return etkin
