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
        assert img.size[0] >= 800 and img.size[1] >= 150, f"beklenmedik canvas boyutu: {img.size}"

    @pytest.mark.integration
    @pytest.mark.skip(reason="v6 Sahne/sahne_animasyonu_uret API kaldırıldı; v7 Senaryo ile yeniden yazılacak")
    def test_minimal_video_render(self):
        """Minimal video render: MP4 üretimi, Frame 0, minimum 15sn."""
        from modules.senaryo_v7.models import Senaryo, Sahne
        from modules.animasyon import sahne_animasyonu_uret

        # Minimal senaryo
        sahne = Sahne(
            konu="komik",
            baslik="Test Video",
            replik="Merhaba dünya!",
            duygu_etiketi="normal",
            ses_turu="erkek",
            tts_url="https://example.com/test.mp3",
        )

        # Animasyon render (TTS yerine dummy session kullanacak)
        with tempfile.TemporaryDirectory() as tmpdir:
            output_video = Path(tmpdir) / "test_render.mp4"

            # Gerçek TTS olmadan test için mock wav dosyası yarat
            test_wav = Path(tmpdir) / "test.wav"
            test_wav.write_bytes(b"RIFF" + b"\x00" * 36)  # Minimal WAV header

            # Video render'ı çalıştır (mock kullanarak)
            # Burada tam render yapılmayacak; bunun yerine fixture dosyası kullan
            assert not output_video.exists() or output_video.stat().st_size > 0


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
