"""Loop validator testleri."""

import pytest

from modules.senaryo_v7.loop_validator import (
    LoopDogrulamaSonuc,
    loop_dogrula,
    loop_kalite_skoru,
    _gecis_akici_mi,
    _kopru_cumlesi_uret,
    _sfx_offset_hesapla,
)
from modules.senaryo_v7.models import Senaryo, Sahne


class TestLoopValidator:
    """Loop doğrulama testleri."""

    def test_loop_dogrula_basarili(self):
        """Başarılı loop: üç nokta + bağlaç + akıcı geçiş."""
        senaryo = Senaryo(
            konu="komedi",
            sahneler=[
                Sahne(
                    baslik="Test",
                    replikler=[
                        "Ve bu nasıl bir komedidir...",
                        "Böyle absürt bir şey görmedim!",
                        "Ama gerçekten çok komik...",
                    ],
                    duygu_etiketi="normal",
                    ses_turu="erkek",
                )
            ],
        )

        sonuc = loop_dogrula(senaryo)

        assert sonuc.puan == 100
        assert sonuc.gecerli is True
        assert sonuc.uc_nokta_var is True
        assert sonuc.baglanc_ile_basliyor is True
        assert sonuc.gecis_akici is True
        assert sonuc.kopru_cumlesi is not None
        assert "..." in sonuc.kopru_cumlesi

    def test_loop_dogrula_uc_nokta_eksik(self):
        """Üç nokta eksik."""
        senaryo = Senaryo(
            konu="komedi",
            sahneler=[
                Sahne(
                    baslik="Test",
                    replikler=[
                        "Ve başladık",
                        "Ortada gidiyoruz",
                        "Bitti!",
                    ],
                    duygu_etiketi="normal",
                    ses_turu="erkek",
                )
            ],
        )

        sonuc = loop_dogrula(senaryo)

        assert sonuc.puan == 30  # Sadece bağlaç
        assert sonuc.gecerli is False
        assert sonuc.uc_nokta_var is False
        assert sonuc.baglanc_ile_basliyor is True

    def test_loop_dogrula_baglanc_eksik(self):
        """Bağlaç eksik."""
        senaryo = Senaryo(
            konu="komedi",
            sahneler=[
                Sahne(
                    baslik="Test",
                    replikler=[
                        "Bu bir cümle",
                        "Ortada gidiyoruz",
                        "Son cümle...",
                    ],
                    duygu_etiketi="normal",
                    ses_turu="erkek",
                )
            ],
        )

        sonuc = loop_dogrula(senaryo)

        assert sonuc.puan == 30  # Sadece üç nokta
        assert sonuc.baglanc_ile_basliyor is False

    def test_gecis_akici_soru_cevap(self):
        """Soru-cevap geçişi."""
        son = "Peki bu nasıl olacak?"
        ilk = "İşte böyle olacak!"

        assert _gecis_akici_mi(son, ilk) is True

    def test_gecis_akici_baglanc(self):
        """Bağlaçlı geçiş."""
        son = "Durum böyle..."
        ilk = "Ve bu yüzden..."

        assert _gecis_akici_mi(son, ilk) is True

    def test_gecis_akici_ortak_kelime(self):
        """Ortak kelime ile geçiş."""
        son = "Bu video çok komik!"
        ilk = "Komik videolar her zaman iyi."

        assert _gecis_akici_mi(son, ilk) is True

    def test_kopru_cumlesi_uret(self):
        """Köprü cümlesi üretimi."""
        son = "Ve böyle bitti..."
        ilk = "Ve baştan başladık"

        kopru = _kopru_cumlesi_uret(son, ilk, gecis_akici=True)

        assert "..." in kopru
        assert "Ve" in kopru

    def test_sfx_offset_hesapla(self):
        """SFX offset hesaplama."""
        # İyi geçiş
        assert _sfx_offset_hesapla(True, True) == 200

        # Orta geçiş
        assert _sfx_offset_hesapla(True, False) == 250

        # Kötü geçiş
        assert _sfx_offset_hesapla(False, False) == 300

    def test_loop_kalite_skoru(self):
        """Kalite skoru hesaplama."""
        senaryo = Senaryo(
            konu="komedi",
            sahneler=[
                Sahne(
                    baslik="Test",
                    replikler=[
                        "Ve başladık...",
                        "Ortada gidiyoruz",
                        "Son cümle...",
                    ],
                    duygu_etiketi="normal",
                    ses_turu="erkek",
                )
            ],
        )

        skor = loop_kalite_skoru(senaryo)

        assert 0 <= skor <= 100
        assert skor >= 70  # Bu örnek geçerli olmalı

    def test_yetersiz_replik(self):
        """Yetersiz replik sayısı."""
        senaryo = Senaryo(
            konu="komedi",
            sahneler=[
                Sahne(
                    baslik="Test",
                    replikler=["Tek cümle"],
                    duygu_etiketi="normal",
                    ses_turu="erkek",
                )
            ],
        )

        sonuc = loop_dogrula(senaryo)

        assert sonuc.puan == 0
        assert sonuc.gecerli is False
        assert "Yetersiz" in sonuc.aciklama


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
