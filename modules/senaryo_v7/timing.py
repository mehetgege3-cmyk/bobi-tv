"""
Zamanlama ve Tempo Modülü
- Türkçe hece bazlı süre tahmini (5.5-6.5 hece/sn)
- Duygu bazlı tempo çarpanları
- 15-22 sn tatlı nokta kontrolü
- Satır bazlı zaman çizelgesi
- Twist anı hesaplama
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Senaryo

_LOG = logging.getLogger("bobi_tv.senaryo_v7.timing")


@dataclass
class SatirZamanlama:
    """Tek bir satırın zamanlama bilgileri."""

    metin: str
    baslangic_sn: float
    bitis_sn: float
    hece_sayisi: int
    duygu: str
    hiz_carpani: float = 1.0


@dataclass
class ZamanlamaSonuc:
    """Zamanlama sonucu."""

    toplam_sure_sn: float
    satirlar: list[SatirZamanlama] = field(default_factory=list)
    tatli_noktada_mi: bool = False  # 15-22 sn arası
    kesme_noktalari: list[float] = field(default_factory=list)  # Her 2 sn'de
    twist_ani_sn: float | None = None
    duzeltme_gerekli: bool = False
    duzeltme_onerileri: list[str] = field(default_factory=list)
    puan: int = 100  # 0-100
    gecerli: bool = True  # 70+ ise True
    onerilen_hiz: float | None = None
    aciklama: str = ""


# Duygu bazlı hız çarpanları
DUYGU_HIZ_CARPANLARI = {
    "normal": 1.0,
    "enerjik": 1.15,  # %15 hızlı
    "sinirli": 1.1,
    "panik": 1.25,  # %25 hızlı
    "sasirmis": 0.95,
    "kesin": 0.9,
    "ciddi": 0.85,
    "soguk": 0.9,
    "bikkin": 0.75,  # %25 yavaş
    "bikkin_dramatik": 0.7,
    "yavas_dramatik": 0.8,
    "uykulu": 0.65,  # %35 yavaş
    "dusunceli": 0.85,
    "gururlu": 0.9,
    "endiseli": 1.05,
    "umutlu": 1.0,
    "robotik": 1.1,
    "robotik_koro": 1.0,
    "derin": 0.8,
    "derin_dramatik": 0.75,
    "alarm": 1.2,
    "twist": 1.0,
}

# Hedef süre aralığı
MIN_SURE_SN = 15.0
MAX_SURE_SN = 22.0
HEDEF_SATIR_SAYISI = (6, 7)

# Hız aralığı (hece/sn)
MIN_HIZ = 5.5
MAKS_HIZ = 6.5
ORTALAMA_HIZ = 6.0


def hece_sayisi_turkce(metin: str) -> int:
    """
    Türkçe metin için hece sayısı hesapla.

    Türkçe heceler:
    - Her sesli harf bir hece oluşturur
    - Bazı kombinasyonlar tek hece sayılır

    Args:
        metin: Metin

    Returns:
        Hece sayısı
    """
    # Türkçe sesli harfler
    sesliler = "aeıioöuüAEIİOÖUÜ"

    # Temel hesaplama: her sesli bir hece
    hece = sum(1 for char in metin if char in sesliler)

    # Özel durumlar:
    # - Tek başına sesliler ayrı hece
    # - "au", "eu" gibi diftonglar tek hece (nadir)

    return max(1, hece)  # En az 1 hece


def sure_tahmin_hece(metin: str, duygu: str = "normal") -> float:
    """
    Hece bazlı süre tahmini.

    Args:
        metin: Metin
        duygu: Duygu etiketi

    Returns:
        Tahmini süre (saniye)
    """
    hece = hece_sayisi_turkce(metin)

    # Temel hız (hece/sn)
    hiz = ORTALAMA_HIZ

    # Duygu çarpanı uygula
    carpan = DUYGU_HIZ_CARPANLARI.get(duygu.lower(), 1.0)
    hiz *= carpan

    # Süre hesapla
    sure = hece / hiz

    # Alt limit (en az 0.5 sn)
    return max(0.5, sure)


def satir_zamanlama_hesapla(
    satirlar: list[str],
    duygular: list[str] | None = None,
    gercek_sureler: list[float] | None = None,
) -> ZamanlamaSonuc:
    """
    Tüm satırlar için zamanlama hesapla.

    Args:
        satirlar: Satır metinleri
        duygular: Her satırın duygu etiketi (opsiyonel)
        gercek_sureler: Gerçek TTS süreleri (opsiyonel)

    Returns:
        ZamanlamaSonuc
    """
    if not satirlar:
        return ZamanlamaSonuc(
            toplam_sure_sn=0.0,
            tatli_noktada_mi=False,
        )

    # Varsayılan duygular
    if not duygular:
        duygular = ["normal"] * len(satirlar)

    # Zamanlama hesapla
    zamanlama_listesi = []
    toplam_sure = 0.0

    for i, (satir, duygu) in enumerate(zip(satirlar, duygular)):
        # Gerçek süre varsa kullan, yoksa tahmin et
        if gercek_sureler and i < len(gercek_sureler):
            sure = gercek_sureler[i]
        else:
            sure = sure_tahmin_hece(satir, duygu)

        hece = hece_sayisi_turkce(satir)
        carpan = DUYGU_HIZ_CARPANLARI.get(duygu.lower(), 1.0)

        zamanlama = SatirZamanlama(
            metin=satir,
            baslangic_sn=toplam_sure,
            bitis_sn=toplam_sure + sure,
            hece_sayisi=hece,
            duygu=duygu,
            hiz_carpani=carpan,
        )

        zamanlama_listesi.append(zamanlama)
        toplam_sure += sure

    # Kesme noktaları (her 2 saniyede)
    kesme_noktalari = []
    for t in range(2, int(toplam_sure) + 1, 2):
        kesme_noktalari.append(float(t))

    # Twist anı (son satırdan 1-2 sn önce)
    twist_ani = None
    if zamanlama_listesi:
        son_satir = zamanlama_listesi[-1]
        twist_ani = son_satir.bitis_sn - 1.5

    # Tatlı nokta kontrolü
    tatli_noktada = MIN_SURE_SN <= toplam_sure <= MAX_SURE_SN

    # Düzeltme gerekli mi?
    duzeltme_gerekli = not tatli_noktada
    duzeltme_onerileri = []

    if toplam_sure < MIN_SURE_SN:
        duzeltme_onerileri.append(
            f"⚠️  Video çok kısa ({toplam_sure:.1f} sn). Min {MIN_SURE_SN} sn olmalı."
        )
        duzeltme_onerileri.append(
            "💡 Öneri: Satır sayısını artır veya satırları uzat."
        )

    elif toplam_sure > MAX_SURE_SN:
        duzeltme_onerileri.append(
            f"⚠️  Video çok uzun ({toplam_sure:.1f} sn). Max {MAX_SURE_SN} sn olmalı."
        )
        duzeltme_onerileri.append(
            "💡 Öneri: Satır sayısını azalt veya satırları kısalt."
        )

    # Satır sayısı kontrolü
    satir_sayisi = len(satirlar)
    if satir_sayisi < HEDEF_SATIR_SAYISI[0]:
        duzeltme_onerileri.append(
            f"⚠️  Satır sayısı az ({satir_sayisi}). Hedef: {HEDEF_SATIR_SAYISI[0]}-{HEDEF_SATIR_SAYISI[1]}"
        )
    elif satir_sayisi > HEDEF_SATIR_SAYISI[1]:
        duzeltme_onerileri.append(
            f"⚠️  Satır sayısı fazla ({satir_sayisi}). Hedef: {HEDEF_SATIR_SAYISI[0]}-{HEDEF_SATIR_SAYISI[1]}"
        )

    # Puan hesapla
    puan = 100
    onerilen_hiz = None
    aciklama = ""

    if not tatli_noktada:
        if toplam_sure < MIN_SURE_SN:
            # Çok kısa - ciddi ceza
            fark = MIN_SURE_SN - toplam_sure
            puan -= min(50, fark * 10)
            aciklama = f"Video çok kısa: {toplam_sure:.1f} sn (min {MIN_SURE_SN} sn)"
        elif toplam_sure > MAX_SURE_SN:
            # Çok uzun - orta ceza
            fark = toplam_sure - MAX_SURE_SN
            puan -= min(30, fark * 5)
            aciklama = f"Video çok uzun: {toplam_sure:.1f} sn (max {MAX_SURE_SN} sn)"
            # Hız önerisi
            onerilen_hiz = round(toplam_sure / MAX_SURE_SN, 2)
    else:
        aciklama = f"Süre tatlı noktada: {toplam_sure:.1f} sn"

    # Satır sayısı cezası
    if satir_sayisi < HEDEF_SATIR_SAYISI[0]:
        puan -= 10
    elif satir_sayisi > HEDEF_SATIR_SAYISI[1]:
        puan -= 5

    puan = max(0, min(100, puan))

    return ZamanlamaSonuc(
        toplam_sure_sn=toplam_sure,
        satirlar=zamanlama_listesi,
        tatli_noktada_mi=tatli_noktada,
        kesme_noktalari=kesme_noktalari,
        twist_ani_sn=twist_ani,
        duzeltme_gerekli=duzeltme_gerekli,
        duzeltme_onerileri=duzeltme_onerileri,
        puan=puan,
        gecerli=puan >= 70,
        onerilen_hiz=onerilen_hiz,
        aciklama=aciklama,
    )


def satir_duzelt(satirlar: list[str], hedef_sure: float = 18.5) -> tuple[list[str], list[str]]:
    """
    Süre hedefine göre satırları düzelt.

    Args:
        satirlar: Mevcut satırlar
        hedef_sure: Hedef süre (default: 18.5 sn)

    Returns:
        (düzeltilmiş_satırlar, değişiklik_listesi)
    """
    duzeltilmis = satirlar.copy()
    degisiklikler = []

    # Mevcut süreyi hesapla
    sonuc = satir_zamanlama_hesapla(satirlar)
    mevcut_sure = sonuc.toplam_sure_sn

    # Kısa ise: satır ekle veya uzat
    if mevcut_sure < MIN_SURE_SN:
        # Eksik süre

        # Her satırı ortalama %20 uzat
        for i, satir in enumerate(duzeltilmis):
            if len(satir.split()) < 10:  # Kısa satırları uzat
                # Basit uzatma: tekrar ekle
                duzeltilmis[i] = f"{satir}... {satir}"
                degisiklikler.append(f"Satır {i+1} uzatıldı")

    # Uzun ise: satır kısalt veya birleştir
    elif mevcut_sure > MAX_SURE_SN:
        # Fazla süre

        # En uzun satırı bul
        uzunluklar = [len(s.split()) for s in duzeltilmis]
        en_uzun_idx = uzunluklar.index(max(uzunluklar))

        # İkiye böl
        satir = duzeltilmis[en_uzun_idx]
        kelimeler = satir.split()

        if len(kelimeler) > 8:
            orta = len(kelimeler) // 2
            ilk_yari = " ".join(kelimeler[:orta])
            ikinci_yari = " ".join(kelimeler[orta:])

            duzeltilmis.insert(en_uzun_idx + 1, ikinci_yari)
            duzeltilmis[en_uzun_idx] = ilk_yari

            degisiklikler.append(f"Satır {en_uzun_idx+1} ikiye bölündü")

    return duzeltilmis, degisiklikler


def zamanlama_olustur(senaryo: Senaryo) -> ZamanlamaSonuc:
    """
    Senaryo için tam zamanlama oluştur.

    Args:
        senaryo: Senaryo objesi

    Returns:
        ZamanlamaSonuc
    """
    # TTS metinlerini al
    tts_metinleri = getattr(senaryo, "tts_metinleri", []) or []

    if not tts_metinleri:
        return ZamanlamaSonuc(
            toplam_sure_sn=0.0,
            tatli_noktada_mi=False,
        )

    # Duyguları al
    duygular = []
    if hasattr(senaryo, "diyaloglar"):
        for diyalog in senaryo.diyaloglar:
            duygu = getattr(diyalog, "duygu", "normal")
            duygular.append(str(duygu))

    # Eğer duygu sayısı yetersizse, varsayılan kullan
    if len(duygular) < len(tts_metinleri):
        duygular.extend(["normal"] * (len(tts_metinleri) - len(duygular)))

    return satir_zamanlama_hesapla(tts_metinleri, duygular)
