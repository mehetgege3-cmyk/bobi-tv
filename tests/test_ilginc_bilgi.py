

# ── 2026-11-13 ŞABLON DEVRİMİ ──────────────────────────────────────────────
def test_kelime_bandi_20_22_saniyeye_ayarli():
    """Şablon devrimi: 200-300 kelime (81-134 sn) → 50-70 kelime (~18-23 sn).

    GEREKÇE (kanal verisi): 20-22 sn videolar 1.100-1.200 izlenme, 1-2 dk
    videolar 0-14. Türkçe TTS ölçümü 185 kelime/dk → 55 kelime ≈ 18 sn.
    """
    import importlib

    from modules.ilginc_bilgi import kurallar

    importlib.reload(kurallar)
    assert kurallar.KELIME_MIN == 50
    assert kurallar.KELIME_MAKS == 70
    # 200-300 bandı ASLA geri gelmesin
    assert kurallar.KELIME_MIN < 100 and kurallar.KELIME_MAKS < 100


def test_kelime_bandi_saniyeye_denk():
    """50-70 kelime, 20-22 sn hedefine denk gelmeli (185 kelime/dk ölçümü)."""
    from modules.ilginc_bilgi import kurallar

    kelime_dk = 185.0
    for k in (kurallar.KELIME_MIN, kurallar.KELIME_MAKS):
        sn = k / (kelime_dk / 60)
        assert 15.0 <= sn <= 24.0, f"{k} kelime {sn:.1f} sn — hedef bant dışında"


def test_kanca_soru_olmak_zorunda_degil():
    """R1: '?' zorunluluğu kaldırıldı — iddia kancası da geçerli.

    Kanal verisi: kazanan 20-22 sn videoların 4'ü soru değil iddia/olay kancası.
    """
    from modules.ilginc_bilgi import kurallar

    metin = (
        f"{kurallar.BASLIK_SORU}\nPiramitleri köleler inşa etmedi, bu bir yalan.\n\n"
        f"{kurallar.BASLIK_CEVAP}\n" + ("kelime " * 55) + "\n\n"
        f"{kurallar.BASLIK_SONUC}\nTarih yanıltıyor."
    )
    ihlal = kurallar.k1_soru_ile_basla(metin, kurallar.bolumleri_ayir(metin), {})
    assert ihlal is None, f"'?' olmadan R1 ihlal etmemeli: {ihlal}"


def test_cok_kisa_kanca_hala_ihlal():
    """R1 gevşedi ama TAMAMEN boş kanca hâlâ yayınlanamaz."""
    from modules.ilginc_bilgi import kurallar

    metin = (
        f"{kurallar.BASLIK_SORU}\nHa?\n\n"
        f"{kurallar.BASLIK_CEVAP}\ncevap\n\n"
        f"{kurallar.BASLIK_SONUC}\nson"
    )
    ihlal = kurallar.k1_soru_ile_basla(metin, kurallar.bolumleri_ayir(metin), {})
    assert ihlal is not None
    assert ihlal.kod == "R1"


def test_prompt_yeni_sure_bandini_yazar():
    """Üretim istemi yeni bandı ve iddia kancasını içermeli."""
    from modules.ilginc_bilgi import kurallar, uretici
    from modules.ilginc_bilgi.etkilesim import TaktikSecimi

    p = uretici.bilgi_promptu(
        "bilim_teknoloji",
        TaktikSecimi(kod="T1", ad="test", talimat="talimat"),
        [],
    )
    assert f"{kurallar.KELIME_MIN}-{kurallar.KELIME_MAKS} KELİME" in p
    assert "200-300" not in p
    assert "20-22 saniye" in p or "İLK 2 SANİYE" in p
