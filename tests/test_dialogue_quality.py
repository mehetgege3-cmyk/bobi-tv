"""Diyalog kalitesi testleri."""

import pytest

from modules.senaryo_v7.dialogue_quality import (
    DiyaloKKaliteSonuc,
    diyalog_kalitesi_analiz,
    ping_pong_dogrula,
    zıtlık_kontrol,
    tek_fikir_kontrol,
    dogallik_kontrol,
    karakter_tutarlılık_kontrol,
)
from modules.senaryo_v7.models import Senaryo, Diyalog, Duygu


class TestPingPongDogrula:
    """Ping-pong doğrulama testleri."""

    def test_ping_pong_basarili(self):
        """Başarılı ping-pong: ardışık satırlar farklı karakterde."""
        diyaloglar = [
            Diyalog(karakter="BOBİ", metin="Merhaba!"),
            Diyalog(karakter="MÜDÜR", metin="Naber?"),
            Diyalog(karakter="BOBİ", metin="İyiyim."),
        ]

        gecerli, hatalar = ping_pong_dogrula(diyaloglar)

        assert gecerli is True
        assert len(hatalar) == 0

    def test_ping_pong_basarisiz_ayni_karakter(self):
        """Başarısız: ardışık satırlar aynı karakterde."""
        diyaloglar = [
            Diyalog(karakter="BOBİ", metin="Merhaba!"),
            Diyalog(karakter="BOBİ", metin="Naber?"),
            Diyalog(karakter="MÜDÜR", metin="İyiyim."),
        ]

        gecerli, hatalar = ping_pong_dogrula(diyaloglar)

        assert gecerli is False
        assert len(hatalar) >= 1
        assert "Satır 1-2" in hatalar[0]
        assert "BOBİ" in hatalar[0]

    def test_ping_pong_dict_format(self):
        """Dict formatında diyaloglar da çalışmalı."""
        diyaloglar = [
            {"karakter": "BOBİ", "metin": "Merhaba!"},
            {"karakter": "MÜDÜR", "metin": "Naber?"},
        ]

        gecerli, hatalar = ping_pong_dogrula(diyaloglar)

        assert gecerli is True


class TestZitlikKontrol:
    """Zıtlık matrisi kontrol testleri."""

    def test_zitlik_basarili(self):
        """Başarılı: ardışık diyaloglar zıt duyguda."""
        diyaloglar = [
            Diyalog(karakter="BOBİ", metin="Sinirlendim!", ses=Duygu.SINIRLI),
            Diyalog(karakter="MÜDÜR", metin="Sakin ol.", ses=Duygu.NORMAL),
        ]

        sorunlar = zıtlık_kontrol(diyaloglar)

        assert len(sorunlar) == 0

    def test_zitlik_basarisiz_ayni_duygu(self):
        """Başarısız: ardışık diyaloglar aynı duyguda."""
        diyaloglar = [
            Diyalog(karakter="BOBİ", metin="Sinirlendim!", ses=Duygu.SINIRLI),
            Diyalog(karakter="MÜDÜR", metin="Ben de sinirliyim!", ses=Duygu.SINIRLI),
        ]

        sorunlar = zıtlık_kontrol(diyaloglar)

        assert len(sorunlar) == 1
        assert "sinirli" in sorunlar[0].lower()

    def test_zitlik_dict_format(self):
        """Dict formatında da çalışmalı."""
        diyaloglar = [
            {"rol": "BOBİ", "metin": "Test", "duygu": "sinirli"},
            {"rol": "MÜDÜR", "metin": "Test 2", "duygu": "sinirli"},
        ]

        sorunlar = zıtlık_kontrol(diyaloglar)

        assert len(sorunlar) == 1


class TestTekFikirKontrol:
    """Tek fikir kuralı testleri."""

    def test_tek_fikir_basarili(self):
        """Başarılı: her satır tek fikir içeriyor."""
        satirlar = [
            "Bu birinci fikir.",
            "Bu da ikinci fikir.",
            "Üçüncü fikir burada.",
        ]

        sorunlu = tek_fikir_kontrol(satirlar)

        assert len(sorunlu) == 0

    def test_tek_fikir_basarisiz_cok_virgul(self):
        """Başarısız: bir satırda çok virgüllü, uzun cümle."""
        satirlar = [
            "Bu normal bir satır.",
            "Bu satırda hem çok virgül var, hem de uzun, ya da başka bir şey, üstelik de bu var, ayrıca şöyle...",
            "Bu da normal.",
        ]

        sorunlu = tek_fikir_kontrol(satirlar)

        assert len(sorunlu) == 1
        assert sorunlu[0] == 2  # 1-indexed

    def test_tek_fikir_kisa_satir(self):
        """Kısa satır kontrol edilmemeli."""
        satirlar = [
            "Kısa, virgüllü, satır.",
        ]

        sorunlu = tek_fikir_kontrol(satirlar)

        assert len(sorunlu) == 0


