"""Çalışma dizinleri — geçici üretim çıktıları workspace DIŞINA yazılabilir.

NEDEN (2026-11-12, kullanıcı fikri): "Root diskte 20 GB boş var ve
/home/user/out snapshot'a dahil değil, işi oraya taşıyayım."

Workspace (snapshot) kotası 128 MB / 10.000 dosya. Render WAV'ları + MP4'ler
tek başına 99 MB'a çıkıp "Workspace over budget" hatası verdi (127 dosya
kaydedilemedi). Geçici üretim çıktıları (tts, render, animasyon, kapak
adayları) zaten .gitignore'da ve yayından sonra GEREKSİZ → bunları
snapshot'a alınmayan diske yazmak doğru çözüm.

KULLANIM:
  BOBITV_GECICI_KOK=/home/user/out   → tts/render/animasyon buraya yazılır
  (tanımsızsa eski davranış: bobi_tv/production/... — GitHub Actions böyle
   çalışır, orada disk sorunu yok ve CI önbelleği bu yolu bekliyor)

`git add bobi_tv/state/` gibi komutlar bu dizinlere dokunmadığı için arşiv
commit'i de etkilenmez.
"""

from __future__ import annotations

import os
from pathlib import Path

#: Snapshot dışı kök (varsa). Boşsa None.
GECICI_KOK = Path(os.environ["BOBITV_GECICI_KOK"]) if os.environ.get("BOBITV_GECICI_KOK") else None


def _yol(varsayilan: str) -> Path:
    """Varsayılan yolu, geçici kök tanımlıysa oraya taşır (bobi_tv/ önekini atar)."""
    if GECICI_KOK is None:
        return Path(varsayilan)
    parcalar = Path(varsayilan).parts
    if parcalar and parcalar[0] == "bobi_tv":
        parcalar = parcalar[1:]
    return GECICI_KOK.joinpath(*parcalar)


#: Konumlar (tek kaynak — modüller bunları import eder)
TTS_YOLU = _yol("bobi_tv/production/tts")
RENDER_YOLU = _yol("bobi_tv/production/render")
ANIMASYON_YOLU = _yol("bobi_tv/production/animation")
OUTPUT_YOLU = _yol("bobi_tv/output")


def hazirla() -> None:
    """Dizinleri oluşturur (idempotent)."""
    for yol in (TTS_YOLU, RENDER_YOLU, ANIMASYON_YOLU, OUTPUT_YOLU):
        try:
            yol.mkdir(parents=True, exist_ok=True)
        except Exception as e:  # pragma: no cover
            print(f"[Dizinler] {yol} oluşturulamadı: {str(e)[:80]}")


def ozet() -> str:
    """Log/teşhis için tek satır."""
    return (
        f"geçici kök: {GECICI_KOK or '(workspace içi)'} | tts={TTS_YOLU} | "
        f"render={RENDER_YOLU} | output={OUTPUT_YOLU}"
    )
