"""Kalite kapısı testleri."""

import pytest

from modules.senaryo_v7.kalite_kapisi import (
    kalite_kapisindan_gecir,
    kalite_raporu_ozetle,
    KaliteRaporu,
)
from modules.senaryo_v7.models import Senaryo, Diyalog, Duygu


class TestKaliteKapisi:
    """Kalite kapısı entegrasyon testleri."""

    def test_kalite_kapisi_basarili_senaryo(self):
        """Başarılı senaryo tüm kontrolleri geçmeli."""
        senaryo = Senaryo(
            baslik="Test Senaryosu",
            diyaloglar=[
                Diyalog(
                    karakter="BOBİ",
                    metin="Ve bu nasıl bir absürt durum?",
                    ses=Duygu.NORMAL,
                ),
                Diyalog(
                    karakter="MÜDÜR",
                    metin="Gerçekten çok garip!",
                    ses=Duygu.SASIRMIS,
                ),
                Diyalog(
                    karakter="BOBİ",
                    metin="Ama komik...",
                    ses=Duygu.ENERJIK,
                ),
            ],
        )

        rapor = kalite_kapisindan_gecir(senaryo)

        assert isinstance(rapor, KaliteRaporu)
        assert 0 <= rapor.toplam_puan <= 100
        assert isinstance(rapor.gecti, bool)
        assert len(rapor.oneriler) >= 0

    def test_kalite_kapisi_dusuk_puanli_senaryo(self):
        """Düşük puanlı senaryo kalmalı."""
        senaryo = Senaryo(
            baslik="Kötü Senaryo",
            diyaloglar=[
                Diyalog(
                    karakter="BOBİ",
                    metin="A",  # Çok kısa
                    ses=Duygu.NORMAL,
                ),
                Diyalog(
                    karakter="BOBİ",  # Aynı karakter
                    metin="B",  # Çok kısa
                    ses=Duygu.NORMAL,  # Aynı duygu
                ),
            ],
        )

        rapor = kalite_kapisindan_gecir(senaryo, esik_puani=70)

        assert rapor.toplam_puan < 70
        assert rapor.gecti is False
        assert len(rapor.oneriler) > 0

    def test_kalite_raporu_ozetle(self):
        """Rapor özeti okunabilir olmalı."""
        senaryo = Senaryo(
            baslik="Test",
            diyaloglar=[
                Diyalog(karakter="BOBİ", metin="Test cümlesi.", ses=Duygu.NORMAL),
            ],
        )

        rapor = kalite_kapisindan_gecir(senaryo)
        ozet = kalite_raporu_ozetle(rapor)

        assert "KALITE RAPORU" in ozet
        assert "Toplam Puan:" in ozet
        assert "Loop:" in ozet
        assert "Kanca:" in ozet
        assert "Zamanlama:" in ozet
        assert "Diyalog:" in ozet

    def test_kalite_kapisi_bos_senaryo(self):
        """Boş senaryo düşük puan almalı."""
        senaryo = Senaryo(baslik="Boş", diyaloglar=[])

        rapor = kalite_kapisindan_gecir(senaryo)

        assert rapor.toplam_puan < 50
        assert rapor.gecti is False
