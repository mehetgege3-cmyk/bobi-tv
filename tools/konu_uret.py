"""Konu üret — Gemini web'e şablon istemini gönder, JSON konu al.

NİÇİN Gemini web: 2026-11-13 kararı — Arena API ve Gemini API anahtarı çöpe
atıldı, tek sağlayıcı **Gemini web çerezi** (`GEMINI_COOKIES`). API kotası yok.

İSTEM BİREBİR: `docs/SABLON_ISTEM.md` içindeki "MEVCUT ŞABLON" bloğu.
Kullanıcı talimatı: *"bu promtu geminiye vericeksin"* — isteme ekleme yapılmaz.

KATEGORİ: 8 kategori, tekrarsız rotasyon (`docs/ILGINC_BILGI_HATTI.md`).
Arşivdeki (`bobi_tv/archive/videos.json`) son kategoriler okunur, son 4'te
çıkan kategori seçilmez.

ÇIKTI (stdout JSON):
    {"baslik": "...", "metin": "...", "soru": "...", "sonuc": "...",
     "kategori": "...", "etiketler": [...], "kaynak": "..."}
"""
from __future__ import annotations

import json
import os
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

#: Sekiz kategori — ad + örnek konu alanları + etiketler.
#: Kaynak: docs/ILGINC_BILGI_HATTI.md §2
KATEGORILER = {
    "bilim_teknoloji": {
        "ad": "Bilim ve Teknoloji", "emoji": "🔬",
        "ornek": "uzay, icatlar, internet, yapay zekâ, fizik, kimya, mühendislik",
        "etiket": ["#shorts", "#ilginçbilgi", "#bilim", "#teknoloji", "#bobitv"],
    },
    "tarih_medeniyet": {
        "ad": "Tarih ve Medeniyetler", "emoji": "🏛️",
        "ornek": "antik uygarlıklar, imparatorluklar, arkeoloji, tarihi olaylar",
        "etiket": ["#shorts", "#ilginçbilgi", "#tarih", "#medeniyet", "#bobitv"],
    },
    "doga_evren": {
        "ad": "Doğa ve Evren", "emoji": "🌌",
        "ornek": "gezegenler, okyanuslar, hava olayları, bitkiler, ekosistemler",
        "etiket": ["#shorts", "#ilginçbilgi", "#doğa", "#evren", "#bobitv"],
    },
    "hayvanlar": {
        "ad": "Hayvanlar ve Canlılar", "emoji": "🐾",
        "ornek": "hayvan davranışları, böcekler, deniz canlıları, kuşlar",
        "etiket": ["#shorts", "#ilginçbilgi", "#hayvanlar", "#doğa", "#bobitv"],
    },
    "insan_vucudu": {
        "ad": "İnsan Vücudu ve Biyoloji", "emoji": "🧬",
        "ornek": "beyin, uyku, bağışıklık, duyular, hücreler, evrim",
        "etiket": ["#shorts", "#ilginçbilgi", "#vücut", "#bilim", "#bobitv"],
    },
    "yiyecekler": {
        "ad": "Yiyecekler ve Beslenme", "emoji": "🍎",
        "ornek": "gıdaların tarihi, tat algısı, mutfak kimyası, baharatlar",
        "etiket": ["#shorts", "#ilginçbilgi", "#yemek", "#beslenme", "#bobitv"],
    },
    "kulturler": {
        "ad": "Kültürler ve Gelenekler", "emoji": "🌍",
        "ornek": "dünya gelenekleri, diller, inançlar, festivaller, yaşam biçimleri",
        "etiket": ["#shorts", "#ilginçbilgi", "#kültür", "#dünya", "#bobitv"],
    },
    "gunluk_yasam": {
        "ad": "Günlük Yaşam ve İlginç Olaylar", "emoji": "☕",
        "ornek": "ev eşyaları, alışkanlıklar, şehir hayatı, gündelik nesneler",
        "etiket": ["#shorts", "#ilginçbilgi", "#günlükyaşam", "#bobitv", "#bilim"],
    },
}

#: Arşiv dosyası — son kategoriler buradan okunur.
ARSIV = Path(__file__).resolve().parent.parent / "bobi_tv" / "archive" / "videos.json"

