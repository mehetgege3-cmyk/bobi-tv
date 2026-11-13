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

GRUPLAR: tuple[str, ...] = ("tetikleme", "uretim_kota", "temizlik", "bildirim", "sistem")
TIPLER: tuple[str, ...] = ("secim", "sayi", "anahtar", "sadece_goruntule")
RISKLER: tuple[str, ...] = ("dusuk", "orta", "yuksek")

# P4 — kota matematiği: YouTube 10.000 birim/gün, videos.insert ≈ 1.600 birim.
from modules.kadans import (  # noqa: E402  (tek doğruluk kaynağı — modules/kadans.py)
    GUNLUK_YUKLEME_TAVANI,
    # Re-export: eski kod/testler bu adları ayar_katalogu'ndan import ediyor.
    VIDEO_INSERT_MALIYETI,  # noqa: F401
    YOUTUBE_GUNLUK_KOTA_BIRIM,  # noqa: F401
)

#: KULLANICI KARARI (2026-11-11): "Kota 6 istemiyorum, kotayı kaldır."
#: Günlük yükleme tavanı ARTIK YOK — hiçbir kapı yüklemeyi sayıyla kesmez.
#: KOTA_TAVANI yalnızca ESKİ kodun import kırılmaması için durur; hiçbir
#: yerde sınır olarak kullanılmaz (aşağıdaki yorumlara bakın).
KOTA_TAVANI: int = GUNLUK_YUKLEME_TAVANI  # SADECE bilgi — SINIR DEĞİL

