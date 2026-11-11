"""BOBİ TV — "Ne işe yarıyor?" rehberi (TODO 22, Kaan).

AMAÇ: Her ayarın ne yaptığını, NE ZAMAN etkili olduğunu ve NEYİ DEĞİŞTİRMEDİĞİNİ
tek ekranda, sade Türkçe ile anlatmak. Kullanıcı "bu düğme ne yapıyor?"
sorusunun cevabını panelden almalı; doküman okumak zorunda kalmamalı.

KURALLAR (değişmez):
- Uydurma sayı/eşik YOK: eşik değerleri katalogdan okunur, katalogda yoksa
  "bilinmiyor" yazılır.
- Yalan vaat YOK: günlük yükleme tavanı kaldırıldı (2026-11-11) — rehber
  hiçbir yerde "günde 6" gibi bir tavan iddia etmez.
- Secret değerleri ASLA yazılmaz; yalnızca "tanımlı / eksik" durumu.
- Ekran ≈15 satır: her ayar 3-4 satırda anlatılır, uzun metin dokümana gider.
"""
from __future__ import annotations

import os
from typing import Any

BILINMIYOR = "bilinmiyor"

#: Ayar → (ne yapar, ne zaman etkili, neyi DEĞİŞTİRMEZ).
#: Metinler kasıtlı kısa: panelde 15 satır sınırı var.
REHBER: dict[str, dict[str, str]] = {
    "KADANS_DK": {
        "ne": "Üretimin kaç dakikada bir DENENECEĞİ.",
        "zaman": "Bir sonraki koşudan itibaren.",
        "degil": "Yükleme sayısını sınırlamaz — günlük tavan yok. Cron YAML'da yaşar: "
        "tam etki için workflow cron'u da değişmeli.",
    },
    "GUNLUK_HEDEF": {
        "ne": "Günde en az kaç yayın hedeflendiği (rapor/özet bunu kullanır).",
        "zaman": "Aynı gün içindeki raporlarda görünür.",
        "degil": "Üretimi DURDURMAZ; hedef dolsa da üretim sürer (fazlası yüklenir).",
    },
    "KOTA_DOLU_DAVRANIS": {
        "ne": "YouTube'un kendi 403 kotası geldiğinde koşunun rengi.",
        "zaman": "Bir sonraki kota hatasında.",
        "degil": "Yüklemeyi SAYIYLA kesmez; tavan yok. Video her durumda stoğa alınır.",
    },
    "KOTA_REZERV": {
        "ne": "Kota birimi bu eşiğin altına inince panelde uyarı görünür.",
        "zaman": "Panel yenilendiğinde.",
        "degil": "Üretimi durdurmaz; yalnız bilgi/uyarı eşiğidir.",
    },
    "YUKLEME_ATLA": {
        "ne": "Render testi: üretimi çalıştırır, YouTube'a YÜKLEME YAPMAZ.",
        "zaman": "Yalnızca tetiklenen koşuda.",
        "degil": "Kanalı etkilemez, arşive yayın kaydı yazmaz.",
    },
    "MOD": {
        "ne": "Isındırma (dönen konu havuzu, 15 sn alt sınır) veya normal mod.",
        "zaman": "Bir sonraki üretimde.",
        "degil": "Kalite kapısını gevşetmez; süre/QC kuralları aynı kalır.",
    },
    "force": {
        "ne": "Ön kontrolleri (render testi vb.) atlayıp üretimi zorlar.",
        "zaman": "Tek kullanımlık: workflow tükettikten sonra 0'a çeker.",
        "degil": "Yükleme tavanını atlamaz — tavan yok. Kalite kapısını atlamaz.",
    },
    "OTOMATIK_SIL_AKTIF": {
        "ne": "Yayından sonra eşiğin altında kalan videoları siler.",
        "zaman": "Kontrol saati geldiğinde, GERİ ALINAMAZ.",
        "degil": "Eşiği kendisi belirlemez; OAuth yetkisi yoksa hiç çalışmaz.",
    },
    "MIN_IZLENME_ESIGI": {
        "ne": "Bu izlenme sayısının ALTINDA kalan video silinir.",
        "zaman": "Sonraki kontrol turunda, GERİ ALINAMAZ.",
        "degil": "Yükleme sayısını etkilemez.",
    },
    "IZLENME_KONTROL_DK": {
        "ne": "Yayından kaç dakika sonra izlenme kontrol edileceği.",
        "zaman": "Sonraki kontrolden itibaren.",
        "degil": "Silme kuralını değiştirmez, yalnız zamanlamasını.",
    },
    "SESSIZ_BASLANGIC": {
        "ne": "Bildirimlerin susacağı saatin başlangıcı.",
        "zaman": "O saatten itibaren.",
        "degil": "Üretimi durdurmaz; yalnız bildirim sessizleşir.",
    },
    "SESSIZ_BITIS": {
        "ne": "Sessiz saatin bittiği saat (bildirimler geri gelir).",
        "zaman": "O saatten itibaren.",
        "degil": "Birikmiş bildirimleri tek tek göndermez; özet gelir.",
    },
    "OZET_SAATI": {
        "ne": "Günlük özet bildiriminin saati.",
        "zaman": "Aynı gün o saatte.",
        "degil": "Sessiz saatteyse özet bekletilir.",
    },
    "YOUTUBE_TOKEN": {
        "ne": "YouTube'a yükleme/silme için OAuth erişimi.",
        "zaman": "Sonraki yüklemede.",
        "degil": "Değeri panelde ASLA gösterilmez; yoksa üretim sürer ama yükleme olmaz.",
    },
    "YOUTUBE_CLIENT_SECRET": {
        "ne": "OAuth token yenilemesi için istemci anahtarı.",
        "zaman": "Token süresi dolduğunda.",
        "degil": "Değeri gösterilmez; eksikse yükleme başarısız olur (sebep loga yazılır).",
    },
    "ARENA_COOKIES_JSON": {
        "ne": "Arena oturum çerezleri — senaryo/kapak üretimi için.",
        "zaman": "Sonraki üretimde.",
        "degil": "Değeri gösterilmez; yoksa senaryo üretilemez (uydurma senaryo yazılmaz).",
    },
    "GH_TOKEN": {
        "ne": "Panelin GitHub API'sine erişimi (koşu durumu, tetikleme).",
        "zaman": "Panel yenilendiğinde.",
        "degil": "Değeri gösterilmez; yoksa panel 'bilinmiyor' yazar, üretim etkilenmez.",
    },
    "TELEGRAM_BOT_TOKEN": {
        "ne": "Bu panelin Telegram'a mesaj göndermesi.",
        "zaman": "Her panel/bildirimde.",
        "degil": "Değeri gösterilmez; yoksa panel açılmaz.",
    },
    "PEXELS_API_KEY": {
        "ne": "Stok görsel/b-roll için Pexels erişimi.",
        "zaman": "Sonraki üretimde.",
        "degil": "Yoksa üretim durmaz; video stok görselsiz üretilir.",
    },
}

