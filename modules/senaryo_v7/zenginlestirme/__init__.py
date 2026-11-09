"""Hook, başlık, CTA ve minimum süre tahminini oluşturan saf zenginleştirme."""

from __future__ import annotations

import logging
from collections.abc import Sequence

from ..ayarlar import Ayarlar
from ..models import Diyalog, DiyalogRolu, Duygu, Sablon, Senaryo

_LOG = logging.getLogger("bobi_tv.senaryo_v7.zenginlestirme")
_EK_REPLIK_CIFTLERI: tuple[tuple[str, str], ...] = (
    (
        "Bir dakika, bu hikâyenin en tuhaf kısmı daha başlamadı!",
        "Daha da mı var, şimdi bütün merakım arttı gerçekten!",
    ),
    ("Peki bu işin sonunda kim haklı çıkacak sence?", "Bekle, finalde bütün hesaplar bir anda değişecek!"),
)


def zenginlestir(senaryo: Senaryo, ayarlar: Ayarlar, sablonlar: Sequence[Sablon] = ()) -> Senaryo:
    """Senaryo alanlarını doldurur ve kısa metni ters köşeyi koruyarak genişletir."""
    if not senaryo.diyaloglar and sablonlar:
        fallback = sablonlar[0]
        senaryo.diyaloglar = [Diyalog.from_dict(item.to_dict()) for item in fallback.diyaloglar]
        senaryo.karakterler = list(fallback.karakterler)
        senaryo.kategori = fallback.kategori
        senaryo.etiketler = list(fallback.etiketler)
        senaryo.hedefkitle = fallback.hedefkitle
        senaryo.mevsimsellik = list(fallback.mevsimsellik)
        senaryo.tekrarkullanimgunsayisi = fallback.tekrarkullanimgunsayisi
        senaryo.performanspuani = fallback.performanspuani
        senaryo.yasakkelimekontrolugecti = fallback.yasakkelimekontrolugecti
    if not senaryo.diyaloglar:
        return senaryo

    twist_positions = [
        index for index, line in enumerate(senaryo.diyaloglar) if line.twist or line.rol is DiyalogRolu.TWIST
    ]
    twist_index = twist_positions[0] if twist_positions else max(0, len(senaryo.diyaloglar) - 2)
    added_pairs = 0
    while (
        _tahmini_sure(senaryo.diyaloglar, ayarlar) < ayarlar.hedef_tahmini_sure
        and added_pairs < len(_EK_REPLIK_CIFTLERI)
        and len(senaryo.diyaloglar) + 2 <= ayarlar.genisletme_diyalog_azami
    ):
        first, second = _EK_REPLIK_CIFTLERI[added_pairs]
        first_role = senaryo.diyaloglar[0]
        second_role = next(
            (line for line in senaryo.diyaloglar if line.karakter != first_role.karakter), first_role
        )
        added = [
            Diyalog(
                karakter=second_role.karakter,
                metin=first,
                cinsiyet=second_role.cinsiyet,
                ses=Duygu.SASIRMIS,
                sfx="pop",
                karakter_ref=second_role.karakter_ref,
                sesid=second_role.sesid,
            ),
            Diyalog(
                karakter=first_role.karakter,
                metin=second,
                cinsiyet=first_role.cinsiyet,
                ses=Duygu.ENERJIK,
                sfx="pop",
                karakter_ref=first_role.karakter_ref,
                sesid=first_role.sesid,
            ),
        ]
        senaryo.diyaloglar[twist_index:twist_index] = added
        twist_index += len(added)
        added_pairs += 1

    lines = senaryo.diyaloglar
    for index, line in enumerate(lines):
        if index == 0:
            line.rol = DiyalogRolu.HOOK
        elif line.twist or line.rol is DiyalogRolu.TWIST:
            line.rol = DiyalogRolu.TWIST
            line.twist = True
        elif index == len(lines) - 1:
            line.rol = DiyalogRolu.LOOPKAPANIS
        elif index == 1:
            line.rol = DiyalogRolu.SETUP
        else:
            line.rol = DiyalogRolu.ESCALATION
        if not line.vurgukelimeler:
            line.vurgukelimeler = _keywords(line.metin)
        line.vurgu_kelimeler = list(line.vurgukelimeler)
        line.tahminisuresn = round(_line_duration(line.metin, line.hiz, ayarlar), 2)
    first_text = _temizle_emoji(lines[0].metin)
    hook = _tr_upper(
        _temizle_emoji(
            senaryo.hook_ust_bant or senaryo.hook_metni or first_text[: ayarlar.hook_kesim_uzunlugu]
        )
    )
    if len(hook) > ayarlar.hook_bant_azami:
        hook = hook[: ayarlar.hook_kesim_uzunlugu].rsplit(" ", 1)[0] + "!"
    title = senaryo.baslik.strip() or f"{first_text[:48]} 😱"
    if "#shorts" not in title.lower():
        title = f"{title[: ayarlar.baslik_kesim_uzunlugu]} #shorts"
    senaryo.baslik = title[: ayarlar.baslik_azami]
    senaryo.hook_metni = hook
    senaryo.hook_ust_bant = hook
    senaryo.hook_suresi = 0.0
    senaryo.tts_metinleri = [line.metin for line in lines]
    senaryo.toplam_sure = round(_tahmini_sure(lines, ayarlar), 1)
    senaryo.acilis = " ".join(senaryo.tts_metinleri[:2])[:200]
    senaryo.semaversiyonu = "7.0"
    if added_pairs:
        _LOG.info("Kısa senaryo uzatıldı: çift=%d, tahmini=%.1fs", added_pairs, senaryo.toplam_sure)
    return senaryo


