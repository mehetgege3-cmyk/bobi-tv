"""
Kanca (Hook) Mühendisliği Modülü
- Otomatik varyant üretimi (soru, şok, sayı formları)
- Kelime bütünlüğünü koruyan üst bant kesme
- Yasaklı/clickbait kelime kontrolü
- İlk 1.5 saniye kuralı (max 12 kelime)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Senaryo

_LOG = logging.getLogger("bobi_tv.senaryo_v7.hook_engineer")


@dataclass
class HookVaryant:
    """Hook üst bant varyantı."""

    metin: str
    form: str  # "soru", "şok", "sayı"
    onaylandi: bool = False
    ab_test_grubu: str = "A"  # A/B test için


@dataclass
class HookMuhendislikSonuc:
    """Hook mühendislik sonucu."""

    hook_ust_bant: str
    varyantlar: list[HookVaryant] = field(default_factory=list)
    yasakli_kelime_var: bool = False
    yasakli_kelimeler: list[str] = field(default_factory=list)
    ilk_satir_uzun: bool = False
    ilk_satir_kelime_sayisi: int = 0
    oneriler: list[str] = field(default_factory=list)
    puan: int = 100  # 0-100
    gecerli: bool = True  # 70+ ise True
    onerilen_varyant: str | None = None


# Yasaklı/clickbait kelime listesi
YASAKLI_KELIMELER = {
    # Şok/şaşırtma
    "şok",
    "şaşırmayın",
    "inanamayacaksınız",
    "gözlerinize inanamayacaksınız",
    "bu gerçek",
    "gerçek mi",
    # Abartı
    "muhteşem",
    "inanılmaz",
    "harika",
    "mükemmel",
    "en iyi",
    "en kötü",
    "dünyanın en",
    # Clickbait
    "izlemelisiniz",
    "kaçırmayın",
    "hemen izleyin",
    "sonunda",
    "bomba",
    "sırrı",
    "gizli",
}

# Yumuşatma önerileri
YUMUSATMA_ONERILERI = {
    "şok": "ilginç",
    "şaşırmayın": "bakın",
    "inanamayacaksınız": "göreceksiniz",
    "muhteşem": "güzel",
    "inanılmaz": "şaşırtıcı",
    "harika": "iyi",
    "mükemmel": "başarılı",
    "en iyi": "başarılı",
    "en kötü": "başarısız",
    "bomba": "önemli",
    "sırrı": "detayı",
    "gizli": "bilinmeyen",
}


def hook_varyant_uret(sablon_metni: str) -> list[HookVaryant]:
    """
    Aynı şablondan 3 farklı üst bant varyantı üret.

    Args:
        sablon_metni: Şablon metin (örneğin: "Bu videoda X yapıyoruz")

    Returns:
        HookVaryant listesi (soru, şok, sayı formları)
    """
    varyantlar = []

    # 1. Soru formu
    soru_formu = _soru_formu_olustur(sablon_metni)
    if soru_formu:
        varyantlar.append(
            HookVaryant(
                metin=soru_formu,
                form="soru",
                onaylandi=True,
                ab_test_grubu="A",
            )
        )

    # 2. Şok formu
    sok_formu = _sok_formu_olustur(sablon_metni)
    if sok_formu:
        varyantlar.append(
            HookVaryant(
                metin=sok_formu,
                form="şok",
                onaylandi=True,
                ab_test_grubu="B",
            )
        )

    # 3. Sayı formu
    sayi_formu = _sayi_formu_olustur(sablon_metni)
    if sayi_formu:
        varyantlar.append(
            HookVaryant(
                metin=sayi_formu,
                form="sayı",
                onaylandi=True,
                ab_test_grubu="C",
            )
        )

    _LOG.info("%d hook varyantı üretildi", len(varyantlar))
    return varyantlar


def _soru_formu_olustur(metin: str) -> str | None:
    """Soru formu üst bant oluştur."""
    # Metinden ana fikir çıkar
    temiz = metin.strip().rstrip(".!?")

    # Zaten soru mu?
    if metin.strip().endswith("?"):
        return metin

    # Soru oluştur

    # İlk kelimeyi koruyarak soru oluştur
    ilk_kelime = temiz.split()[0] if temiz.split() else ""
    if ilk_kelime:
        return f"{temiz} mi?"

    return None


def _sok_formu_olustur(metin: str) -> str | None:
    """Şok formu üst bant oluştur."""
    temiz = metin.strip().rstrip(".!?")

    # Yasaklı kelime kontrolü
    if any(yasakli in temiz.lower() for yasakli in ["şok", "şaşırmayın"]):
        # Yumuşatma uygula
        for yasakli, yumusak in YUMUSATMA_ONERILERI.items():
            if yasakli in temiz.lower():
                temiz = temiz.replace(yasakli, yumusak)
                break

    # Şok formu oluştur
    sok_kalari = [
        f"Bakın: {temiz}",
        f"İşte {temiz.lower()}",
        f"Gerçek: {temiz}",
    ]

    return sok_kalari[0] if temiz else None


def _sayi_formu_olustur(metin: str) -> str | None:
    """Sayı formu üst bant oluştur."""
    temiz = metin.strip().rstrip(".!?")

    # Metinde sayı var mı?
    sayi_match = re.search(r"\d+", temiz)
    if sayi_match:
        return temiz  # Zaten sayı var

    # Rastgele sayı ekle
    import random

    sayilar = [3, 5, 7, 10]
    sayi = random.choice(sayilar)

    sayi_kalari = [
        f"{sayi} şey: {temiz.lower()}",
        f"{sayi} nedir? {temiz}",
        f"Top {sayi}: {temiz.lower()}",
    ]

    return sayi_kalari[0] if temiz else None


def ust_bant_kes(metin: str, max_uzunluk: int = 35) -> str:
    """
    Üst bant uzunluk kesme - kelime bütünlüğünü koru.

    Args:
        metin: Kesilecek metin
        max_uzunluk: Maksimum karakter sayısı (default: 35)

    Returns:
        Kesilmiş metin (sonu ... ile bitiyor)
    """
    if len(metin) <= max_uzunluk:
        return metin

    # Kelime bütünlüğünü koruyarak kes
    kelimeler = metin.split()

    # Tek tek kelime ekle, sınırı geçme
    kesilmis = ""
    for kelime in kelimeler:
        test = f"{kesilmis} {kelime}".strip()
        if len(test) + 3 <= max_uzunluk:  # +3 for "..."
            kesilmis = test
        else:
            break

    # Sonuç boşsa ilk kelimeyi kes
    if not kesilmis and kelimeler:
        kesilmis = kelimeler[0][: max_uzunluk - 3]

    return f"{kesilmis}..."


def yasakli_kelime_kontrol(metin: str) -> tuple[bool, list[str]]:
    """
    Yasaklı/clickbait kelime kontrolü.

    Args:
        metin: Kontrol edilecek metin

    Returns:
        (yasakli_var, yasakli_kelimeler_listesi)
    """
    metin_lower = metin.lower()
    bulunanlar = []

    for yasakli in YASAKLI_KELIMELER:
        if yasakli in metin_lower:
            bulunanlar.append(yasakli)

    return len(bulunanlar) > 0, bulunanlar


def yumusama_onerisi(yasakli_kelime: str) -> str:
    """
    Yasaklı kelime için yumuşatma önerisi.

    Args:
        yasakli_kelime: Yasaklı kelime

    Returns:
        Yumuşatılmış alternatif
    """
    return YUMUSATMA_ONERILERI.get(yasakli_kelime.lower(), yasakli_kelime)


def ilk_satir_kontrol(ilk_satir: str, max_kelime: int = 12) -> tuple[bool, int, str | None]:
    """
    İlk 1.5 saniye kuralı kontrolü.

    Args:
        ilk_satir: İlk diyalog satırı
        max_kelime: Maksimum kelime sayısı (default: 12)

    Returns:
        (uzun_mu, kelime_sayisi, kısaltma_onerisi)
    """
    kelimeler = ilk_satir.split()
    kelime_sayisi = len(kelimeler)

    if kelime_sayisi <= max_kelime:
        return False, kelime_sayisi, None

    # Kısaltma önerisi: İlk 10 kelime + "..."
    kisa_oneri = " ".join(kelimeler[:10]) + "..."
    oneri = f"İlk satır çok uzun ({kelime_sayisi} kelime). Öneri: {kisa_oneri}"

    return True, kelime_sayisi, oneri


def hook_muhendislik_yap(senaryo: Senaryo) -> HookMuhendislikSonuc:
    """
    Senaryonun hook'unu mühendislik yap.

    Args:
        senaryo: Senaryo objesi

    Returns:
        HookMuhendislikSonuc
    """
    # 1. Üst bant al
    hook_ust_bant = getattr(senaryo, "hook_ust_bant", "") or ""

    # 2. Varyant üret
    varyantlar = hook_varyant_uret(hook_ust_bant) if hook_ust_bant else []

    # 3. Yasaklı kelime kontrol
    yasakli_var, yasakli_kelimeler = yasakli_kelime_kontrol(hook_ust_bant)

    # 4. İlk satır kontrol
    ilk_satir_uzun = False
    ilk_satir_kelime_sayisi = 0

    if hasattr(senaryo, "tts_metinleri") and senaryo.tts_metinleri:
        ilk_satir = senaryo.tts_metinleri[0]
        ilk_satir_uzun, ilk_satir_kelime_sayisi, oneri = ilk_satir_kontrol(ilk_satir)

    # 5. Öneriler
    oneriler = []

    if yasakli_var:
        for yasakli in yasakli_kelimeler:
            yumusak = yumusama_onerisi(yasakli)
            oneriler.append(f"⚠️  '{yasakli}' → '{yumusak}' olarak değiştirin")

    if ilk_satir_uzun:
        oneriler.append(f"⚠️  İlk satır {ilk_satir_kelime_sayisi} kelime (max 12 olmalı)")

    if len(hook_ust_bant) > 35:
        oneriler.append(f"⚠️  Üst bant {len(hook_ust_bant)} karakter (max 35 olmalı)")

    # 6. Puan hesapla
    puan = 100

    if yasakli_var:
        puan -= len(yasakli_kelimeler) * 15

    if ilk_satir_uzun:
        puan -= 20

    if len(hook_ust_bant) > 35:
        puan -= 10

    if not hook_ust_bant:
        puan -= 30

    puan = max(0, min(100, puan))

    # 7. Önerilen varyant
    onerilen_varyant = None
    if varyantlar:
        # İlk onaylanmış varyantı seç, yoksa ilkini seç
        onayli = [v for v in varyantlar if v.onaylandi]
        onerilen_varyant = onayli[0].metin if onayli else varyantlar[0].metin

    return HookMuhendislikSonuc(
        hook_ust_bant=hook_ust_bant,
        varyantlar=varyantlar,
        yasakli_kelime_var=yasakli_var,
        yasakli_kelimeler=yasakli_kelimeler,
        ilk_satir_uzun=ilk_satir_uzun,
        ilk_satir_kelime_sayisi=ilk_satir_kelime_sayisi,
        oneriler=oneriler,
        puan=puan,
        gecerli=puan >= 70,
        onerilen_varyant=onerilen_varyant,
    )