#: Secret ayarlar: değer değil, yalnızca VAR/YOK gösterilir.
SECRET_ANAHTARLAR = {
    "YOUTUBE_TOKEN",
    "YOUTUBE_CLIENT_SECRET",
    "ARENA_COOKIES_JSON",
    "GH_TOKEN",
    "TELEGRAM_BOT_TOKEN",
}

#: Secret olmayan, değeri gösterilebilir ayarlar.
SECRET_DEGIL = {"PEXELS_API_KEY"}

#: Ekranda gösterilecek üst düzey "ne işe yarıyor" özeti (ana ekran/yardım için).
SISTEM_OZETI = (
    "Sistem ne yapıyor: konu seçer → senaryo yazar → seslendirir → kapak + altyazı "
    "ile render eder → YouTube Shorts'a YÜKLER. Günlük yükleme tavanı YOK."
)


def rehber_girdisi(anahtar: str) -> dict[str, str]:
    """Ayarın rehber metni; yoksa dürüst 'bilinmiyor' (uydurma açıklama yok)."""
    g = REHBER.get(anahtar)
    if not g:
        return {
            "ne": f"{BILINMIYOR} — bu ayar için açıklama tanımlı değil.",
            "zaman": BILINMIYOR,
            "degil": BILINMIYOR,
        }
    return g


