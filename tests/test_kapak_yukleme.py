"""Kapak gömme + yükleme düzeltmeleri.

KÖK NEDENLER (2026-11-13, yt-dlp + artifact kanıtı — docs/KAPAK_TESHIS.md):
  1) `paket["final_video"]` güncellenmiyordu → YouTube'a KAPAKSIZ video gidiyordu.
  2) Kapak 1 kare (33 ms) görünüyordu → göz yakalayamaz.
"""

import inspect
from pathlib import Path

from modules import kapak_arena, uretim_hatti


def test_uretim_hatti_final_video_gunceller():
    """KÖK NEDEN 1: kapak üretildikten sonra final_video güncellenmeli."""
    kaynak = inspect.getsource(uretim_hatti.uretim_hatti_calistir)
    assert 'paket["final_video"] = video_yolu' in kaynak, (
        "final_video güncellenmiyor → YouTube'a kapaksız video gider"
    )


def test_kapak_suresi_1_5_saniye():
    """KÖK NEDEN 2: 1 kare (33 ms) yerine 45 kare (1.5 sn)."""
    kaynak = inspect.getsource(kapak_arena.ilk_kareye_yerlestir)
    assert "end_frame=45" in kaynak
    assert "end_frame=1," not in kaynak and "end_frame=1]" not in kaynak
    assert '"-t", "1.5"' in kaynak


def test_kapak_suresi_hesabi():
    """45 kare @ 30 fps = 1.5 sn (ölçümle aynı)."""
    assert 45 / 30 == 1.5


def test_kapak_yenile_araci_var():
    yol = Path("tools/kapak_yenile.py")
    assert yol.exists()
    kaynak = yol.read_text(encoding="utf-8")
    # K8: kullanıcının tek istemi kullanılmalı
    assert "İsimli short video için kapak fotoğrafı istiyorum" in kaynak
    # Gemini web çerezi kullanılmalı (Arena veya Gemini API değil)
    assert "gemini_web" in kaynak
    assert "_kapak_yukle" in kaynak  # thumbnails.set


def test_kapak_yenile_workflow_var():
    yol = Path(".github/workflows/kapak_yenile.yml")
    assert yol.exists()
    import yaml

    d = yaml.safe_load(yol.read_text(encoding="utf-8"))
    assert "GEMINI_COOKIES" in yol.read_text(encoding="utf-8")
    assert "workflow_dispatch" in d.get("on", d.get(True, {}))
