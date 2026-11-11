"""BOBİ TV — Kanca motoru (hook) v8: ölçülebilir, veri odaklı ilk 1.5 saniye.

NEDEN YENİDEN YAZILDI (2026-11-11)
----------------------------------
Eski motor (`hook_engineer.py`) puan hesaplıyordu ama:
  1. Formlar ZAYIFTI: "`{temiz} mi?`", "Bakın: ..." gibi kalıplar gerçek bir
     merak boşluğu kurmuyordu; kanca puana %25 ağırlıkla giriyordu, yani
     kötü kanca 100'lük skalada ~25 puan kaybettiriyordu.
  2. Sayı formu **rastgele sayı** ekliyordu (`random.choice([3,5,7,10])`) —
     uydurma veri, yasak.
  3. Önerilen varyant hiçbir yere YAZILMIYORDU: `onerilen_varyant` alanı
     dolduruluyor, senaryoya uygulanmıyordu. Yani motorun tüm çıktısı süstü.

BU MODÜL NE YAPAR
-----------------
- 5 kanca formu (soru / iddia / sayı / itiraf / sahne) — hepsi ŞABLON, uydurma
  sayı yok: sayı formu yalnız metinde GEÇEN sayıyı kullanır.
- Ölçülebilir puan: kelime sayısı (≤12), karakter (≤70), yasaklı kelime yok,
  ilk kelime güçlü mü, merak boşluğu işareti var mı (?, :, —), somut özne var mı.
- `en_iyi_kanca()` → senaryoyu UYGULANABİLİR şekilde günceller
  (`hook_ust_bant`, `hook_metni`, `tts_metinleri[0]`).
- A/B grubu (A/B/C) senaryoya yazılır; performans raporu hangi formun
  kazandığını ölçebilir (`kanca_formu` alanı).

KURAL: kanca metni UYDURMA OLGU içermez. Yalnız senaryonun kendi cümlesinden
türetilir; sayı uydurulmaz.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

#: İlk 1.5 saniyede söylenebilecek azami kelime.
MAKS_KELIME = 12
#: Üst bantta okunabilir azami karakter (mobilde kesilmesin).
MAKS_KARAKTER = 70
#: Kanca kabul eşiği (kalite kapısı 70 kullanıyor; kanca daha sıkı).
KANCA_ESIGI = 75

#: Clickbait/abartı — kullanılırsa puan kırılır (YouTube "misleading" riski).
YASAKLI = {
    "şok", "şaşırmayın", "inanamayacaksınız", "muhteşem", "inanılmaz",
    "harika", "mükemmel", "en iyi", "en kötü", "dünyanın en", "izlemelisiniz",
    "kaçırmayın", "hemen izleyin", "bomba", "sırrı", "gizli", "sonunda",
}

#: Kanca açılışında güçlü duran ilk kelimeler (merak/somutluk taşır).
GUCLU_ACILISLAR = {
    "bir", "bu", "ben", "beni", "benim", "sen", "seni", "kimse", "herkes",
    "neden", "nasıl", "niye", "ne", "kaç", "asla", "artık", "dün",
    "bugün", "sabah", "gece", "patron", "müdür", "doktor", "kasiyer", "komşu",
}

#: Yumuşatma sözlüğü (yasaklı kelime → kabul edilebilir karşılık).
YUMUSATMA = {
    "şok": "beklenmedik", "şaşırmayın": "dikkat", "inanamayacaksınız": "göreceksiniz",
    "muhteşem": "iyi", "inanılmaz": "şaşırtıcı", "harika": "iyi",
    "mükemmel": "başarılı", "en iyi": "başarılı", "en kötü": "başarısız",
    "bomba": "önemli", "sırrı": "detayı", "gizli": "bilinmeyen",
    "sonunda": "sonrasında", "izlemelisiniz": "bakın", "kaçırmayın": "kaçmayın",
    "hemen izleyin": "izleyin", "dünyanın en": "çok",
}


@dataclass
class KancaAdayi:
    """Tek kanca adayı + puanı + gerekçesi."""

    metin: str
    form: str  # soru | iddia | sayi | itiraf | sahne
    ab_grubu: str = "A"
    puan: int = 0
    gerekce: str = ""
    yasakli: list[str] = field(default_factory=list)

    @property
    def gecerli(self) -> bool:
        return not self.yasakli and self.puan >= KANCA_ESIGI


@dataclass
class KancaSonucu:
    """Senaryo için seçilen kanca + tüm adaylar (ölçüm/depolama için)."""

    secilen: KancaAdayi | None
    adaylar: list[KancaAdayi] = field(default_factory=list)
    uygulandi: bool = False
    gerekce: str = ""
    eski_ust_bant: str = ""

    @property
    def puan(self) -> int:
        return self.secilen.puan if self.secilen else 0

    def ozet(self) -> str:
        if not self.secilen:
            return "kanca: aday üretilemedi (metin boş)"
        return (
            f"kanca: {self.secilen.form} ({self.secilen.puan}/100, "
            f"A/B {self.secilen.ab_grubu}) → \"{self.secilen.metin}\""
        )


# ---------------------------------------------------------------------------
# Metin yardımcıları
# ---------------------------------------------------------------------------


def _temizle(metin: str) -> str:
    """Tırnak/boşluk/bitiş noktalama temizliği."""
    t = re.sub(r"\s+", " ", str(metin or "")).strip()
    t = t.strip("\"'„“”‘’ ")
    return t.rstrip(".!…")


def _cumle_parcasi(metin: str, azami_kelime: int = 10) -> str:
    """Uzun cümleyi ilk `azami_kelime` kelimeye indirger (anlamı bozmadan).

    Bitiş noktalaması ("?", "!", "...") temizlenir: form üreticisi kendi
    noktalamasını ekler — aksi hâlde üst üste uygulanan formlar
    "...açıkladı? — ve bu gerçekten oldu?" gibi bozuk metin üretir.
    """
    kelimeler = _temizle(metin).rstrip("?!… ").split()
    if len(kelimeler) <= azami_kelime:
        return " ".join(kelimeler)
    return " ".join(kelimeler[:azami_kelime])


def yasakli_bul(metin: str) -> list[str]:
    kucuk = _temizle(metin).lower()
    return sorted({y for y in YASAKLI if y in kucuk})


def yumusat(metin: str) -> str:
    """Yasaklı/clickbait kelimeleri kabul edilebilir karşılıklarına çevirir.

    Eski motor bunu ÖNERİ olarak yazıyordu (uygulanmıyordu); artık metne
    uygulanır. Böylece aday "yasaklı var" diye ölmez, düzelir.
    """
    sonuc = _temizle(metin)
    for yasakli in sorted(YASAKLI, key=len, reverse=True):
        yumusak = YUMUSATMA.get(yasakli, "")
        if not yumusak or yasakli not in sonuc.lower():
            continue
        # Cümlenin BAŞINDA ise ilk harf büyük kalır (Türkçe cümle kuralı):
        # "ŞOK! ..." → "Beklenmedik! ..." (eskiden "beklenmedik!" oluyordu)
        bas = sonuc.lower().startswith(yasakli)
        yerine = yumusak[0].upper() + yumusak[1:] if bas else yumusak
        sonuc = re.sub(re.escape(yasakli), yerine, sonuc, flags=re.IGNORECASE)
    return _temizle(sonuc)


# ---------------------------------------------------------------------------
# Form üreticileri — hepsi senaryonun KENDİ cümlesinden türetilir
# ---------------------------------------------------------------------------


def _soru_formu(cumle: str) -> str | None:
    temel = _cumle_parcasi(cumle)
    if not temel:
        return None
    if temel.endswith("?"):
        return temel
    return f"{temel}?"


def _iddia_formu(cumle: str) -> str | None:
    temel = _cumle_parcasi(cumle)
    if not temel:
        return None
    return f"{temel} — ve bu gerçekten oldu"


def _sayi_formu(cumle: str) -> str | None:
    """Yalnız metinde GEÇEN sayıyı kullanır (uydurma sayı yok)."""
    temel = _cumle_parcasi(cumle)
    if not temel:
        return None
    sayilar = re.findall(r"\d+", temel)
    if not sayilar:
        return None  # sayı yoksa bu form URETILMEZ (eskiden rastgele ekliyordu)
    return temel


def _itiraf_formu(cumle: str) -> str | None:
    """Birinci ağızdan itiraf: "Benim başıma geldi: ..." — her cümleye uyar.

    (Önceki sürüm cümlenin ilk harfini küçültüyordu: "Ben şOK!" gibi bozuk
    metin üretiyordu.)
    """
    temel = _cumle_parcasi(cumle, 9)
    if not temel:
        return None
    if temel.lower().startswith(("ben ", "beni ", "benim ")):
        return temel
    return f"Benim başıma geldi: {temel}"


def _sahne_formu(cumle: str) -> str | None:
    """Somut sahne: ilk cümleyi 'an' hissiyle verir (en sade, en güvenli form)."""
    temel = _cumle_parcasi(cumle, 12)
    if not temel:
        return None
    return temel if len(temel.split()) <= MAKS_KELIME else _cumle_parcasi(cumle, 9)


FORM_URETICILERI = (
    ("soru", _soru_formu, "A"),
    ("iddia", _iddia_formu, "B"),
    ("itiraf", _itiraf_formu, "A"),
    ("sahne", _sahne_formu, "C"),
    ("sayi", _sayi_formu, "B"),
)

#: Rotasyon sırası — her video bir sonraki formu dener (A/B öğrenmesi).
ROTASYON = ("soru", "sahne", "iddia", "itiraf")


def siradaki_form(video_no: int | None = None) -> str:
    """Video numarasına göre SIRADAKİ form (deterministik, rastgele değil).

    Neden: her videoda aynı formu (ör. hep soru) kullanırsak hangi formun
    daha iyi çalıştığını ASLA öğrenemeyiz. Rotasyon + `kanca_formu` kaydı
    sayesinde performans raporu form bazında karşılaştırma yapabilir.
    """
    try:
        n = int(video_no or 0)
    except Exception:
        n = 0
    return ROTASYON[n % len(ROTASYON)]


# ---------------------------------------------------------------------------
# Puanlama — her ölçüt açık ve test edilebilir
# ---------------------------------------------------------------------------


def puanla(metin: str) -> tuple[int, str]:
    """0-100 kanca puanı + kısa gerekçe (uydurma yok, ölçütler yazılı)."""
    temiz = _temizle(metin)
    if not temiz:
        return 0, "boş metin"
    kelimeler = temiz.split()
    puan = 100
    sebepler: list[str] = []

    yasakli = yasakli_bul(temiz)
    if yasakli:
        puan -= 25 * len(yasakli)
        sebepler.append(f"yasaklı: {', '.join(yasakli)}")

    if len(kelimeler) > MAKS_KELIME:
        puan -= 15
        sebepler.append(f"{len(kelimeler)} kelime (>12)")
    if len(temiz) > MAKS_KARAKTER:
        puan -= 10
        sebepler.append(f"{len(temiz)} karakter (>70)")

    ilk = kelimeler[0].lower().strip(",.!?") if kelimeler else ""
    if ilk in GUCLU_ACILISLAR:
        puan += 5
    else:
        puan -= 5
        sebepler.append("zayıf açılış kelimesi")

    # Merak boşluğu işareti: soru, iki nokta, tire, üç nokta
    if any(isaret in temiz for isaret in ("?", ":", "—", "...")):
        puan += 5
    else:
        sebepler.append("merak işareti yok")

    # Somutluk: en az bir büyük harfle başlamayan somut isim/kişi izi
    if re.search(r"\b(patron|müdür|doktor|komşu|kasiyer|öğretmen|garson|"
                 r"asansör|fatura|kahve|telefon|toplantı|kapı|market)\b", temiz.lower()):
        puan += 5

    puan = max(0, min(100, puan))
    return puan, "; ".join(sebepler) if sebepler else "tüm ölçütler uygun"


def aday_uret(cumle: str) -> list[KancaAdayi]:
    """Bir cümleden tüm kanca formlarını üretir ve puanlar."""
    adaylar: list[KancaAdayi] = []
    gorulen: set[tuple[str, str]] = set()
    for form, uretici, grup in FORM_URETICILERI:
        metin = uretici(yumusat(cumle) or cumle)
        if not metin:
            continue
        metin = _temizle(metin)
        # Tekrar denetimi FORM bazında: iki farklı form aynı metni üretebilir
        # (sahne/sayı). Form bazında silmek rotasyonu bozardı.
        if (form, metin.lower()) in gorulen:
            continue
        gorulen.add((form, metin.lower()))
        puan, gerekce = puanla(metin)
        adaylar.append(
            KancaAdayi(
                metin=metin,
                form=form,
                ab_grubu=grup,
                puan=puan,
                gerekce=gerekce,
                yasakli=yasakli_bul(metin),
            )
        )
    # En iyi aday önce: geçerli olanlar, sonra puan
    adaylar.sort(key=lambda a: (a.gecerli, a.puan), reverse=True)
    return adaylar


# ---------------------------------------------------------------------------
# Senaryoya uygulama (eski motorda EKSİK olan adım)
# ---------------------------------------------------------------------------


def _ilk_cumle(senaryo: Any) -> str:
    """Senaryodan kanca kaynağı: ilk replik, yoksa hook metni, yoksa başlık."""
    for alan in ("hook_metni", "hook_ust_bant"):
        deger = str(getattr(senaryo, alan, "") or "").strip()
        if deger:
            return deger
    tts = getattr(senaryo, "tts_metinleri", None) or []
    if tts:
        return str(tts[0])
    diyaloglar = getattr(senaryo, "diyaloglar", None) or []
    if diyaloglar:
        ilk = diyaloglar[0]
        return str(getattr(ilk, "metin", "") or (ilk.get("metin", "") if isinstance(ilk, dict) else ""))
    return str(getattr(senaryo, "baslik", "") or "")


def en_iyi_kanca(
    senaryo: Any,
    uygula: bool = True,
    tercih_form: str | None = None,
    video_no: int | None = None,
) -> KancaSonucu:
    """Senaryo için en iyi kancayı seçer ve (varsayılan) senaryoya UYGULAR.

    Uygulama adımları:
      1. `hook_ust_bant` = seçilen kanca (üst bant metni).
      2. `hook_metni` = aynı metin (ilk saniye konuşması).
      3. `tts_metinleri[0]` kancayla başlamıyorsa kanca ile değiştirilir.
      4. `kanca_formu` / `kanca_ab` alanları yazılır (performans ölçümü için).
    """
    kaynak = _ilk_cumle(senaryo)
    eski = str(getattr(senaryo, "hook_ust_bant", "") or "")
    adaylar = aday_uret(kaynak)
    if not adaylar:
        return KancaSonucu(secilen=None, adaylar=[], gerekce="aday üretilemedi",
                           eski_ust_bant=eski)

    # Tercih edilen form (A/B rotasyonu) varsa onun en iyi adayı seçilir;
    # geçerli değilse genel en iyi adaya düşülür (kalite her zaman önce).
    istenen = tercih_form or siradaki_form(video_no)
    form_adaylari = [a for a in adaylar if a.form == istenen]
    if form_adaylari and form_adaylari[0].gecerli:
        secilen = form_adaylari[0]
    else:
        secilen = next((a for a in adaylar if a.gecerli), adaylar[0])
    sonuc = KancaSonucu(
        secilen=secilen,
        adaylar=adaylar,
        eski_ust_bant=eski,
        gerekce=secilen.gerekce,
    )
    if not uygula or not secilen.gecerli:
        return sonuc

    try:
        senaryo.hook_ust_bant = secilen.metin
        senaryo.hook_metni = secilen.metin
        tts = list(getattr(senaryo, "tts_metinleri", None) or [])
        if tts:
            # Spoken hook = seçilen kanca (aynı cümle; soru formunda "?" eklenir).
            tts[0] = secilen.metin
            senaryo.tts_metinleri = tts
        # Ölçüm alanları (dataclass'ta yoksa sessizce atlanır)
        if hasattr(senaryo, "kanca_formu"):
            senaryo.kanca_formu = secilen.form
        if hasattr(senaryo, "kanca_ab"):
            senaryo.kanca_ab = secilen.ab_grubu
        sonuc.uygulandi = True
    except Exception as e:  # noqa: BLE001 - uygulama başarısızsa kanca değişmez
        sonuc.gerekce = f"uygulanamadı: {str(e)[:80]}"

    return sonuc


def kanca_raporu(senaryo: Any) -> dict[str, Any]:
    """Senaryonun kancasını ölçer (değiştirmeden) — test/panel için."""
    kaynak = _ilk_cumle(senaryo)
    adaylar = aday_uret(kaynak)
    secilen = next((a for a in adaylar if a.gecerli), adaylar[0] if adaylar else None)
    return {
        "kaynak": kaynak[:120],
        "aday_sayisi": len(adaylar),
        "secilen": secilen.metin if secilen else "",
        "form": secilen.form if secilen else "",
        "puan": secilen.puan if secilen else 0,
        "gecerli": bool(secilen and secilen.gecerli),
        "adaylar": [
            {"metin": a.metin, "form": a.form, "puan": a.puan, "gecerli": a.gecerli}
            for a in adaylar[:5]
        ],
    }


# ---------------------------------------------------------------------------
# PAKET (dict) üzerinde uygulama — üretim hattının çağırdığı giriş noktası
# ---------------------------------------------------------------------------


def paket_kancasini_uygula(paket: dict, video_no: int | None = None) -> dict:
    """Üretim paketinin kancasını seçer ve UYGULAR (dict üzerinde çalışır).

    Neden dict: `arena_api.arena_video_uret` paketi sözlük olarak taşıyor ve
    TTS/render bu sözlüğü okuyor. Burada senaryonun şu alanları yazılır:
      hook_ust_bant (üst bant), hook_metni, kanca_formu, kanca_ab,
      tts_metinleri[0] ve (varsa) ilk diyalog metni.

    Döner: ölçüm özeti (kalite loguna yazılır): {"form","puan","metin","uygulandi"}
    Hiçbir koşulda exception fırlatmaz — kanca yüzünden üretim durmaz.
    """
    ozet = {"form": "", "puan": 0, "metin": "", "uygulandi": False, "gerekce": ""}
    try:
        senaryo = paket.get("senaryo")
        if not isinstance(senaryo, dict):
            ozet["gerekce"] = "senaryo sözlük değil"
            return ozet

        # Kanca kaynağı: ÖZGÜN kaynak (tekrar uygulamada kendini çoğaltmasın)
        kaynak = str(senaryo.get("kanca_kaynak") or "").strip()
        if not kaynak:
            kaynak = str(
                senaryo.get("hook_ust_bant")
                or senaryo.get("hook_metni")
                or ""
            ).strip()
            if kaynak:
                senaryo["kanca_kaynak"] = kaynak
        if not kaynak:
            diyaloglar = senaryo.get("diyaloglar") or []
            if diyaloglar and isinstance(diyaloglar[0], dict):
                kaynak = str(diyaloglar[0].get("metin") or "").strip()
        if not kaynak:
            ozet["gerekce"] = "kanca kaynağı boş"
            return ozet

        adaylar = aday_uret(kaynak)
        if not adaylar:
            ozet["gerekce"] = "aday üretilemedi"
            return ozet

        istenen = siradaki_form(video_no)
        form_adaylari = [a for a in adaylar if a.form == istenen]
        if form_adaylari and form_adaylari[0].gecerli:
            secilen = form_adaylari[0]
        else:
            secilen = next((a for a in adaylar if a.gecerli), adaylar[0])

        senaryo["hook_ust_bant"] = secilen.metin
        senaryo["hook_metni"] = secilen.metin
        senaryo["kanca_formu"] = secilen.form
        senaryo["kanca_ab"] = secilen.ab_grubu
        senaryo["kanca_puan"] = secilen.puan

        tts = senaryo.get("tts_metinleri")
        if isinstance(tts, list) and tts:
            tts[0] = secilen.metin

        # İlk replik = kanca (izleyicinin duyduğu ilk 1.5 saniye budur).
        # "sahne" formunda metin zaten aynıdır; diğer formlarda kanca konuşulur.
        diyaloglar = senaryo.get("diyaloglar")
        if isinstance(diyaloglar, list) and diyaloglar and isinstance(diyaloglar[0], dict):
            diyaloglar[0]["metin"] = secilen.metin

        ozet.update(
            form=secilen.form,
            puan=secilen.puan,
            metin=secilen.metin,
            uygulandi=True,
            gerekce=secilen.gerekce,
        )
        paket["kanca_ozeti"] = ozet
        return ozet
    except Exception as e:  # noqa: BLE001 - kanca hatası üretimi durdurmaz
        ozet["gerekce"] = f"hata: {str(e)[:100]}"
        return ozet
