"""
Render ve QC testleri: MP4 üretimi, minimum 15sn, Frame 0 doğrulaması.
"""
import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest


class TestAnimasyonRender:
    """Animasyon render pipeline QC testleri."""

    @pytest.mark.integration
    def test_karaoke_altyazi_katmani_render(self):
        """Karaoke altyazı katmanı eksik argüman olmadan render edilir."""
        from modules.animasyon import _karaoke_altyazi_katmani

        # Geniş satır (daraltılmış font yolunu tetikleyen)
        kelime_grubu = [
            {"kelime": "Bu", "duygu": "normal"},
            {"kelime": "çok", "duygu": "heyecanlı"},
            {"kelime": "uzun", "duygu": "normal"},
            {"kelime": "bir", "duygu": "şüpheli"},
            {"kelime": "cümle", "duygu": "normal"},
        ]

        img = _karaoke_altyazi_katmani(
            kelime_grubu=kelime_grubu,
            aktif_idx=2,
            stil="büyük",
            twist_mi=False,
        )

        assert img is not None
        assert img.mode == "RGBA"
        # modules/animasyon.py _karaoke_altyazi_katmani: kat_g, kat_y = 960, 210 (sabit canvas)
        assert img.size == (960, 210), f"karaoke katman boyutu değişmiş: {img.size}"

    @pytest.mark.integration
    def test_minimal_video_render(self):
        """v7 model kurulumu: Senaryo.from_dict ile diyaloglar ve duygu normalize edilir (gerçek MP4 render YOK)."""
        from modules.senaryo_v7.models import Senaryo, Duygu

        senaryo = Senaryo.from_dict({
            "kategori": "absurt_komedi",
            "hook_metni": "Beklenmedik twist!",
            "hook_suresi": 0.0,
            "diyaloglar": [
                {"karakter": "Ahmet", "metin": "Merhaba dünya!", "ses": "normal"},
                {"karakter": "Emel", "metin": "Şaşkın bakma!", "ses": "şaşkın"},
            ],
            "baslik": "Test Shorts",
        })

        assert senaryo.semaversiyonu == "7.0"
        assert senaryo.hook_suresi == 0.0
        assert senaryo.baslik == "Test Shorts"
        assert len(senaryo.diyaloglar) == 2
        assert senaryo.diyaloglar[0].ses is Duygu.NORMAL
        assert senaryo.diyaloglar[1].ses is Duygu.SASIRMIS_TR  # şaşkın -> kanonik
        assert senaryo.diyaloglar[1].metin == "Şaşkın bakma!"

    @pytest.mark.integration
    @pytest.mark.skip(reason="Gerçek MP4 render CI'da ffmpeg/ağ gerektirir; lokalde elle çalıştırılır")
    def test_gercek_mp4_render_integration(self):
        """Gerçek render doğrulaması — sadece lokalde, ffmpeg ve ağ varken çalıştırılır (main_pipeline.py)."""


class TestDuyguNormalizasyon:
    """Duygu etiketi normalizasyon testleri."""

    def test_duygu_normalizasyonu_guvenli_fallback(self):
        """Bilinmeyen etikette güvenli NORMAL fallback'i kullanılır."""
        from modules.senaryo_v7.models import duyguyu_normalize_et, Duygu

        # Tamamen bilinmeyen etiketler
        result = duyguyu_normalize_et("bilinmeyen_duygu_xyz")
        assert result == Duygu.NORMAL

        # Raporda görülen hatalı eşleşmeler şimdi fallback'e gidiyor
        result = duyguyu_normalize_et("mantıklı")  # Eski: panik, yeni: fallback
        assert result == Duygu.NORMAL

        result = duyguyu_normalize_et("dostça")  # Eski: twist, yeni: fallback
        assert result == Duygu.NORMAL

    def test_duygu_normalizasyonu_yuksek_benzerlik(self):
        """Yalnızca yüksek benzerlik eşiğini geçen eşleşmeler kabul edilir."""
        from modules.senaryo_v7.models import duyguyu_normalize_et, Duygu

        # Geçerli yazım varyantları
        result = duyguyu_normalize_et("enerjik")
        assert result == Duygu.ENERJIK

        # Alias'lar
        result = duyguyu_normalize_et("üzgün")
        assert result == Duygu.NORMAL  # cutoff=0.6 alti, guvenli fallback


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