#: `docs/SABLON_ISTEM.md` §"MEVCUT ŞABLON" — birebir. Ekleme yok.
SABLON = """SADECE şu JSON ile cevap ver (şablonu tekrar yazma, doldur):
{{"soru":"...","cevap":"...","sonuc":"...","baslik":"...","kaynak":"...",
"sayilar":["..."],"dogru_bilgi":"...","kapak_baslik":"..."}}

Sen BOBİ TV için Türkçe kısa bilgi videoları yazan bir editörsün. YouTube
Shorts için 'ilginç bilgi' içeriği üretiyorsun. Aşağıdaki kategori ve taktiğe uy.

KATEGORİ: {ad} {emoji}
ÖRNEK KONU ALANLARI: {ornek}

ETKİLEŞİM TAKTİĞİ: {kod} — {tak_ad}
{tak_talimat}

YAZIM KURALLARI:
1) 'cevap' alanı 200-300 KELİME olmalı (ne az ne çok).
2) 'soru' merak uyandıran, tek cümlelik bir soru; cevabı içermez.
3) 'cevap' sohbet tonunda, 'sen' diliyle, sade Türkçe. İçinde günlük hayattan
   somut bir örnek/karşılaştırma olsun.
4) 'sonuc' 1-2 cümlelik şaşırtıcı kapanış; cevabı özetler.
5) 'baslik' en fazla 70 karakter, merak uyandıran, TÜMÜ BÜYÜK HARF DEĞİL,
   sonunda '#shorts' yok.
6) 'kaynak' gerçek bir kurum/kitap/dergi adı (NASA, Britannica, Nature, WHO,
   National Geographic...). Uydurma.
7) 'sayilar' cevapta geçen tüm sayıların listesi (metin olarak).
8) 'dogru_bilgi' cevabın 1-2 cümlelik ÖZETİ (yorum cevaplarında kullanılacak).
9) 'kapak_baslik' en fazla 34 karakter; çarpıcı ifade; EMOJI YOK.
10) Şu konulara YAKLAŞMA (daha önce yapıldı): {kacin}
11) TAMAMEN TÜRKÇE. İngilizce kelime yok.
12) Emoji kullan ama abartma (2-5 arası).
13) JSON dışında HİÇBİR ŞEY yazma; şablonu yankılama.
14) 'cevap' alanında bölüm başlığı (🧠/🔍/💡) KULLANMA; sadece metin yaz."""

#: 7 etkileşim taktiği — kod rotasyonu. Kaynak: docs/ILGINC_BILGI_HATTI.md §5
TAKTIKLER = {
    "T1": ("yaygın yanlış inanış",
           "İzleyicinin doğru sandığı bir şeyi nazikçe çürüt; doğrusunu göster."),
    "T2": ("cevabı boşluk bırak",
           "Cevabı başta verme, son cümlede kapat; merakı canlı tut."),
    "T3": ("sürçme + düzeltme",
           "Küçük bir yanlış söyle, aynı videoda düzelt. Sağlık/para/güvenlikte YASAK."),
    "T4": ("ters psikoloji",
           "Beklenenin tam tersini savun, sonra gerçeği göster. Sağlık/para/güvenlikte YASAK."),
    "T5": ("paradoksal gerçek",
           "İki doğru bilgiyi çarpıştır; sonuç şaşırtıcı olsun."),
    "T6": ("iki cevap / hangisi doğru",
           "İki olası açıklama sun, hangisinin doğru olduğunu sonda açıkla."),
    "T7": ("düzeltme / sabitlenmiş yorum",
           "Yaygın bir hatayı düzelt, izleyiciyi yoruma davet et."),
}

#: T3 ve T4 bu kategorilerde yasak (YouTube "deceptive practices" riski).
HASSAS = {"insan_vucudu", "yiyecekler"}


def gecmis_kategoriler(adet: int = 4) -> list[str]:
    """Arşivdeki son `adet` kaydın kategorisi."""
    try:
        veri = json.loads(ARSIV.read_text(encoding="utf-8"))
    except Exception:
        return []
    kayitlar = veri if isinstance(veri, list) else veri.get("videolar", [])
    return [str(k.get("kategori", "")) for k in kayitlar[-adet:] if k.get("kategori")]


