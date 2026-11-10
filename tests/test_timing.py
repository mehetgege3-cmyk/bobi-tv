"""Timing modülü testleri."""

import pytest

from modules.senaryo_v7.timing import (
    hece_sayisi_turkce,
    sure_tahmin_hece,
    satir_zamanlama_hesapla,
    satir_duzelt,
    zamanlama_olustur,
    MIN_SURE_SN,
    MAX_SURE_SN,
)


class TestHeceSayisi:
    """Hece sayısı testleri."""

    def test_basit_kelime(self):
        """Basit kelime hece sayısı."""
        assert hece_sayisi_turkce("elma") == 2
        assert hece_sayisi_turkce("masa") == 2
        assert hece_sayisi_turkce("kitap") == 2

    def test_turkce_karakterler(self):
        """Türkçe karakterler."""
        assert hece_sayisi_turkce("göz") == 1
        assert hece_sayisi_turkce("gün") == 1
        assert hece_sayisi_turkce("iş") == 1

    def test_cumle(self):
        """Cümle hece sayısı."""
        cumle = "Bu bir test cümlesi"
        # Bu (1) + bir (1) + test (1) + cümlesi (3) = 6
        assert hece_sayisi_turkce(cumle) == 6

    def test_bos_metin(self):
        """Boş metin."""
        assert hece_sayisi_turkce("") == 1  # En az 1


class TestSureTahmin:
    """Süre tahmin testleri."""

    def test_normal_hiz(self):
        """Normal hız."""
        metin = "Bu bir test"
        sure = sure_tahmin_hece(metin, "normal")

        # 4 hece / 6 hece/sn ≈ 0.67 sn
        assert 0.5 <= sure <= 1.0

    def test_panik_hizli(self):
        """Panik duygusu hızlı."""
        metin = "Bu bir test cümlesi"
        sure_normal = sure_tahmin_hece(metin, "normal")
        sure_panik = sure_tahmin_hece(metin, "panik")

        assert sure_panik <= sure_normal  # Panik daha hızlı veya eşit

    def test_bikkin_yavas(self):
        """Bıkkın duygusu yavaş."""
        metin = "Bu bir test"
        sure_normal = sure_tahmin_hece(metin, "normal")
        sure_bikkin = sure_tahmin_hece(metin, "bikkin")

        assert sure_bikkin > sure_normal  # Bıkkın daha yavaş


class TestSatirZamanlama:
    """Satır zamanlama testleri."""

    def test_tek_satir(self):
        """Tek satır zamanlama."""
        satirlar = ["Bu bir test cümlesi"]
        sonuc = satir_zamanlama_hesapla(satirlar)

        assert sonuc.toplam_sure_sn > 0
        assert len(sonuc.satirlar) == 1
        assert sonuc.satirlar[0].baslangic_sn == 0.0

    def test_coklu_satir(self):
        """Çoklu satır zamanlama."""
        satirlar = [
            "Birinci satır",
            "İkinci satır",
            "Üçüncü satır",
        ]
        sonuc = satir_zamanlama_hesapla(satirlar)

        assert len(sonuc.satirlar) == 3
        assert sonuc.satirlar[0].bitis_sn == sonuc.satirlar[1].baslangic_sn

    def test_kesme_noktalari(self):
        """Kesme noktaları."""
        satirlar = ["Bu" * 20]  # Uzun satır (~15 sn)
        sonuc = satir_zamanlama_hesapla(satirlar)

        # Her 2 saniyede kesme
        assert len(sonuc.kesme_noktalari) > 0
        assert all(nokta % 2 == 0 for nokta in sonuc.kesme_noktalari)

    def test_twist_ani(self):
        """Twist anı hesaplama."""
        satirlar = ["Bir", "İki", "Üç"]
        sonuc = satir_zamanlama_hesapla(satirlar)

        assert sonuc.twist_ani_sn is not None
        assert sonuc.twist_ani_sn < sonuc.toplam_sure_sn

    def test_tatli_nokta(self):
        """Tatlı nokta kontrolü."""
        # 18 sn'lik metin oluştur
        satirlar = ["Bu" * 30 for _ in range(6)]
        sonuc = satir_zamanlama_hesapla(satirlar)

        # Süre aralığı kontrolü
        assert MIN_SURE_SN <= sonuc.toplam_sure_sn <= MAX_SURE_SN or not sonuc.tatli_noktada_mi


class TestSatirDuzelt:
    """Satır düzeltme testleri."""

    def test_kisa_sure_duzelt(self):
        """Kısa süre düzeltme."""
        satirlar = ["Kısa"]
        duzeltilmis, degisiklikler = satir_duzelt(satirlar)

        assert len(duzeltilmis) >= len(satirlar)

    def test_uzun_sure_duzelt(self):
        """Uzun süre düzeltme."""
        satirlar = ["Bu çok uzun bir satır ve ikiye bölünmesi gerekiyor"]
        duzeltilmis, degisiklikler = satir_duzelt(satirlar)

        assert len(duzeltilmis) >= len(satirlar)  # Bölme sonucu artabilir


class TestZamanlamaOlustur:
    """Senaryo zamanlama testleri."""

    def test_senaryo_zamanlama(self):
        """Senaryo zamanlama."""
        from modules.senaryo_v7.models import Senaryo

        class MockSenaryo:
            tts_metinleri = [
                "Birinci satır",
                "İkinci satır",
                "Üçüncü satır",
            ]
            diyaloglar = []

        senaryo = MockSenaryo()
        sonuc = zamanlama_olustur(senaryo)

        assert sonuc.toplam_sure_sn > 0
        assert len(sonuc.satirlar) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