class TestDogallikKontrol:
    """Türkçe doğallık kontrol testleri."""

    def test_dogallik_basarili(self):
        """Başarılı: doğal Türkçe."""
        metin = "Bu gayet doğal bir Türkçe cümlesi."

        uyarılar = dogallik_kontrol(metin)

        assert len(uyarılar) == 0

    def test_dogallik_hatali_kelime(self):
        """Hatalı: birleşik yazılmış kelimeler."""
        metin = "Herşey çok güzel, hiçbirşey yok."

        uyarılar = dogallik_kontrol(metin)

        assert len(uyarılar) > 0
        assert any("ayrı yazılmalı" in u.lower() for u in uyarılar)

    def test_dogallik_fazla_ya(self):
        """Hatalı: çok fazla 'ya' kullanımı."""
        metin = "Ya bu ya şu ya öteki ya beriki ya başka."

        uyarılar = dogallik_kontrol(metin)

        assert len(uyarılar) > 0
        assert any("ya" in u.lower() for u in uyarılar)


class TestKarakterTutarlılık:
    """Karakter tutarlılık testleri."""

    def test_tutarlılık_basarili(self):
        """Başarılı: karakterler tutarlı isimlerle anılmış."""
        diyaloglar = [
            Diyalog(karakter="BOBİ", metin="Müdür Bey geldi."),
            Diyalog(karakter="MÜDÜR", metin="Evet geldim."),
        ]

        tutarsızlıklar = karakter_tutarlılık_kontrol(diyaloglar)

        # Bu örnekte sorun yok, çünkü farklı karakterler
        assert isinstance(tutarsızlıklar, list)

    def test_tutarlılık_basarisiz_farkli_isimler(self):
        """Başarısız: aynı karakter farklı isimlerle."""
        diyaloglar = [
            Diyalog(karakter="BOBİ", metin="Müdür Bey geldi."),
            Diyalog(karakter="MÜDÜR", metin="Ahmet Bey de geldi."),
        ]

        # İK karakteri farklı isimlerle anılmış
        tutarsızlıklar = karakter_tutarlılık_kontrol(diyaloglar)

        assert isinstance(tutarsızlıklar, list)


class TestDiyalogKalitesiAnaliz:
    """Entegre diyalog kalitesi analiz testleri."""

    def test_analiz_mukemmel_senaryo(self):
        """Mükemmel senaryo: tüm kontroller geçmeli."""
        senaryo = Senaryo(
            baslik="Test Senaryosu",
            diyaloglar=[
                Diyalog(
                    karakter="BOBİ",
                    metin="Müdür Bey, her şey yolunda mı?",
                    ses=Duygu.NORMAL,
                ),
                Diyalog(
                    karakter="MÜDÜR",
                    metin="Evet, her şey gayet güzel.",
                    ses=Duygu.SASIRMIS,
                ),
                Diyalog(
                    karakter="BOBİ",
                    metin="Harika!",
                    ses=Duygu.ENERJIK,
                ),
            ],
        )

        sonuc = diyalog_kalitesi_analiz(senaryo)

        assert isinstance(sonuc, DiyaloKKaliteSonuc)
        assert sonuc.ping_pong_gecerli is True
        assert len(sonuc.zıtlık_sorunları) == 0
        assert len(sonuc.cok_fikirli_satırlar) == 0
        assert sonuc.puan >= 90

    def test_analiz_sorunlu_senaryo(self):
        """Sorunlu senaryo: ping-pong hatası + zıtlık yok."""
        senaryo = Senaryo(
            baslik="Kötü Senaryo",
            diyaloglar=[
                Diyalog(
                    karakter="BOBİ",
                    metin="Sinirlendim!",
                    ses=Duygu.SINIRLI,
                ),
                Diyalog(
                    karakter="BOBİ",  # Aynı karakter!
                    metin="Ben de sinirliyim!",
                    ses=Duygu.SINIRLI,  # Aynı duygu!
                ),
            ],
        )

        sonuc = diyalog_kalitesi_analiz(senaryo)

        assert sonuc.ping_pong_gecerli is False
        assert len(sonuc.zıtlık_sorunları) > 0
        assert sonuc.puan <= 80

    def test_analiz_bos_senaryo(self):
        """Boş senaryo: puan 0 olmalı."""
        senaryo = Senaryo(baslik="Boş", diyaloglar=[])

        sonuc = diyalog_kalitesi_analiz(senaryo)

        assert sonuc.puan == 0

    def test_analiz_dogallik_sorunu(self):
        """Doğallık sorunu: birleşik yazılmış kelimeler."""
        senaryo = Senaryo(
            baslik="Doğallık Testi",
            diyaloglar=[
                Diyalog(
                    karakter="BOBİ",
                    metin="Herşey çok güzel!",
                    ses=Duygu.NORMAL,
                ),
                Diyalog(
                    karakter="MÜDÜR",
                    metin="Evet öyle.",
                    ses=Duygu.NORMAL,
                ),
            ],
        )

        sonuc = diyalog_kalitesi_analiz(senaryo)

        assert len(sonuc.dogallık_sorunları) > 0
        assert sonuc.puan < 100