def _tahmini_sure(diyaloglar: Sequence[Diyalog], ayarlar: Ayarlar) -> float:
    """Hız çarpanını ve satır sonu duraklamalarını içeren yaklaşık toplam süreyi hesaplar."""
    return sum(
        max(ayarlar.minimum_replik_saniyesi, len(item.metin.split()) * ayarlar.tahmini_saniye_kelime)
        / item.hiz
        + item.duraklamams / 1000
        for item in diyaloglar
    )


def _line_duration(text: str, speed: float, ayarlar: Ayarlar) -> float:
    """Merkezi ayarlardaki saniye/kelime tabanını hız çarpanıyla uygular."""
    duration = max(ayarlar.minimum_replik_saniyesi, len(text.split()) * ayarlar.tahmini_saniye_kelime)
    return duration / max(0.85, min(1.25, speed))


def _keywords(text: str) -> list[str]:
    """Boş vurguları önlemek için satırdan en fazla üç anlamlı kelime çıkarır."""
    import re

    tokens = re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü0-9'-]+", text)
    stop = {
        "bunun",
        "şunun",
        "olarak",
        "şimdi",
        "benim",
        "senin",
        "bana",
        "sana",
        "ama",
        "fakat",
        "çünkü",
        "yani",
        "bile",
        "daha",
        "sonra",
        "gibi",
        "için",
        "kadar",
        "mi",
        "mı",
        "mu",
        "mü",
    }
    useful = [word for word in tokens if len(word) >= 4 and word.casefold() not in stop]
    return useful[-3:] or tokens[-3:] or ["..."]


def _temizle_emoji(text: str) -> str:
    """Pillow/ASS fallback'lerinde kırık emoji oluşmasını azaltmak için sembolleri temizler."""
    result = "".join(
        character
        for character in text
        if not (0x1F300 <= ord(character) <= 0x1FAFF or 0x2600 <= ord(character) <= 0x27BF)
    )
    return result.replace("\ufe0f", "").replace("\u200d", "").strip()


def _tr_upper(text: str) -> str:
    """Türkçe büyük I/İ dönüşümünü korur."""
    return text.replace("i", "İ").replace("ı", "I").upper()
