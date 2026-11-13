"""Mevcut senaryo şablonunu Gemini'ye gönder → yeni şablon önerisi al.

KULLANICI (2026-11-13): "Mevcut video üretme şablonunu değiştirelim, mevcut
şablonu geminiye at ve bize daha kaliteli etkileşimi yüksek olması için gerekli
tüm değişiklikleri yapsın."

Bu araç HİÇBİR KOD DEĞİŞTİRMEZ. Yalnız öneri toplar; uygulama ayrı adım.

GİRDİ : docs/SABLON_ISTEM.md  (şablon + gerçek kanal verisi + kısıtlar)
ÇIKTI : docs/SABLON_GEMINI_CEVAP.md
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ISTEM = Path("docs/SABLON_ISTEM.md")
CIKTI = Path("docs/SABLON_GEMINI_CEVAP.md")


def main() -> int:
    if not ISTEM.exists():
        print(f"❌ istem dosyası yok: {ISTEM}")
        return 2

    istem = ISTEM.read_text(encoding="utf-8")
    print(f"[Şablon] istem: {len(istem):,} karakter")

    from modules import gemini_web

    if not gemini_web.hazir_mi():
        print("❌ GEMINI_COOKIES yok — çerez kur: tools/gemini_cerez_kur.py")
        return 2

    print("[Şablon] Gemini'ye gönderiliyor (~240 sn)...")
    cevap = gemini_web.metin_uret(istem, sure=240)

    if not cevap or not cevap.strip():
        print(f"❌ cevap gelmedi: {gemini_web.durum()}")
        return 1

    CIKTI.write_text(
        "# Gemini'nin yeni şablon önerisi — HAM ÇIKTI\n\n"
        f"> İstem: `docs/SABLON_ISTEM.md` ({len(istem):,} karakter)\n"
        f"> Cevap: **{len(cevap):,} karakter**\n"
        "> Bu dosya **düzenlenmemiştir**. Uygulamadan önce insan denetimi gerekir.\n\n"
        "---\n\n" + cevap,
        encoding="utf-8",
    )
    print(f"✅ cevap alındı: {len(cevap):,} karakter → {CIKTI}")
    print(f"--- ilk 500 karakter ---\n{cevap[:500]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