#: Temizlik grubunun ZORUNLU dürüstlük metni (panel bu metni aynen gösterir).
#: 2026-11-11 düzeltmesi: eski metin "ETKİLEMEZ" diyordu — YANLIŞTI. Bu ayarlar
#: main_pipeline → dusuk_izlenmeli_videolari_temizle → videos.delete zinciriyle
#: GERÇEK video siler. H1 yalnızca İKİNCİ mekanizma (cleanup_low_views.yml)
#: için geçerlidir; bu ayarlarla ilgisi yoktur.
TEMIZLIK_UYARI: str = (
    "⚠️ Bu ayar KANALDA GERÇEK VİDEO SİLER ve geri alınamaz. "
    "Kural: yayından sonra belirlenen süre geçip izlenme eşiğinin altında kalan "
    "video kalıcı silinir (main_pipeline.py → dusuk_izlenmeli_videolari_temizle "
    "→ videos.delete). Değişiklik onay ekranından geçer ve silinecek video "
    "sayısı önizlenir. (Ayrıca cleanup_low_views.yml kendi sabitini kullanır — H1.)"
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
        "etiket": "Zorla üretim",
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
        "aciklama": "1 iken render testi/atlanabilir ön kontroller yok sayılır ve üretim "
        "zorlanır. Günlük yükleme tavanı yoktur (kota kaldırıldı). Tek kullanımlıktır: "
        "üretim workflow'u tükettikten sonra otomatik 0'a çeker.",
    },
    # ---------- Grup 2 — uretim_kota ----------
    {
        "anahtar": "KADANS_DK",
        "etiket": "Üretim kadansı (dk)",
        "grup": "uretim_kota",
        "tip": "sayi",
        "secenekler": ["480", "240", "65"],
        "varsayilan": "480",
        "min": 65,
        "max": 1440,
        "env_adi": "KADANS_DK",
        "risk": "orta",
        "kalici": True,
        "etkili": True,
        "secret": False,
        "aciklama": (
            "Üretimin KAÇ DAKİKADA BİR DENENECEĞİ (zamanlama). 480 dk = 8 saatte "
            "bir, günde 3 video (2026-11-11: 15 dk kanalı yaktı — algoritma "
            "yükle-sil spam'i cezalandırdı). Günlük yükleme tavanı YOK. "
            "Değiştirmek için workflow cron'u da (docs/KADANS.md) "
            "güncellenmelidir."
        ),
    },
    {
        "anahtar": "GUNLUK_HEDEF",
        "etiket": "Günlük hedef",
        "grup": "uretim_kota",
        "tip": "sayi",
        # KULLANICI KURALI (2026-11-11): "günlük yükleme tavanı 6 İSTEMİYORUM".
        # Bu ayar artık GÜNLÜK TOPLAM HEDEF'tir (hedef = alt sınır, tavan DEĞİL).
        # 8 saatlik kadans = günde 3 koşu → varsayılan 3.
        "secenekler": ["1", "2", "3", "4"],
        "varsayilan": "3",
        "min": 1,
        "max": None,
        "env_adi": "GUNLUK_HEDEF",
        "risk": "dusuk",
        "kalici": True,
        "etkili": True,
        "secret": False,
        "aciklama": (
            "Günlük TOPLAM yayın hedefi (alt sınır). Tavan YOK: hedef dolsa da "
            "üretim/yükleme sürer. 8 saatlik kadans = günde 3 koşu."
        ),
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
        "tip": "anahtar",
        "secenekler": None,
        "varsayilan": "1",
        "min": None,
        "max": None,
        "env_adi": "OTOMATIK_SIL_AKTIF",
        "risk": "yuksek",
        "kalici": False,
        "etkili": True,
        "secret": False,
        "mevcut": "1",
    
        "aciklama": (
            "GERÇEK VİDEO SİLER. 1 saatte 100 izlenme almayan video kalıcı silinir "
            "(main_pipeline.py → dusuk_izlenmeli_videolari_temizle, videos.delete). "
            "Değer düşükse çok video gider, yüksekse az. Değişiklik çift onay ister "
            "ve onay ekranı SİLİNECEK video sayısını önizler. Geri alınamaz."
        ),
    },
    {
        "anahtar": "MIN_IZLENME_ESIGI",
        "etiket": "Min izlenme eşiği",
        "grup": "temizlik",
        "tip": "sayi",
        "secenekler": None,
        "varsayilan": "100",
        "env_adi": "MIN_IZLENME_ESIGI",
        "risk": "yuksek",
        "kalici": True,
        "etkili": True,
        "secret": False,
        "mevcut": "100",
        "min": 0,
        "max": 100000,
    
        "aciklama": (
            "GERÇEK VİDEO SİLER. 6 saatte 100 izlenme almayan video kalıcı silinir "
            "(main_pipeline.py → dusuk_izlenmeli_videolari_temizle, videos.delete). "
            "Değer düşükse çok video gider, yüksekse az. Değişiklik çift onay ister "
            "ve onay ekranı SİLİNECEK video sayısını önizler. Geri alınamaz."
        ),
    },
    {
        "anahtar": "IZLENME_KONTROL_DK",
        "etiket": "İzlenme kontrolü",
        "grup": "temizlik",
        "tip": "sayi",
        "secenekler": None,
        "varsayilan": "360",
        "env_adi": "IZLENME_KONTROL_DK",
        "risk": "orta",
        "kalici": True,
        "etkili": True,
        "secret": False,
        "mevcut": "360",
        "min": 15,
        "max": 10080,
        "aciklama": (
            "GERÇEK VİDEO SİLER. Bu süre (dk) dolunca izlenme kontrol edilir; "
            "6 saat = 360 dk (2026-11-11 kararı: 60 dk çok erkendi, videolar "
            "akışa girmeden siliniyordu). Geri alınamaz."
        ),
    },
    # ---------- Grup 4 — sistem (SADECE GÖRÜNTÜLE, değer asla yazdırılmaz) ----------
    {
        "anahtar": "SESSIZ_BASLANGIC",
        "env_adi": "SESSIZ_BASLANGIC",
        "etiket": "Sessiz saat başlangıcı",
        "grup": "bildirim",
        "tip": "secim",
        "secenekler": ["21:00", "22:00", "23:00", "00:00"],
        "varsayilan": "00:00",
        "min": 21,
        "max": 23,
        "kalici": True,
        "etkili": True,
        "risk": "dusuk",
        "degistirilebilir": True,
        "aciklama": "Bu saatten sonra NORMAL bildirimler bekler (KRİTİK her zaman geçer).",
    },
    {
        "anahtar": "SESSIZ_BITIS",
        "env_adi": "SESSIZ_BITIS",
        "etiket": "Sessiz saat bitişi",
        "grup": "bildirim",
        "tip": "secim",
        "secenekler": ["06:00", "07:00", "08:00", "09:00"],
        "varsayilan": "08:00",
        "min": 6,
        "max": 9,
        "kalici": True,
        "etkili": True,
        "risk": "dusuk",
        "degistirilebilir": True,
        "aciklama": "Pencere bitince gece biriken bildirimler TEK mesajda gelir.",
    },
    {
        "anahtar": "OZET_SAATI",
        "env_adi": "OZET_SAATI",
        "etiket": "Günlük özet saati",
        "grup": "bildirim",
        "tip": "secim",
        "secenekler": ["08:00", "09:00", "10:00", "12:00"],
        "varsayilan": "09:00",
        "min": 8,
        "max": 12,
        "kalici": True,
        "etkili": True,
        "risk": "dusuk",
        "degistirilebilir": True,
        "aciklama": "Günlük özet bu saatte gönderilir (TR).",
    },
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
        # 2026-11-13: Arena AI çöpe atıldı (kullanıcı kararı). Panelde ölü
        # secret göstermek yanıltıcıydı — yerine GERÇEK sağlayıcı geldi.
        # Eski kayıt: ARENA_COOKIES_JSON ("Arena cookies").
        "anahtar": "GEMINI_COOKIES",
        "etiket": "Gemini web çerezi",
        "grup": "sistem",
        "tip": "sadece_goruntule",
        "secenekler": None,
        "varsayilan": None,
        "min": None,
        "max": None,
        "env_adi": "GEMINI_COOKIES",
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
    """Geriye dönük uyumluluk sarmalayıcı — ARTIK KIRPMA YAPMAZ.

    KULLANICI KARARI (2026-11-11): "Kota 6 istemiyorum, kotayı kaldır."
    Eski davranış değeri 6'ya kırpıyordu; bu bir YÜKLEME SINIRI yaratıyordu.
    Artık değer ne verilirse o kullanılır (yalnız negatif değer 0'a çekilir).
    """
    try:
        return max(0, int(str(ham_deger).strip()))
    except (TypeError, ValueError):
        return 0
