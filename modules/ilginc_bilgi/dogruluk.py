"""Doğruluk motoru — "uydurma bilgi yok" kuralının kod hâli.

KULLANICI KURALI (2026-11-11): "Doğruluk" 12 içerik kuralının 5.'si;
ayrıca "uydurma bilgi yok" kabul kriteri. Ama "bilimsel doğruluk zinciri"
gevşetildi: "Kafanı kullan. Bazı şeyleri tamamen doğru ver. Küçük aptalca
hatacıklar olabilir, bilinçli, her zaman değil."

BU MODÜLÜN İŞİ: içeriğin DOĞRU olup olmadığını DENETLEMEK değil (LLM
kendini denetleyemez), **doğrulanabilir olmasını SAĞLAMAK**:

1. **Kaynak zorunluluğu.** Her bilgi kartı `kaynak` (kurum/kitap/dergi adı)
   taşımak zorundadır. Kaynak uydurulamaz → Arena'ya "sadece iyi bilinen,
   kaynağı adlandırılabilir bilgi" talimatı gider; kaynak alanı boşsa kart
   REDDEDİLİR.
2. **Aşırı iddia filtresi.** "asla", "her zaman", "kanıtlanmıştır", "%100",
   "kesinlikle" gibi kesinlik ifadeleri tespit edilir; bunların **en fazla
   1 tanesi** kullanılabilir (abartılı ton = güven kaybı + yanlış olma riski).
3. **Sayı denetimi.** Metindeki sayılar `sayilar` listesiyle uyuşmalı; sayı
   varsa ama kaynak yoksa kart reddedilir.
4. **Tıbbi/finansal iddia kara listesi.** "tedavi eder", "kanseri yener",
   "garanti kazanç", "kesin çözüm" → RED (T3/T4 taktikleriyle birlikte de
   yasak; bu konularda sürçme = gerçek zarar).
5. **Şüpheli bilgi bankası.** Bilimde düzeltilmiş, ama hâlâ dolaşan yaygın
   yanlışlar (dil yalanı, %10 beyin, at nalı yengeci kanı vb.) ID listesi
   olarak tutulur; içerik bunlardan birini "gerçek" diye sunarsa RED.

Bu modül "doğru mu?" sorusuna cevap vermez; "doğrulanabilir biçimde mi
sunulmuş?" sorusuna cevap verir — ve asıl risk orada.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

#: Kesinlik/abartı ifadeleri (en fazla 1 tanesi kullanılabilir).
ABARTI_IFADELERI = (
    "asla", "her zaman", "kesinlikle", "kanıtlanmıştır", "ispatlanmıştır",
    "yüzde yüz", "%100", "tartışmasız", "tüm bilim dünyası", "hiç kimse bilmiyor",
    "şok edici gerçek", "kimsenin bilmediği",
)

#: Tıbbi / finansal / güvenlik iddiaları — bu metinler içerikte GEÇEMEZ.
#: (T3 sürçme ve T4 ters psikoloji de bu kategorilerde yasak.)
TEHLIKELI_IDDIALAR = (
    "tedavi eder", "tedavi ediyor", "kanseri yener", "kanseri önler", "hastalığı iyileştirir",
    "doktora gerek yok", "ilacı bırakın", "kesin çözüm", "garanti kazanç",
    "kesin kazanç", "zengin olursunuz", "hızlı para", "risksiz yatırım",
    "kesin sonuç", "her derde deva", "mucize", "ölümcül tehlike yok",
)

#: Bilimde ÇÜRÜTÜLMÜŞ ama hâlâ dolaşan bilgiler. İçerik bunları "gerçek"
#: diye sunamaz. (Bunları ÇÜRÜTEN içerik yapmak serbest ve T1 taktiğinin
#: en güçlü malzemesidir — `curutulebilir` alanı bunun için var.)
CURUTULMUS_BILGILER = {
    "beyin_yuzde10": ["beyninin %10", "beynin %10", "beynimizin %10", "%10unu kullanıyoruz"],
    "dil_bolgeleri": ["dilin farklı bölgeleri", "tat haritası", "dil haritası"],
    "at_nali_yengec": ["at nalı yengecinin kanı mavi", "yengecin kanı mavidir",
                        "at nalı yengeci mavi kan"],
    "sakiz_7_yil": ["sakız 7 yıl", "7 yıl sindirilmez"],
    "tiras_klil": ["tıraş kılı kalınlaştırır", "tıraş kılı gürleştirir"],
    "besin_5_saniye": ["5 saniye kuralı", "yerden alınca bakteri"],
    "altin_balik_hafiza": ["altın balık 3 saniye", "balıkların hafızası 3"],
    "kopek_renk_gormez": ["köpekler renk görmez", "köpekler sadece siyah beyaz"],
    "uranyum_kaşık": ["uranyum kaşık", "radyoaktif kaşık"],
    "napolyon_kisa": ["napolyon çok kısaydı", "napolyon kısa boylu"],
    "einstein_matematik": ["einstein matematikte zayıftı", "einstein sınıfta kal"],
    "viking_boynuz": ["vikinglerin miğferinde boynuz", "viking boynuzlu miğfer"],
    "buyuk_set_duvar": ["çin seddi uzaydan görünür", "uzaydan görülen tek yapı"],
    "kan_mavi_damar": ["damarlardaki kan mavidir", "toplardamar kanı mavi"],
}

#: Kaynak göstergesi sayılan ifadeler (kart `kaynak` alanını doldurmalı).
_ZAYIF_KAYNAKLAR = ("internette okudum", "bir yerde gördüm", "herkes bilir", "rivayet")


@dataclass
class DogrulamaSonucu:
    """Doğrulama çıktısı: geçti mi, hangi uyarılar, hangi red."""

    gecti: bool
    ret_sebebi: str = ""
    uyarilar: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:  # pragma: no cover - kolaylık
        return self.gecti


def _kucuk(metin: str) -> str:
    """Karşılaştırma için normalleştirir.

    NEDEN: kesme işareti/tipografi farkı ("%10'unu" vs "%10unu") yüzünden
    çürütülmüş bilgi kalıpları kaçıyordu. `_kucuk` artık kesme işaretlerini
    atar ve fazla boşluğu tekleştirir.
    """
    t = str(metin or "").lower()
    t = t.replace("’", "").replace("'", "").replace("`", "")
    t = t.replace("\u00a0", " ")
    return re.sub(r"\s+", " ", t).strip()


def abarti_sayisi(metin: str) -> int:
    k = _kucuk(metin)
    return sum(1 for i in ABARTI_IFADELERI if i in k)


def curutulmus_bilgi_mi(metin: str) -> str | None:
    """Metin, çürütülmüş bir bilgiyi GERÇEK gibi sunuyor mu? Anahtar döner."""
    k = _kucuk(metin)
    for anahtar, kalıplar in CURUTULMUS_BILGILER.items():
        if any(kalıp in k for kalıp in kalıplar):
            return anahtar
    return None


def sayilar(metin: str) -> list[str]:
    return re.findall(r"\d+(?:[.,]\d+)?", str(metin or ""))


def kaynak_gecerli_mi(kaynak: str) -> tuple[bool, str]:
    """Kaynak alanı anlamlı mı? ('', 'bilinmiyor', 'internette okudum' → hayır)."""
    k = _kucuk(kaynak)
    if not k or k in ("-", "yok", "bilinmiyor", "kaynak", "n/a", "na"):
        return False, "kaynak boş"
    if any(z in k for z in _ZAYIF_KAYNAKLAR):
        return False, "kaynak belirsiz (kurum/kitap adı olmalı)"
    if len(k) < 3:
        return False, "kaynak çok kısa"
    return True, "uygun"


def dogrula(
    metin: str,
    kaynak: str = "",
    sayi_listesi: list[str] | None = None,
    *,
    curutme_icerigi: bool = False,
) -> DogrulamaSonucu:
    """Bir bilgi kartının sunumunu denetler.

    `curutme_icerigi=True` → metin çürütülmüş bir bilgiyi ÇÜRÜTÜYORSA
    (T1 taktiği), çürütülmüş-bilgi kontrolü atlanır (yasak sadece "gerçek
    gibi sunmak").
    """
    m = _kucuk(metin)
    uyarilar: list[str] = []

    if len(str(metin or "").strip()) < 40:
        return DogrulamaSonucu(False, "metin çok kısa (bilgi taşımıyor)")

    # 1) Tehlikeli iddia (tıbbi/finansal/güvenlik) — KESİN RED
    for iddia in TEHLIKELI_IDDIALAR:
        if iddia in m:
            return DogrulamaSonucu(
                False, f"tehlikeli iddia ('{iddia}') — sağlık/para/güvenlik reddedildi"
            )

    # 2) Çürütülmüş bilgiyi gerçek gibi sunma — KESİN RED (tehlikeli içerik,
    #    kaynaktan bağımsız: kaynak yazmak yanlış bilgiyi doğru yapmaz)
    if not curutme_icerigi:
        anahtar = curutulmus_bilgi_mi(m)
        if anahtar:
            return DogrulamaSonucu(
                False,
                f"çürütülmüş bilgi '{anahtar}' gerçek gibi sunulmuş "
                "(çürüten içerik yapılabilir: curutme_icerigi=True)",
            )

    # 3) Kaynak zorunlu (doğrulanabilirlik ön koşulu)
    kaynak_ok, kaynak_sebep = kaynak_gecerli_mi(kaynak)
    if not kaynak_ok:
        return DogrulamaSonucu(False, f"doğrulanabilirlik: {kaynak_sebep}")

    # 4) Sayı denetimi
    metin_sayilari = sayilar(metin)
    if metin_sayilari and sayi_listesi:
        bildirilen = {str(s).replace(",", ".") for s in sayi_listesi}
        eksik = [s for s in metin_sayilari if s.replace(",", ".") not in bildirilen]
        if eksik:
            uyarilar.append(f"sayılar bildirilen listede yok: {eksik[:3]}")

    # 5) Abartı sayısı
    ab = abarti_sayisi(metin)
    if ab > 1:
        return DogrulamaSonucu(False, f"abartılı kesinlik ifadesi fazla ({ab} tane, en fazla 1)")
    if ab == 1:
        uyarilar.append("1 abartı ifadesi var (sınıra takıldı)")

    return DogrulamaSonucu(True, "", uyarilar)


def arena_dogruluk_talimati() -> str:
    """Arena prompt'una eklenecek doğruluk kuralları (tek kaynak)."""
    return (
        "DOĞRULUK KURALLARI (ihlal = içerik çöp):\n"
        "1) Sadece İYİ BİLİNEN, kaynağı adlandırılabilir bilgi kullan. "
        "Kaynağı uydurma; gerçek kurum/kitap/dergi adı yaz (NASA, Nature, "
        "Britannica, Scientific American, WHO vb.).\n"
        "2) Emin olmadığın bir sayıyı YAZMA. Sayı vereceksen kesin ol.\n"
        "3) 'asla', 'her zaman', 'kanıtlanmıştır', '%100' gibi kesinlik "
        "ifadelerini en fazla BİR kez kullan.\n"
        "4) Sağlık, para ve güvenlik iddiası YOK ('tedavi eder', 'garanti "
        "kazanç' gibi ifadeler kesinlikle yasak).\n"
        "5) Yaygın ama YANLIŞ bilgileri gerçek gibi sunma. Onları "
        "çürütüyorsan bu çok iyidir — 'herkes böyle bilir, oysa...' diye yaz.\n"
        "6) Emin olmadığın yerde 'bilim insanları hâlâ tartışıyor' de; "
        "uydurma kesinlik verme."
    )