def gecmis_basliklar(adet: int = 40) -> list[str]:
    """Tekrarı önlemek için son başlıklar."""
    try:
        veri = json.loads(ARSIV.read_text(encoding="utf-8"))
    except Exception:
        return []
    kayitlar = veri if isinstance(veri, list) else veri.get("videolar", [])
    return [str(k.get("baslik", ""))[:60] for k in kayitlar[-adet:] if k.get("baslik")]


def kategori_sec(video_no: int = 0) -> str:
    """Tekrarsız kategori: son 4'te çıkanı atla, kalanlardan rastgele."""
    gecmis = gecmis_kategoriler(4)
    adaylar = [k for k in KATEGORILER if k not in gecmis] or list(KATEGORILER)
    r = random.Random(video_no or None)
    return r.choice(adaylar)


def taktik_sec(kategori: str, video_no: int = 0) -> str:
    """Takfik rotasyonu: video_no mod 7. Hassas kategoride T3/T4 atlanır."""
    anahtarlar = list(TAKTIKLER)
    if kategori in HASSAS:
        anahtarlar = [k for k in anahtarlar if k not in ("T3", "T4")]
    return anahtarlar[(video_no or 0) % len(anahtarlar)]


def istem_yaz(kategori: str, taktik: str) -> str:
    """Şablonu doldurur. `docs/SABLON_ISTEM.md` ile birebir aynı metin."""
    k = KATEGORILER[kategori]
    kod, talimat = TAKTIKLER[taktik]
    kacin = ", ".join(gecmis_basliklar(40)) or "yok"
    return SABLON.format(
        ad=k["ad"], emoji=k["emoji"], ornek=k["ornek"],
        kod=taktik, tak_ad=kod, tak_talimat=talimat, kacin=kacin,
    )


def json_ayikla(metin: str) -> dict | None:
    """Gemini cevabından JSON'u çıkarır (```json çiti, ön/son söz olabilir)."""
    if not metin:
        return None
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", metin, re.S)
    if m:
        metin = m.group(1)
    else:
        i, j = metin.find("{"), metin.rfind("}")
        if i >= 0 and j > i:
            metin = metin[i:j + 1]
    try:
        d = json.loads(metin)
    except Exception:
        return None
    return d if isinstance(d, dict) and d.get("cevap") else None


def konu_uret(video_no: int = 0, kategori: str | None = None) -> dict | None:
    """Gemini web'den konu üretir. Başarısızsa None — UYDURMA YOK.

    Sabit konu havuzu ve yedek konu YOK (kullanıcı kararı 2026-11-15).
    """
    from modules.gemini_web import metin_uret

    kat = kategori or kategori_sec(video_no)
    tak = taktik_sec(kat, video_no)
    istem = istem_yaz(kat, tak)
    print(f"[konu] kategori={kat} taktik={tak} istem={len(istem)} krkt")

    ham = metin_uret(istem, sure=240)
    if not ham:
        print("[konu] ❌ Gemini cevap vermedi")
        return None

    d = json_ayikla(ham)
    if not d:
        print(f"[konu] ❌ JSON ayrıştırılamadı (ilk 200: {ham[:200]!r})")
        return None

    metin = str(d["cevap"]).strip()
    kelime = len(metin.split())
    if kelime < 120:
        print(f"[konu] ⚠️ cevap kısa: {kelime} kelime (hedef 200-300)")

    return {
        "baslik": str(d.get("baslik") or d.get("soru") or "İlginç Bilgi").strip()[:95],
        "metin": metin,
        "soru": str(d.get("soru", "")).strip(),
        "sonuc": str(d.get("sonuc", "")).strip(),
        "kaynak": str(d.get("kaynak", "")).strip(),
        "kapak_baslik": str(d.get("kapak_baslik", "")).strip(),
        "dogru_bilgi": str(d.get("dogru_bilgi", "")).strip(),
        "kategori": kat,
        "taktik": tak,
        "etiketler": KATEGORILER[kat]["etiket"],
        "kelime": kelime,
    }


def main() -> int:
    no = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    kat = sys.argv[2] if len(sys.argv) > 2 else None
    konu = konu_uret(no, kat)
    if not konu:
        return 1
    print(json.dumps(konu, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
