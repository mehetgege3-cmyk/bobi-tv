"""Loop validator testleri."""

import pytest

from modules.senaryo_v7.loop_validator import (
    LoopDogrulamaSonuc,
    loop_dogrula,
)
from modules.senaryo_v7.models import Senaryo, Diyalog, Duygu


class TestLoopValidator:
    """Loop doğrulama testleri."""

    def test_loop_dogrula_basarili(self):
        """Başarılı loop: üç nokta + bağlaç + akıcı geçiş."""
        senaryo = Senaryo(
            baslik="Test Senaryosu",
            diyaloglar=[
                Diyalog(karakter="BOBİ", metin="Ve bu nasıl bir komedidir...", ses=Duygu.NORMAL),
                Diyalog(karakter="MÜDÜR", metin="Böyle absürt bir şey görmedim!", ses=Duygu.SASIRMIS),
                Diyalog(karakter="BOBİ", metin="Ama gerçekten çok komik...", ses=Duygu.ENERJIK),
            ],
        )

        sonuc = loop_dogrula(senaryo)

        assert sonuc.gecerli is True
        assert sonuc.uc_nokta_var is True
        assert sonuc.baglanc_ile_basliyor is True

    def test_loop_dogrula_uc_nokta_eksik(self):
        """Üç nokta eksik."""
        senaryo = Senaryo(
            baslik="Test",
            diyaloglar=[
                Diyalog(karakter="BOBİ", metin="Ve başladık", ses=Duygu.NORMAL),
                Diyalog(karakter="MÜDÜR", metin="Ortada gidiyoruz", ses=Duygu.NORMAL),
                Diyalog(karakter="BOBİ", metin="Bitti!", ses=Duygu.NORMAL),
            ],
        )

        sonuc = loop_dogrula(senaryo)

        assert sonuc.gecerli is False
        assert sonuc.uc_nokta_var is False
        assert sonuc.baglanc_ile_basliyor is True

    def test_loop_dogrula_baglanc_eksik(self):
        """Bağlaç eksik."""
        senaryo = Senaryo(
            baslik="Test",
            diyaloglar=[
                Diyalog(karakter="BOBİ", metin="Bu bir cümle", ses=Duygu.NORMAL),
                Diyalog(karakter="MÜDÜR", metin="Ortada gidiyoruz", ses=Duygu.NORMAL),
                Diyalog(karakter="BOBİ", metin="Son cümle...", ses=Duygu.NORMAL),
            ],
        )

        sonuc = loop_dogrula(senaryo)

        assert sonuc.baglanc_ile_basliyor is False

    def test_loop_dogrula_bos_senaryo(self):
        """Boş senaryo."""
        senaryo = Senaryo(baslik="Boş", diyaloglar=[])

        sonuc = loop_dogrula(senaryo)

        assert sonuc.puan == 0
        assert sonuc.gecerli is False
