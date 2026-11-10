"""
Karakter Zıtlığı ve Diyalog Kalitesi Modülü
- Ping-pong doğrulaması (ardışık satırlar farklı karakter)
- Zıtlık matrisi (aynı duygu çifti kontrolü)
- Tek fikir kuralı (virgülle bağlanmış espri kontrolü)
- Türkçe doğallık kontrolü
- Karakter adı tutarlılığı
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Senaryo

_LOG = logging.getLogger("bobi_tv.senaryo_v7.dialogue_quality")


@dataclass
class DiyaloKKaliteSonuc:
    """Diyalog kalitesi sonucu."""

    ping_pong_gecerli: bool = True
    zıtlık_sorunları: list[str] = field(default_factory=list)
    cok_fikirli_satırlar: list[int] = field(default_factory=list)  # Satır numaraları
    dogallık_sorunları: list[str] = field(default_factory=list)
    karakter_tutarsızlıkları: list[str] = field(default_factory=list)
    puan: int = 100  # 0-100


# Zıtlık matrisi: hangi duygu çiftleri zıt değil (kaçınılmalı) - aynı duygu ardışık gelmemeli
ZITLIK_YASAKLI_CIFTLER = {
    ("sinirli", "sinirli"),
    ("sinirli", "soguk"),
    ("soguk", "soguk"),
    ("panik", "panik"),
    ("enerjik", "enerjik"),
    ("bikkin", "bikkin"),
    ("ciddi", "ciddi"),
    ("alarm", "alarm"),
    ("normal", "normal"),
    ("sasirmis", "sasirmis"),
    ("dusunceli", "dusunceli"),
}

# İyi zıtlık örnekleri
IYI_ZITLIK_ORNEKLERI = {
    ("sinirli", "normal"),
    ("sinirli", "sasirmis"),
    ("panik", "dusunceli"),
    ("enerjik", "bikkin"),
    ("ciddi", "sasirmis"),
}

# Türkçe doğallık kuralları
DOGALLIK_KURALLARI = {
    "unvan_buyuk_harf": {
        "pattern": r"\b(bey|hanım|efendi)\b",
        "uyarı": "Unvanlar küçük harfle yazılmalı: 'Müdür bey' → 'Müdür Bey'",
        "duzeltme": lambda m: m.group(0).title(),
    },
    "ya_kullanimi": {
        "pattern": r"\bya\b",
        "uyarı": "'ya' kelimesi doğal ama fazla kullanım kaçınılmalı",
        "limit": 3,
    },
    "yani_kullanimi": {
        "pattern": r"\byani\b",
        "uyarı": "'yani' kelimesi doğal ama fazla kullanım kaçınılmalı",
        "limit": 2,
    },
    "hatali_kelime": {
        "pattern": r"\b(herşey|hiçbirşey|birşey)\b",
        "uyarı": "Kelime ayrı yazılmalı: 'her şey', 'hiçbir şey', 'bir şey'",
        "duzeltme": {
            "herşey": "her şey",
            "hiçbirşey": "hiçbir şey",
            "birşey": "bir şey",
        },
    },
}

# Karakter adı tutarlılığı için örnek mapping
KARAKTER_ALIASES = {
    "ik": ["İK", "İnsan Kaynakları", "Ayşe"],
    "mudur": ["Müdür", "Müdür Bey", "Ahmet Bey"],
    "isci": ["İşçi", "Çalışan", "Mehmet"],
}


def ping_pong_dogrula(diyaloglar: list) -> tuple[bool, list[str]]:
    """
    Ping-pong doğrulaması: ardışık satırlar farklı karakterde olmalı.

    Args:
        diyaloglar: Diyalog listesi (her biri 'karakter' ve 'metin' içerir)

    Returns:
        (gecerli_mi, hatalar_listesi)
    """
    hatalar = []

    for i in range(len(diyaloglar) - 1):
        mevcut_karakter = getattr(diyaloglar[i], "karakter", None) or diyaloglar[i].get("karakter", "")
        sonraki_karakter = getattr(diyaloglar[i + 1], "karakter", None) or diyaloglar[i + 1].get("karakter", "")

        if mevcut_karakter == sonraki_karakter:
            hata = f"Satır {i+1}-{i+2}: Ardışık satırlar aynı karakterde ('{mevcut_karakter}')"
            hatalar.append(hata)

    return len(hatalar) == 0, hatalar


def zıtlık_kontrol(diyaloglar: list) -> list[str]:
    """
    Zıtlık matrisi kontrolü: ardışık diyaloglar aynı duyguda olmamalı.

    Args:
        diyaloglar: Diyalog listesi

    Returns:
        Sorun listesi
    """
    sorunlar = []

    for i in range(len(diyaloglar) - 1):
        # Diyalog objesi 'ses' attribute'ı kullanıyor (Duygu enum)
        mevcut_duygu_raw = getattr(diyaloglar[i], "ses", None) or diyaloglar[i].get("ses", None) or diyaloglar[i].get("duygu", "normal")
        sonraki_duygu_raw = getattr(diyaloglar[i + 1], "ses", None) or diyaloglar[i + 1].get("ses", None) or diyaloglar[i + 1].get("duygu", "normal")
        
        # Enum ise value'sunu al
        mevcut_duygu = str(mevcut_duygu_raw.value if hasattr(mevcut_duygu_raw, 'value') else mevcut_duygu_raw).lower()
        sonraki_duygu = str(sonraki_duygu_raw.value if hasattr(sonraki_duygu_raw, 'value') else sonraki_duygu_raw).lower()

        # Aynı duygu çifti kontrolü
        cift = (mevcut_duygu, sonraki_duygu)
        ters_cift = (sonraki_duygu, mevcut_duygu)

        if cift in ZITLIK_YASAKLI_CIFTLER or ters_cift in ZITLIK_YASAKLI_CIFTLER:
            sorun = f"Satır {i+1}-{i+2}: Zıtlık yok - '{mevcut_duygu}' → '{sonraki_duygu}'"
            öneri = f"💡 Öneri: '{mevcut_duygu}' → '{sonraki_duygu}' yerine zıt duygu kullan"
            sorunlar.append(f"{sorun}\n{öneri}")

    return sorunlar


def tek_fikir_kontrol(satirlar: list[str]) -> list[int]:
    """
    Tek fikir kuralı: bir satırda virgülle bağlanmış iki espri var mı?

    Args:
        satirlar: Satır metinleri

    Returns:
        Sorunlu satır numaraları (1-indexed)
    """
    sorunlu_satırlar = []

    # Espri kalıpları
    espri_kalari = [
        r"\.\.\..*\.\.\.",  # Birden fazla üç nokta
        r",\s*ya\s+da\s+",  # "ya da" bağlacı
        r",\s*hem\s+de\s+",  # "hem de" bağlacı
        r",\s*üstelik\s+",  # "üstelik" bağlacı
    ]

    for i, satir in enumerate(satirlar, 1):
        # Virgül sayısı > 2 ve uzun satır
        if satir.count(",") >= 3 and len(satir.split()) > 15:
            # Espri kalıbı var mı?
            for kalar in espri_kalari:
                if re.search(kalar, satir, re.IGNORECASE):
                    sorunlu_satırlar.append(i)
                    break

    return sorunlu_satırlar


def dogallik_kontrol(metin: str) -> list[str]:
    """
    Türkçe doğallık kontrolü.

    Args:
        metin: Kontrol edilecek metin

    Returns:
        Uyarı listesi
    """
    uyarılar = []

    for kural_adi, kural in DOGALLIK_KURALLARI.items():
        pattern = kural["pattern"]
        matches = re.findall(pattern, metin, re.IGNORECASE)

        if matches:
            # Limit kontrolü
            if "limit" in kural and len(matches) > kural["limit"]:
                uyarı = f"⚠️  '{kural_adi}': {len(matches)} kez kullanılmış (max {kural['limit']})"
                uyarılar.append(uyarı)
            elif "uyarı" in kural:
                uyarı = f"⚠️  {kural['uyarı']}"
                uyarılar.append(uyarı)

    return uyarılar


def karakter_tutarlılık_kontrol(
    diyaloglar: list, karakter_mapping: dict | None = None
) -> list[str]:
    """
    Karakter adı tutarlılığı kontrolü.

    Args:
        diyaloglar: Diyalog listesi
        karakter_mapping: Karakter alias mapping (opsiyonel)

    Returns:
        Tutarsızlık listesi
    """
    if not karakter_mapping:
        karakter_mapping = KARAKTER_ALIASES

    tutarsızlıklar = []

    # Karakter referanslarını topla
    karakter_referansları = {}
    for i, diyalog in enumerate(diyaloglar):
        metin = getattr(diyalog, "metin", "") or diyalog.get("metin", "")

        # Karakter adı geçiyor mu?
        for karakter, aliases in karakter_mapping.items():
            for alias in aliases:
                if alias.lower() in metin.lower():
                    if karakter not in karakter_referansları:
                        karakter_referansları[karakter] = []
                    karakter_referansları[karakter].append((i + 1, alias))

    # Tutarsızlık kontrolü
    for karakter, referanslar in karakter_referansları.items():
        kullanilan_aliaslar = set([alias for _, alias in referanslar])

        if len(kullanilan_aliaslar) > 1:
            satırlar = [str(satır) for satır, _ in referanslar]
            tutarsızlık = (
                f"Karakter '{karakter}' farklı isimlerle anılmış: {', '.join(kullanilan_aliaslar)} "
                f"(satırlar: {', '.join(satırlar)})"
            )
            tutarsızlıklar.append(tutarsızlık)

    return tutarsızlıklar


def diyalog_kalitesi_analiz(senaryo: Senaryo) -> DiyaloKKaliteSonuc:
    """
    Senaryonun diyalog kalitesini analiz et.

    Args:
        senaryo: Senaryo objesi

    Returns:
        DiyaloKKaliteSonuc
    """
    # Diyalogları al
    diyaloglar = getattr(senaryo, "diyaloglar", []) or []

    if not diyaloglar:
        return DiyaloKKaliteSonuc(puan=0)

    # 1. Ping-pong kontrolü
    ping_pong_gecerli, ping_pong_hatalar = ping_pong_dogrula(diyaloglar)

    # 2. Zıtlık kontrolü
    zıtlık_sorunları = zıtlık_kontrol(diyaloglar)

    # 3. Tek fikir kontrolü
    satirlar = [
        getattr(d, "metin", "") or d.get("metin", "") for d in diyaloglar
    ]
    cok_fikirli_satırlar = tek_fikir_kontrol(satirlar)

    # 4. Doğallık kontrolü
    dogallık_sorunları = []
    for satir in satirlar:
        uyarılar = dogallik_kontrol(satir)
        dogallık_sorunları.extend(uyarılar)

    # 5. Karakter tutarlılık
    karakter_tutarsızlıkları = karakter_tutarlılık_kontrol(diyaloglar)

    # Puan hesapla
    puan = 100

    if not ping_pong_gecerli:
        puan -= 20

    if zıtlık_sorunları:
        puan -= len(zıtlık_sorunları) * 5

    if cok_fikirli_satırlar:
        puan -= len(cok_fikirli_satırlar) * 3

    if dogallık_sorunları:
        puan -= min(len(dogallık_sorunları) * 2, 10)  # Max 10 puan düş

    if karakter_tutarsızlıkları:
        puan -= len(karakter_tutarsızlıkları) * 5

    puan = max(0, min(100, puan))

    return DiyaloKKaliteSonuc(
        ping_pong_gecerli=ping_pong_gecerli,
        zıtlık_sorunları=ping_pong_hatalar + zıtlık_sorunları,
        cok_fikirli_satırlar=cok_fikirli_satırlar,
        dogallık_sorunları=dogallık_sorunları,
        karakter_tutarsızlıkları=karakter_tutarsızlıkları,
        puan=puan,
    )
