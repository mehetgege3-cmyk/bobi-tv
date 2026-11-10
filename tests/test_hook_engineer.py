"""Hook engineer testleri."""

import pytest

from modules.senaryo_v7.hook_engineer import (
    HookVaryant,
    HookMuhendislikSonuc,
    hook_varyant_uret,
    ust_bant_kes,
    yasakli_kelime_kontrol,
    yumusama_onerisi,
    ilk_satir_kontrol,
    hook_muhendislik_yap,
)


class TestHookVaryantUret:
    """Hook varyant üretim testleri."""

    def test_soru_formu(self):
        """Soru formu varyantı."""
        varyantlar = hook_varyant_uret("Bu bir test")

        assert len(varyantlar) == 3
        assert varyantlar[0].form == "soru"
        assert "?" in varyantlar[0].metin

    def test_sok_formu(self):
        """Şok formu varyantı."""
        varyantlar = hook_varyant_uret("Bu bir test")

        assert varyantlar[1].form == "şok"
        assert "Bakın:" in varyantlar[1].metin or "İşte" in varyantlar[1].metin

    def test_sayi_formu(self):
        """Sayı formu varyantı."""
        varyantlar = hook_varyant_uret("Bu bir test")

        assert varyantlar[2].form == "sayı"
        assert any(char.isdigit() for char in varyantlar[2].metin)

    def test_yasakli_kelime_yumusatma(self):
        """Yasaklı kelime yumuşatma."""
        varyantlar = hook_varyant_uret("Bu şok bir haber")

        # Şok formunda yasaklı kelime yumuşatılmış olmalı
        assert "şok" not in varyantlar[1].metin.lower()


class TestUstBantKes:
    """Üst bant kesme testleri."""

    def test_kisa_metin(self):
        """Kısa metin kesilmez."""
    metin = "Kısa metin"
    sonuc = ust_bant_kes(metin)

    assert sonuc == metin

    def test_uzun_metin_kelime_koruma(self):
        """Uzun metin kelime bütünlüğünü korur."""
    metin = "Bu çok uzun bir üst bant metnidir ve kesilmesi gerekir"
    sonuc = ust_bant_kes(metin, max_uzunluk=35)

    assert len(sonuc) <= 38  # 35 + "..."
    assert sonuc.endswith("...")
    assert " " in sonuc  # Kelime sınırlarında kesilmiş

    def test_kelime_ortasindan_kesmez(self):
        """Kelime ortasından kesmez."""
    metin = "Bu çok uzun bir test metnidir"
    sonuc = ust_bant_kes(metin, max_uzunluk=15)

    # Son karakter harf olmamalı (kelime ortasında değil)
    assert sonuc.rstrip(".").rstrip().split()[-1] in metin.split()


class TestYasakliKelimeKontrol:
    """Yasaklı kelime kontrol testleri."""

    def test_yasakli_kelime_var(self):
        """Yasaklı kelime tespit."""
    metin = "Bu şok bir haber!"
    var, kelimeler = yasakli_kelime_kontrol(metin)

    assert var is True
    assert "şok" in kelimeler

    def test_yasakli_kelime_yok(self):
        """Yasaklı kelime yok."""
    metin = "Normal bir haber"
    var, kelimeler = yasakli_kelime_kontrol(metin)

    assert var is False
    assert len(kelimeler) == 0

    def test_yumusama_onerisi(self):
        """Yumuşatma önerisi."""
    oneri = yumusama_onerisi("şok")

    assert oneri == "ilginç"


class TestIlkSatirKontrol:
    """İlk satır kontrol testleri."""

    def test_kisa_satir(self):
        """Kısa satır geçerli."""
    satir = "Bu kısa bir cümle"
    uzun, sayi, oneri = ilk_satir_kontrol(satir)

    assert uzun is False
    assert sayi == 4
    assert oneri is None

    def test_uzun_satir(self):
        """Uzun satır uyarı verir."""
    satir = "Bu çok uzun bir cümle ve maksimum kelime sayısını aşıyor"
    uzun, sayi, oneri = ilk_satir_kontrol(satir, max_kelime=10)

    assert uzun is True
    assert sayi > 10
    assert oneri is not None
    assert "uzun" in oneri.lower()

    def test_max_kelime_siniri(self):
        """Max kelime sınırı."""
    satir = " ".join(["kelime"] * 15)
    uzun, sayi, oneri = ilk_satir_kontrol(satir, max_kelime=12)

    assert uzun is True
    assert sayi == 15


class TestHookMuhendislikYap:
    """Hook mühendislik testleri."""

    def test_senaryo_hook_muhendislik(self):
        """Senaryo hook mühendislik."""
    from modules.senaryo_v7.models import Senaryo

    class MockSenaryo:
        hook_ust_bant = "Bu bir test üst bandı"
        tts_metinleri = ["Bu ilk satır"]

    senaryo = MockSenaryo()
    sonuc = hook_muhendislik_yap(senaryo)

    assert isinstance(sonuc, HookMuhendislikSonuc)
    assert sonuc.hook_ust_bant == "Bu bir test üst bandı"
    assert len(sonuc.varyantlar) == 3

    def test_yasakli_kelime_uyari(self):
        """Yasaklı kelime uyarısı."""
    class MockSenaryo:
        hook_ust_bant = "Şok haber: Bu gerçek!"
        tts_metinleri = ["Kısa satır"]

    senaryo = MockSenaryo()
    sonuc = hook_muhendislik_yap(senaryo)

    assert sonuc.yasakli_kelime_var is True
    assert "şok" in sonuc.yasakli_kelimeler
    assert len(sonuc.oneriler) > 0

    def test_uzun_ilk_satir_uyari(self):
        """Uzun ilk satır uyarısı."""
    class MockSenaryo:
        hook_ust_bant = "Normal başlık"
        tts_metinleri = ["Bu çok uzun bir ilk satır ve maksimum kelime sayısını aşıyor"]

    senaryo = MockSenaryo()
    sonuc = hook_muhendislik_yap(senaryo)

    assert sonuc.ilk_satir_uzun is True
    assert sonuc.ilk_satir_kelime_sayisi > 12


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
