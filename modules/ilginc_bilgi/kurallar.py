"""12 içerik kuralı — her kural bir DENETİM fonksiyonudur.

KULLANICI KURALLARI (2026-11-11):
  1. Merak uyandıran soruyla başla
  2. Cevabı hemen verme
  3. Sonra anlaşılır sohbet tonunda açıkla
  4. Sıradan değil, az bilinen bilgi
  5. Doğru bilgi (→ `dogruluk.py`)
  6. Önceki konuları tekrar etme
  7. Günlük kategori geçişi (→ `kategoriler.py`)
  8. 200–300 kelime
  9. Günlük hayattan örnek/karşılaştırma
 10. Sade Türkçe
 11. Emoji kullan
 12. Tamamen Türkçe

ZORUNLU FORMAT:
  🧠 Günün Merak Uyandıran Sorusu
  🔍 Cevabı Biliyor Muydun?   ← 200–300 kelime
  💡 Şaşırtıcı Sonuç

TASARIM: her kural `(metin, baglam) -> Ihlal | None` imzasında bağımsız bir
fonksiyondur. Böylece hangi kuralın çiğnendiği **tek tek** raporlanabilir;
"kalite 68/100" gibi anlamsız tek sayı yerine "R8 ihlal: 187 kelime" gibi
düzeltilebilir çıktı verir.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

BASLIK_SORU = "🧠 Günün Merak Uyandıran Sorusu"
BASLIK_CEVAP = "🔍 Cevabı Biliyor Muydun?"
BASLIK_SONUC = "💡 Şaşırtıcı Sonuç"

ZORUNLU_BASLIKLAR = (BASLIK_SORU, BASLIK_CEVAP, BASLIK_SONUC)

# 2026-11-13 ŞABLON DEVRİMİ — ölçüme dayalı.
# ESKİ: 200-300 kelime → TTS ile 81-134 sn video.
# KANAL VERİSİ: 81-134 sn videolar 0-14 izlenme · 20-22 sn videolar 1.100-1.200.
# YENİ: 50-70 kelime → ~16-23 sn. Türkçe TTS ölçümü: 250 kelime/81 sn
# = 185 kelime/dk → 55 kelime ≈ 17.8 sn. Hedef bant 20-22 sn ile örtüşüyor.
KELIME_MIN = 50
KELIME_MAKS = 70

#: İngilizce işlev kelimeleri — "tamamen Türkçe" kuralını ihlal eder.
INGILIZCE_ISLEV = (
    " the ", " and ", " with ", " this ", " that ", " from ", " your ", " have ",
    " about ", " which ", " there ", " would ", " could ", " should ", " because ",
    " actually ", " however ", " therefore ", " we ", " they ", " you ", " is ",
    " are ", " was ", " were ", " of ", " to ", " in ", " on ", " for ",
)

#: Günlük hayat bağlantısı işaretleri (9. kural).
GUNLUK_IZLER = (
    "günlük", "her gün", "bir düşün", "mutfakta", "cebinde", "sabah", "evde",
    "telefonun", "markette", "kahve", "yürürken", "akşam", "elinde", "sofrada",
    "bir düşünün", "hepimiz", "çoğumuz", "sokakta", "işe giderken",
)

#: Sohbet tonu işaretleri (3. kural) — resmî/robotik metni yakalar.
SOHBET_IZLER = ("sen", "senin", "bak", "işte", "aslında", "hadi", "düşün", "gördün mü",
                "biliyor musun", "peki", "yani", "şöyle", "bir de")

#: Az bilinen bilgi işaretleri (4. kural).
SIradan_IZLER = (
    "herkes bilir", "bilinen bir şey", "malum", "tabii ki", "hepimizin bildiği",
    "çok bilinen", "klasik olarak",
)

EMOJI_RE = re.compile(
    "[" "\U0001F300-\U0001FAFF" "\U00002600-\U000027BF" "\U0001F1E6-\U0001F1FF"
    "\U00002190-\U000021FF" "\U00002B00-\U00002BFF" "\uFE0F" "]",
)

#: Türkçeye özgü harfler (Türkçe olduğunu kanıtlar).
TURKCE_HARFLER = set("çğıİöşüÇĞÖŞÜ")


@dataclass
class Ihlal:
    """Tek bir kural ihlali: hangi kural, ne bekleniyordu, ne bulundu."""

    kod: str
    kural: str
    ayrinti: str
    agirlik: int = 1  # 1 = uyarı, 2 = düzeltilmeli, 3 = yayınlanamaz

    def __str__(self) -> str:
        return f"[{self.kod}] {self.kural}: {self.ayrinti}"


@dataclass
class Rapor:
    ihlaller: list[Ihlal] = field(default_factory=list)
    gecen: list[str] = field(default_factory=list)

    @property
    def kritik(self) -> list[Ihlal]:
        return [i for i in self.ihlaller if i.agirlik >= 3]

    @property
    def yayinlanabilir(self) -> bool:
        """Ağırlık 3 ihlal yoksa yayınlanabilir (uyarılar kabul)."""
        return not self.kritik

    @property
    def skor(self) -> int:
        """0-100: ağırlıklı ihlal cezası (ölçüm için, karar için değil)."""
        ceza = sum(8 * i.agirlik for i in self.ihlaller)
        return max(0, 100 - ceza)

    def ozet(self) -> str:
        if not self.ihlaller:
            return "12/12 kural tamam"
        return "; ".join(str(i) for i in self.ihlaller)


# ---------------------------------------------------------------------------
# Bölüm ayrıştırma
# ---------------------------------------------------------------------------


def bolumleri_ayir(metin: str) -> dict[str, str]:
    """Metni 3 zorunlu başlığa göre böler. Eksik başlık → o anahtar yok."""
    metin = str(metin or "")
    konumlar: list[tuple[str, int]] = []
    for baslik in ZORUNLU_BASLIKLAR:
        i = metin.find(baslik)
        if i >= 0:
            konumlar.append((baslik, i))
    konumlar.sort(key=lambda x: x[1])
    sonuc: dict[str, str] = {}
    for sira, (baslik, bas) in enumerate(konumlar):
        son = konumlar[sira + 1][1] if sira + 1 < len(konumlar) else len(metin)
        sonuc[baslik] = metin[bas + len(baslik): son].strip()
    return sonuc


def kelime_say(metin: str) -> int:
    """Kelime sayısı: emoji ve noktalama sayılmaz."""
    temiz = EMOJI_RE.sub(" ", str(metin or ""))
    return len([k for k in re.split(r"\s+", temiz) if k.strip(" -–—•·…")])


# ---------------------------------------------------------------------------
# 12 kural denetimi
# ---------------------------------------------------------------------------


def k1_soru_ile_basla(metin: str, _b: dict, _bag: dict) -> Ihlal | None:
    """K1: Metin, merak uyandıran bir KANCA ile başlamalı (soru veya iddia)."""
    bolumler = bolumleri_ayir(metin)
    soru = bolumler.get(BASLIK_SORU, "").strip()
    if not soru:
        return Ihlal("R1", "Soru ile başla", "🧠 sorusu bölümü boş", 3)
    # 2026-11-13: '?' ZORUNLULUĞU KALDIRILDI.
    # GEREKÇE (kanal verisi): 20-22 sn'lik kazanan videoların 4'ü "Wi-Fi hırsızı
    # kim çıktı?", "Büyülü Ayna Sandı, Etiketi Görünce Şok" gibi SORU değil
    # İDDİA/OLAY kancası kullanıyor. '🧠 Günün Merak Uyandıran Sorusu' başlığı
    # zorunlu kalıyor (metin/görsel işaret) ama cümlenin soru olması şart değil.
    # Bunun yerine "kanca gücü" ölçülür: çok kısa veya boş olmasın.
    if kelime_say(soru) < 3:
        return Ihlal("R1", "Soru ile başla", f"soru çok kısa ({kelime_say(soru)} kelime)", 2)
    return None


def k2_cevabi_hemen_verme(metin: str, _b: dict, _bag: dict) -> Ihlal | None:
    """K2: Cevap, soru bölümünde verilmemeli (merak korunmalı)."""
    bolumler = bolumleri_ayir(metin)
    soru = bolumler.get(BASLIK_SORU, "")
    cevap = bolumler.get(BASLIK_CEVAP, "")
    if not cevap:
        return Ihlal("R2", "Cevabı hemen verme", "cevap bölümü yok", 3)
    # Cevap sızması: cevabın İLK CÜMLESİNDE sorunun sayıları tekrar ediyorsa,
    # cevap hemen verilmiş demektir (merak ölmüş). Yanıtın ilerisinde geçmesi
    # normaldir — bilgi orada açıklanır.
    ilk_cumle = re.split(r"[.!?…]", cevap)[0]
    sizan = set(re.findall(r"\d+", soru)) & set(re.findall(r"\d+", ilk_cumle))
    if sizan:
        return Ihlal(
            "R2", "Cevabı hemen verme",
            f"cevabın ilk cümlesinde sorunun sayısı ({sorted(sizan)[:2]}) geçiyor",
            2,
        )
    return None


def k3_sohbet_tonu(metin: str, _b: dict, _bag: dict) -> Ihlal | None:
    """K3: Anlaşılır, sohbet tonunda açıklama (resmî rapor dili değil)."""
    kucuk = " " + str(metin or "").lower() + " "
    if not any(i in kucuk for i in SOHBET_IZLER):
        return Ihlal("R3", "Sohbet tonu", "sohbet/sen dili izi yok (rapor gibi)", 2)
    resmi = ("tarafından gerçekleştirilmiştir", "söz konusudur", "bu bağlamda",
             "hususunda", "mütalaa")
    bulunan = [r for r in resmi if r in kucuk]
    if bulunan:
        return Ihlal("R3", "Sohbet tonu", f"resmî dil: {bulunan[:2]}", 2)
    return None


def k4_az_bilinen(metin: str, _b: dict, _bag: dict) -> Ihlal | None:
    """K4: Sıradan değil, az bilinen bilgi."""
    kucuk = str(metin or "").lower()
    for i in SIradan_IZLER:
        if i in kucuk:
            return Ihlal("R4", "Az bilinen bilgi", f"klişe ifade: '{i}'", 1)
    return None


def k5_dogruluk(metin: str, _b: dict, bag: dict) -> Ihlal | None:
    """K5: Doğruluk → `dogruluk.dogrula()` (kaynak, tehlike, çürütülmüş bilgi)."""
    from modules.ilginc_bilgi.dogruluk import dogrula

    sonuc = dogrula(
        metin,
        kaynak=str(bag.get("kaynak") or ""),
        sayi_listesi=bag.get("sayilar"),
        curutme_icerigi=bool(bag.get("curutme_icerigi")),
    )
    if not sonuc.gecti:
        return Ihlal("R5", "Doğruluk", sonuc.ret_sebebi, 3)
    return None


def k6_tekrar_etme(metin: str, _b: dict, bag: dict) -> Ihlal | None:
    """K6: Önceki konuları tekrar etme (kelime örtüşmesi ile)."""
    onceki = bag.get("onceki_metinler") or []
    if not onceki:
        return None
    yeni = _anlamli_kelimeler(metin)
    for eski in onceki[-30:]:
        eski_k = _anlamli_kelimeler(str(eski))
        if not eski_k or not yeni:
            continue
        ortak = len(yeni & eski_k) / max(1, min(len(yeni), len(eski_k)))
        if ortak > 0.55:
            return Ihlal("R6", "Tekrar etme", f"önceki bir videoyla %{ortak*100:.0f} örtüşüyor", 3)
    return None


def k7_kategori_gecisi(metin: str, _b: dict, bag: dict) -> Ihlal | None:
    """K7: Günlük kategori geçişi — son videolarda çıkan kategori tekrar etmesin."""
    kategori = str(bag.get("kategori") or "")
    son = [str(k) for k in (bag.get("son_kategoriler") or [])][:4]
    if kategori and kategori in son:
        return Ihlal("R7", "Kategori geçişi", f"'{kategori}' son 4 videoda vardı", 2)
    return None


def k8_kelime_sayisi(metin: str, bolumler: dict, _bag: dict) -> Ihlal | None:
    """K8: 50-70 kelime (cevap bölümü esas alınır). 2026-11-13: 200-300 → 50-70."""
    cevap = bolumler.get(BASLIK_CEVAP, "")
    if not cevap:
        return Ihlal("R8", "200-300 kelime", "cevap bölümü yok", 3)
    n = kelime_say(cevap)
    if n < KELIME_MIN:
        return Ihlal("R8", f"{KELIME_MIN}-{KELIME_MAKS} kelime", f"{n} kelime (< {KELIME_MIN})", 3)
    if n > KELIME_MAKS:
        return Ihlal("R8", f"{KELIME_MIN}-{KELIME_MAKS} kelime", f"{n} kelime (> {KELIME_MAKS})", 2)
    return None


def k9_gunluk_ornek(metin: str, _b: dict, bag: dict) -> Ihlal | None:
    """K9: Günlük hayattan örnek/karşılaştırma."""
    if bag.get("gunluk_ornek"):
        return None
    kucuk = str(metin or "").lower()
    if not any(i in kucuk for i in GUNLUK_IZLER):
        return Ihlal("R9", "Günlük hayat örneği", "günlük hayat bağlantısı yok", 2)
    return None


def k10_sade_turkce(metin: str, _b: dict, _bag: dict) -> Ihlal | None:
    """K10: Sade Türkçe — cümle uzunluğu ve ağır kelimeler."""
    cumleler = [c for c in re.split(r"[.!?…]+", str(metin or "")) if len(c.split()) > 2]
    if not cumleler:
        return Ihlal("R10", "Sade Türkçe", "cümle bulunamadı", 3)
    ortalama = sum(len(c.split()) for c in cumleler) / len(cumleler)
    if ortalama > 26:
        return Ihlal("R10", "Sade Türkçe", f"ortalama cümle {ortalama:.0f} kelime (>26)", 2)
    # Tek bir cümle bile çok uzunsa sadelik bozulur (sesli okumada nefes kaçar)
    en_uzun = max(len(c.split()) for c in cumleler)
    if en_uzun > 35:
        return Ihlal("R10", "Sade Türkçe", f"tek cümle {en_uzun} kelime (>35)", 2)
    agir = ("müteakiben", "hasebiyle", "külliyat", "müstesna", "bilahare", "akabinde")
    kucuk = str(metin or "").lower()
    bulunan = [a for a in agir if a in kucuk]
    if bulunan:
        return Ihlal("R10", "Sade Türkçe", f"ağır kelime: {bulunan[:2]}", 2)
    return None


def k11_emoji(metin: str, _b: dict, _bag: dict) -> Ihlal | None:
    """K11: Emoji kullanımı (en az 2, en fazla 12 — spam görünmesin)."""
    n = len(EMOJI_RE.findall(str(metin or "")))
    if n < 2:
        return Ihlal("R11", "Emoji", f"{n} emoji (en az 2)", 1)
    if n > 12:
        return Ihlal("R11", "Emoji", f"{n} emoji (çok fazla, emoji çorbası)", 2)
    return None


def k12_tamamen_turkce(metin: str, _b: dict, _bag: dict) -> Ihlal | None:
    """K12: Tamamen Türkçe (İngilizce işlev kelimesi veya Latin harf yığını yok)."""
    kucuk = " " + re.sub(r"\s+", " ", str(metin or "")).lower() + " "
    bulunan = [i.strip() for i in INGILIZCE_ISLEV if i in kucuk]
    if bulunan:
        return Ihlal("R12", "Tamamen Türkçe", f"İngilizce kelime: {bulunan[:4]}", 3)
    harfler = set(str(metin or ""))
    if len(harfler & TURKCE_HARFLER) < 3 and kelime_say(metin) > 60:
        return Ihlal("R12", "Tamamen Türkçe", "Türkçe karakter yok (çeviri metin?)", 2)
    return None


def _anlamli_kelimeler(metin: str) -> set[str]:
    """Tekrar karşılaştırması için gövde kelimeler (ilk 3 harf, kısa/boş kelime yok)."""
    dur = {
        "bir", "bu", "şu", "ve", "ile", "için", "ama", "çok", "daha", "en", "de",
        "da", "ki", "mi", "ne", "o", "her", "gibi", "kadar", "sonra", "önce",
        "olan", "olarak", "var", "yok", "ise", "hem", "ya", "veya", "diye",
    }
    kucuk = str(metin or "").lower().replace("’", "").replace("'", "")
    kelimeler = re.findall(r"[a-zçğıöşü]{4,}", kucuk)
    return {k[:4] for k in kelimeler if k not in dur}


#: Kural tablosu: kod → (ad, fonksiyon)
KURAL_TABLOSU = (
    ("R1", "Soru ile başla", k1_soru_ile_basla),
    ("R2", "Cevabı hemen verme", k2_cevabi_hemen_verme),
    ("R3", "Sohbet tonu", k3_sohbet_tonu),
    ("R4", "Az bilinen bilgi", k4_az_bilinen),
    ("R5", "Doğruluk", k5_dogruluk),
    ("R6", "Tekrar etme", k6_tekrar_etme),
    ("R7", "Kategori geçişi", k7_kategori_gecisi),
    ("R8", "200-300 kelime", k8_kelime_sayisi),
    ("R9", "Günlük hayat örneği", k9_gunluk_ornek),
    ("R10", "Sade Türkçe", k10_sade_turkce),
    ("R11", "Emoji", k11_emoji),
    ("R12", "Tamamen Türkçe", k12_tamamen_turkce),
)


def format_dogrula(metin: str) -> list[Ihlal]:
    """Zorunlu 3 başlık sırayla var mı?"""
    metin = str(metin or "")
    ihlaller = []
    konumlar = []
    for baslik in ZORUNLU_BASLIKLAR:
        i = metin.find(baslik)
        if i < 0:
            ihlaller.append(Ihlal("F", "Zorunlu format", f"başlık eksik: {baslik}", 3))
        else:
            konumlar.append(i)
    if len(konumlar) == 3 and konumlar != sorted(konumlar):
        ihlaller.append(Ihlal("F", "Zorunlu format", "başlıklar yanlış sırada", 3))
    return ihlaller


def denetle(metin: str, **baglam) -> Rapor:
    """12 kuralı + formatı denetler.

    Bağlam anahtarları: kaynak, sayilar, kategori, son_kategoriler,
    onceki_metinler, gunluk_ornek, curutme_icerigi.
    """
    rapor = Rapor()
    bolumler = bolumleri_ayir(metin)
    rapor.ihlaller.extend(format_dogrula(metin))
    for kod, ad, fn in KURAL_TABLOSU:
        try:
            ihlal = fn(metin, bolumler, baglam)
        except Exception as e:  # tek kural çökerse denetim sürsün
            ihlal = Ihlal(kod, ad, f"denetim hatası: {str(e)[:60]}", 1)
        if ihlal:
            rapor.ihlaller.append(ihlal)
        else:
            rapor.gecen.append(kod)
    return rapor