def secret_durumu(anahtar: str) -> str:
    """Secret için değer DEĞİL, yalnızca tanımlı/eksik bilgisi."""
    env_adi = _env_adi(anahtar)
    return "✅ tanımlı" if os.environ.get(env_adi, "") else "⛔ eksik"


def _env_adi(anahtar: str) -> str:
    """Katalogdaki env adı; katalog okunamazsa anahtarın kendisi."""
    try:
        from modules.ayar_katalogu import ayar_getir

        a = ayar_getir(anahtar)
        if a and a.get("env_adi"):
            return str(a["env_adi"])
    except Exception:
        pass
    return anahtar


def _kisa(metin: str, sinir: int = 96) -> str:
    m = " ".join(str(metin).split())
    return m if len(m) <= sinir else m[: sinir - 1] + "…"


def detay_metni(anahtar: str, etiket: str | None = None) -> str:
    """Tek ayarın rehber ekranı (≈10 satır)."""
    g = rehber_girdisi(anahtar)
    baslik = etiket or anahtar
    satirlar = [f"❓ <b>{baslik} ne işe yarar?</b>", ""]
    satirlar.append(f"✔️ <b>Ne yapar:</b> {_kisa(g['ne'])}")
    satirlar.append(f"⏱️ <b>Ne zaman etkili:</b> {_kisa(g['zaman'])}")
    satirlar.append(f"🚫 <b>Neyi değiştirmez:</b> {_kisa(g['degil'])}")
    return "\n".join(satirlar)


def grup_metni(grup: str) -> str:
    """Bir ayar grubunun rehber özeti — her ayar TEK satır (15 satır sınırı)."""
    try:
        from modules.ayar_katalogu import grup_ayarlari
    except Exception:
        return f"❓ {BILINMIYOR} — ayar kataloğu okunamadı."
    satirlar = ["❓ <b>Bu ayarlar ne işe yarıyor?</b>", ""]
    for a in grup_ayarlari(grup):
        anahtar = str(a["anahtar"])
        ad = str(a.get("etiket") or anahtar)
        g = rehber_girdisi(anahtar)
        satirlar.append(f"• <b>{ad}</b>: {_kisa(g['ne'], 70)}")
    return "\n".join(satirlar)


def sistem_metni() -> str:
    """Sistemin uçtan uca ne yaptığı + dürüst sınırlar (≈12 satır)."""
    satirlar = [
        "❓ <b>Bu sistem ne işe yarıyor?</b>",
        "",
        "1️⃣ Konu seçer (dönen kategori havuzu)",
        "2️⃣ Senaryoyu Arena ile yazar",
        "3️⃣ Çift sesle Türkçe TTS",
        "4️⃣ Kapak (1. kare + Arena başlık) + karaoke altyazı",
        "5️⃣ Render + QC (süre/çözünürlük kapısı)",
        "6️⃣ YouTube Shorts'a YÜKLER",
        "",
        "📌 Günlük yükleme tavanı <b>YOK</b> — üretilen her video yüklenir.",
        "📌 Tek gerçek engel YouTube'un kendi 403 kotasıdır: o an video stoğa "
        "alınır, kota açılınca (UTC 00:00) yüklenir.",
        "📌 Kalite kapısını geçmeyen video <b>yayınlanmaz</b> (süre 15-59,5 sn).",
    ]
    return "\n".join(satirlar)


def butun_anahtarlar() -> list[str]:
    """Rehberi olan tüm ayarlar (test ve yardım ekranı için)."""
    return sorted(REHBER)


def rehbersiz_ayarlar() -> list[str]:
    """Katalogdaki ama rehberi olmayan ayarlar — eksik dokümantasyonu görünür kılar."""
    try:
        from modules.ayar_katalogu import GRUPLAR, grup_ayarlari
    except Exception:
        return []
    eksik: list[str] = []
    for g in GRUPLAR:
        for a in grup_ayarlari(g):
            k = str(a["anahtar"])
            if k not in REHBER:
                eksik.append(k)
    return sorted(eksik)


def metin_uret(anahtar: str, ayar: dict[str, Any] | None = None) -> str:
    """Geriye dönük kolaylık: ayar sözlüğü verilirse etiketiyle detay üretir."""
    etiket = str(ayar.get("etiket")) if isinstance(ayar, dict) and ayar.get("etiket") else None
    return detay_metni(anahtar, etiket)
