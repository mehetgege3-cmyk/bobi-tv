"""
Kalite Kapısı Modülü - 4 ana kalite kontrolü birleştirir.
- Loop Validation (Döngü Kusursuzluğu)
- Hook Engineering (Kanca Mühendisliği)
- Timing Analysis (Zamanlama ve Tempo)
- Dialogue Quality (Karakter Zıtlığı ve Diyalog Kalitesi)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Senaryo

from .dialogue_quality import diyalog_kalitesi_analiz, DiyaloKKaliteSonuc
from .hook_engineer import hook_muhendislik_yap, HookMuhendislikSonuc
from .loop_validator import loop_dogrula, LoopDogrulamaSonuc
from .timing import zamanlama_olustur, ZamanlamaSonuc

_LOG = logging.getLogger("bobi_tv.senaryo_v7.kalite_kapisi")


@dataclass
class KaliteRaporu:
    """Tüm kalite kontrollerinin birleştirilmiş raporu."""

    loop_sonuc: LoopDogrulamaSonuc
    kanca_sonuc: HookMuhendislikSonuc
    zamanlama_sonuc: ZamanlamaSonuc
    diyalog_sonuc: DiyaloKKaliteSonuc
    toplam_puan: int  # 0-100
    gecti: bool  # 70+ ise True
    oneriler: list[str]


def kalite_kapisindan_gecir(senaryo: Senaryo, esik_puani: int = 70) -> KaliteRaporu:
    """
    Senaryoyu 4 kalite kontrolünden geçir.

    Args:
        senaryo: Senaryo objesi
        esik_puani: Geçiş için minimum puan (default: 70)

    Returns:
        KaliteRaporu: Birleştirilmiş kalite raporu
    """
    _LOG.info("Kalite kapısı başlatılıyor: %s", senaryo.baslik)

    # 1. Loop validation
    loop_sonuc = loop_dogrula(senaryo)
    _LOG.debug("Loop puanı: %d", loop_sonuc.puan)

    # 2. Hook engineering
    kanca_sonuc = hook_muhendislik_yap(senaryo)
    _LOG.debug("Kanca puanı: %d", kanca_sonuc.puan)

    # 3. Timing analysis
    zamanlama_sonuc = zamanlama_olustur(senaryo)
    _LOG.debug("Zamanlama puanı: %d", zamanlama_sonuc.puan)

    # 4. Dialogue quality
    diyalog_sonuc = diyalog_kalitesi_analiz(senaryo)
    _LOG.debug("Diyalog puanı: %d", diyalog_sonuc.puan)

    # Toplam puan hesapla (ağırlıklı ortalama)
    # Loop: %25, Kanca: %25, Zamanlama: %25, Diyalog: %25
    toplam_puan = int(
        (loop_sonuc.puan * 0.25)
        + (kanca_sonuc.puan * 0.25)
        + (zamanlama_sonuc.puan * 0.25)
        + (diyalog_sonuc.puan * 0.25)
    )

    # Öneriler topla
    oneriler = []

    if not loop_sonuc.gecerli:
        oneriler.append(f"🔄 Loop: {loop_sonuc.aciklama}")
        if loop_sonuc.kopru_cumlesi:
            oneriler.append(f"   Köprü cümlesi önerisi: {loop_sonuc.kopru_cumlesi}")

    if not kanca_sonuc.gecerli:
        oneriler.append("🪝 Kanca: İlk cümle yeterince çekici değil")
        if kanca_sonuc.onerilen_varyant:
            oneriler.append(f"   Öneri: {kanca_sonuc.onerilen_varyant}")

    if not zamanlama_sonuc.gecerli:
        oneriler.append(f"⏱️ Zamanlama: {zamanlama_sonuc.aciklama}")
        if zamanlama_sonuc.onerilen_hiz:
            oneriler.append(f"   Önerilen hız: {zamanlama_sonuc.onerilen_hiz}")

    if diyalog_sonuc.puan < 70:
        if diyalog_sonuc.zıtlık_sorunları:
            oneriler.append("💬 Diyalog zıtlık sorunları:")
            for sorun in diyalog_sonuc.zıtlık_sorunları[:3]:  # İlk 3
                oneriler.append(f"   - {sorun}")

        if diyalog_sonuc.dogallık_sorunları:
            oneriler.append("💬 Doğallık sorunları:")
            for sorun in diyalog_sonuc.dogallık_sorunları[:3]:
                oneriler.append(f"   - {sorun}")

    # Geçti mi?
    gecti = toplam_puan >= esik_puani

    _LOG.info(
        "Kalite kapısı sonucu: puan=%d, gecti=%s (loop=%d, kanca=%d, zamanlama=%d, diyalog=%d)",
        toplam_puan,
        gecti,
        loop_sonuc.puan,
        kanca_sonuc.puan,
        zamanlama_sonuc.puan,
        diyalog_sonuc.puan,
    )

    return KaliteRaporu(
        loop_sonuc=loop_sonuc,
        kanca_sonuc=kanca_sonuc,
        zamanlama_sonuc=zamanlama_sonuc,
        diyalog_sonuc=diyalog_sonuc,
        toplam_puan=toplam_puan,
        gecti=gecti,
        oneriler=oneriler,
    )


def kalite_raporu_ozetle(rapor: KaliteRaporu) -> str:
    """
    Kalite raporunu okunabilir metin olarak özetle.

    Args:
        rapor: KaliteRaporu objesi

    Returns:
        Özet metin
    """
    lines = [
        "📊 KALITE RAPORU",
        "═══════════════════════════════════",
        f"Toplam Puan: {rapor.toplam_puan}/100",
        f"Durum: {'✅ GEÇTİ' if rapor.gecti else '❌ KALDI'}",
        "",
        "Detaylar:",
        f"  🔄 Loop:     {rapor.loop_sonuc.puan}/100 {'✅' if rapor.loop_sonuc.gecerli else '❌'}",
        f"  🪝 Kanca:    {rapor.kanca_sonuc.puan}/100 {'✅' if rapor.kanca_sonuc.gecerli else '❌'}",
        f"  ⏱️ Zamanlama: {rapor.zamanlama_sonuc.puan}/100 {'✅' if rapor.zamanlama_sonuc.gecerli else '❌'}",
        f"  💬 Diyalog:  {rapor.diyalog_sonuc.puan}/100 {'✅' if rapor.diyalog_sonuc.puan >= 70 else '❌'}",
    ]

    if rapor.oneriler:
        lines.append("")
        lines.append("Öneriler:")
        for oneri in rapor.oneriler:
            lines.append(f"  {oneri}")

    return "\n".join(lines)
