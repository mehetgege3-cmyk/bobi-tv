"""
Döngü (Loop) Kusursuzluğu Modülü
- Son cümlenin üç nokta ile bitiş kontrolü
- İlk cümlenin bağlaçla başlayış kontrolü
- Son → ilk cümle geçiş akıcılığı
- Köprü cümlesi üretimi
- SFX offset hesaplama
- Kalite skoru (0-100)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Senaryo

_LOG = logging.getLogger("bobi_tv.senaryo_v7.loop_validator")


@dataclass
class LoopDogrulamaSonuc:
    """Loop doğrulama sonucu."""

    puan: int  # 0-100
    gecerli: bool  # 70+ ise True
    uc_nokta_var: bool
    baglanc_ile_basliyor: bool
    gecis_akici: bool
    aciklama: str
    kopru_cumlesi: str | None = None
    sfx_offset_ms: int = 0
    #: Öneri UYGULANDI mı (2026-11-11). Eskiden köprü cümlesi yalnız öneri
    #: listesine yazılıyordu; senaryo hiç değişmiyordu — aynı kanca motorunda
    #: bulunan "hesapla ama uygulama" hatasının kardeşi.
    uygulandi: bool = False


def loop_dogrula(senaryo: Senaryo) -> LoopDogrulamaSonuc:
    """
    Senaryonun döngü kalitesini doğrula.

    Args:
        senaryo: Senaryo objesi

    Returns:
        LoopDogrulamaSonuc: Doğrulama sonucu
    """
    diyaloglar = senaryo.diyaloglar
    if not diyaloglar or len(diyaloglar) < 2:
        return LoopDogrulamaSonuc(
            puan=0,
            gecerli=False,
            uc_nokta_var=False,
            baglanc_ile_basliyor=False,
            gecis_akici=False,
            aciklama="Yetersiz diyalog sayısı (min 2 gerekli)",
        )

    son_cumle = diyaloglar[-1].metin.strip()
    ilk_cumle = diyaloglar[0].metin.strip()

    # 1. Son cümlenin üç nokta ile bitişi
    uc_nokta_var = son_cumle.rstrip().endswith("...")

    # 2. İlk cümlenin bağlaçla başlayışı
    baglanc_listesi = [
        "ve",
        "ama",
        "fakat",
        "çünkü",
        "bu yüzden",
        "işte bu yüzden",
        "o yüzden",
        "dolayısıyla",
        "bu nedenle",
        "bu sayede",
        "öyle ki",
        "hatta",
        "üstelik",
        "ayrıca",
    ]

    ilk_cumle_lower = ilk_cumle.lower()
    baglanc_ile_basliyor = any(
        ilk_cumle_lower.startswith(baglanc + " ")
        for baglanc in baglanc_listesi
    )

    # 3. Geçiş akıcılığı (son → ilk cümle)
    gecis_akici = _gecis_akici_mi(son_cumle, ilk_cumle)

    # 4. Puan hesaplama
    puan = 0
    detaylar = []

    if uc_nokta_var:
        puan += 30
        detaylar.append("✅ Son cümle '...' ile bitiyor (+30)")
    else:
        detaylar.append("❌ Son cümle '...' ile bitmiyor (+0)")

    if baglanc_ile_basliyor:
        puan += 30
        detaylar.append("✅ İlk cümle bağlaçla başlıyor (+30)")
    else:
        detaylar.append("❌ İlk cümle bağlaçla başlamıyor (+0)")

    if gecis_akici:
        puan += 40
        detaylar.append("✅ Geçiş akıcı (+40)")
    else:
        detaylar.append("⚠️  Geçiş akıcı değil (+0)")

    # 5. Köprü cümlesi üret
    kopru_cumlesi = None
    if puan >= 40:
        kopru_cumlesi = _kopru_cumlesi_uret(son_cumle, ilk_cumle, gecis_akici)

    # 6. SFX offset hesapla
    sfx_offset_ms = _sfx_offset_hesapla(uc_nokta_var, gecis_akici)

    # 7. Sonuç
    gecerli = puan >= 70
    aciklama = "\n".join(detaylar)

    _LOG.info(
        "Loop doğrulama: puan=%d, geçerli=%s, açıklama=%s",
        puan,
        gecerli,
        aciklama.replace("\n", " | "),
    )

    return LoopDogrulamaSonuc(
        puan=puan,
        gecerli=gecerli,
        uc_nokta_var=uc_nokta_var,
        baglanc_ile_basliyor=baglanc_ile_basliyor,
        gecis_akici=gecis_akici,
        aciklama=aciklama,
        kopru_cumlesi=kopru_cumlesi,
        sfx_offset_ms=sfx_offset_ms,
    )


#: Köprü eklenirken kullanılan bağlaçlar (sırayla, rastgele DEĞİL — test edilebilir).
KOPRU_BAGLACLARI = ("Ve", "Ama", "Bu yüzden", "İşte bu yüzden", "O yüzden", "Dolayısıyla")


def dongu_uygula(senaryo: Senaryo) -> LoopDogrulamaSonuc:
    """Döngüyü KUSURSUZLAŞTIRIR: son cümleye "..." ekler, ilk cümleye bağlaç verir.

    Neden (2026-11-11 canlı test bulgusu): kalite raporu 68/100 ile KALDI ve
    döngü puanı 0/100'dü — son cümle "..." ile bitmiyordu, ilk cümle bağlaçla
    başlamıyordu. Öneri üretiliyor ama UYGULANMIYORDU; render/QC bunu
    engellemediği için video yine yayına gitti (kalitesiz döngü = izleyici
    videoyu baştan izlemez → izlenme süresi düşer → algoritma dağıtmaz).

    Kanca motoruyla aynı ilke: ölç, düzelt, TEKRAR ölç.
    """
    diyaloglar = getattr(senaryo, "diyaloglar", None) or []
    if len(diyaloglar) < 2:
        return loop_dogrula(senaryo)

    # 1) Son cümle "..." ile bitmiyorsa ekle (mevcut noktalamayı koru)
    son = str(diyaloglar[-1].metin or "").rstrip()
    if not son.endswith("..."):
        temel = son.rstrip(".!?… ")
        diyaloglar[-1].metin = f"{temel}..."

    # 2) İlk cümle bağlaçla başlamıyorsa köprü bağlacı ekle
    ilk = str(diyaloglar[0].metin or "").strip()
    kucuk = ilk.lower()
    baglaclar = ("ve ", "ama ", "fakat ", "çünkü ", "bu yüzden ", "işte bu yüzden ",
                 "o yüzden ", "dolayısıyla ", "bu nedenle ", "bu sayede ",
                 "öyle ki ", "hatta ", "üstelik ", "ayrıca ")
    if ilk and not kucuk.startswith(baglaclar):
        # Deterministik seçim: senaryo içeriğine göre (rastgele değil)
        baglac = KOPRU_BAGLACLARI[len(ilk) % len(KOPRU_BAGLACLARI)]
        diyaloglar[0].metin = f"{baglac} {ilk}"
        # Konuşulan metin listesi varsa o da güncellenir (TTS bunu okur)
        tts = list(getattr(senaryo, "tts_metinleri", None) or [])
        if tts and str(tts[0]).strip() == ilk:
            tts[0] = diyaloglar[0].metin
            senaryo.tts_metinleri = tts

    sonuc = loop_dogrula(senaryo)
    sonuc.uygulandi = True
    return sonuc


def _gecis_akici_mi(son_cumle: str, ilk_cumle: str) -> bool:
    """
    Son → ilk cümle geçişinin dilbilgisel ve anlamsal akıcılığını kontrol et.

    Basit heuristik:
    - Son cümle bir soru mu? İlk cümle cevap niteliğinde mi?
    - Son cümle bir durum anlatimi mi? İlk cümle sonuç mu?
    - Tematik tutarlılık var mı?
    """
    son_lower = son_cumle.lower().strip()
    ilk_lower = ilk_cumle.lower().strip()

    # Soru işareti ile biten son cümle + cevap niteliğinde ilk cümle
    if son_lower.endswith("?"):
        # İlk cümle cevap niteliğinde mi?
        cevap_baglaclari = [
            "evet",
            "hayır",
            "belki",
            "tabii",
            "elbette",
            "aslında",
            "gerçekten",
            "şimdi",
            "işte",
        ]
        if any(ilk_lower.startswith(cb) for cb in cevap_baglaclari):
            return True

    # Üç nokta ile biten son cümle + devam niteliğinde ilk cümle
    if son_lower.endswith("..."):
        # İlk cümle bağlaçla başlıyor mu?
        baglaclar = ["ve", "ama", "fakat", "çünkü", "bu yüzden", "o yüzden"]
        if any(ilk_lower.startswith(b) for b in baglaclar):
            return True

    # Anlamsal tutarlılık: aynı kelimelerden bazıları geçiyor mu?
    son_kelimeler = set(re.findall(r"\b\w+\b", son_lower))
    ilk_kelimeler = set(re.findall(r"\b\w+\b", ilk_lower))

    # Ortak kelime oranı
    if son_kelimeler and ilk_kelimeler:
        ortak = son_kelimeler & ilk_kelimeler
        oran = len(ortak) / min(len(son_kelimeler), len(ilk_kelimeler))
        if oran > 0.2:  # %20+ ortak kelime
            return True

    return False


def _kopru_cumlesi_uret(
    son_cumle: str, ilk_cumle: str, gecis_akici: bool
) -> str:
    """
    Son cümle + ilk cümleyi birleştirip köprü cümlesi üret.
    """
    # Son cümlenin sonundaki noktalama işaretlerini temizle
    son_temiz = son_cumle.rstrip(".!?…")

    # İlk cümlenin başındaki bağlaçları koru
    ilk_temiz = ilk_cumle.lstrip()

    if gecis_akici:
        # Akıcı geçiş: direkt birleştir
        return f"{son_temiz}... {ilk_temiz}"
    else:
        # Akıcı değil: köprü bağlaç ekle
        kopru_baglaclar = [
            "Ve",
            "Ama",
            "Bu yüzden",
            "İşte bu yüzden",
            "O yüzden",
            "Dolayısıyla",
        ]
        # Deterministik seçim (eskiden random.choice idi → test edilemez,
        # aynı senaryo her koşuda farklı öneri veriyordu).
        kopru = kopru_baglaclar[len(son_temiz) % len(kopru_baglaclar)]
        return f"{son_temiz}... {kopru} {ilk_temiz}"


def _sfx_offset_hesapla(uc_nokta_var: bool, gecis_akici: bool) -> int:
    """
    Loop'un ses tarafı için SFX offset hesapla.

    Son satırın sonunda:
    - ding + 150-300 ms sessizlik
    - İlk satırın whoosh'u ile çakışma olmaması için offset
    """
    if uc_nokta_var and gecis_akici:
        # İyi geçiş: ding + 200ms sessizlik + whoosh
        return 200
    elif uc_nokta_var:
        # Orta geçiş: ding + 250ms sessizlik
        return 250
    else:
        # Kötü geçiş: ding + 300ms sessizlik
        return 300


def loop_kalite_skoru(senaryo: Senaryo) -> int:
    """
    Döngü kalite skoru (0-100) üret.

    70 altını üretimden düşür veya yedek şablona geç.
    """
    sonuc = loop_dogrula(senaryo)
    return sonuc.puan


def loop_icin_yedek_sablon() -> dict:
    """
    Loop başarısız olduğunda kullanılacak yedek şablon.
    """
    return {
        "son_cumle_ek": "...",
        "ilk_cumle_baslangic": "Ve",
        "kopru_cumlesi": "Ve işte böyle...",
        "sfx_offset_ms": 300,
    }
