

# ── 2026-11-13 ŞABLON DEVRİMİ ──────────────────────────────────────────────
def test_kelime_bandi_20_22_saniyeye_ayarli():
    """Şablon devrimi: 200-300 kelime (81-134 sn) → 50-70 kelime (~18-23 sn).

    GEREKÇE (kanal verisi): 20-22 sn videolar 1.100-1.200 izlenme, 1-2 dk
    videolar 0-14. Türkçe TTS ölçümü 185 kelime/dk → 55 kelime ≈ 18 sn.
    """
    import importlib

    from modules.ilginc_bilgi import kurallar

    importlib.reload(kurallar)
    # 2026-11-13 kalibrasyon (koşu 43403370045): 163 kelime/dk ÖLÇÜLDÜ.
    # 18-20 sn konuşma bütçesi → 45-58 kelime TÜM METİN.
    assert kurallar.KELIME_MIN == 45
    assert kurallar.KELIME_MAKS == 58
    # 200-300 bandı ASLA geri gelmesin
    assert kurallar.KELIME_MIN < 100 and kurallar.KELIME_MAKS < 100


def test_kelime_bandi_saniyeye_denk():
    """45-58 kelime, 17-22 sn konuşma hedefine denk gelmeli.

    163 kelime/dk = canlı ölçüm (koşu 43403370045: 86 kelime / 31.68 sn).
    Kapak 1.5 sn + pay ~1 sn → toplam video ~20-24 sn.
    """
    from modules.ilginc_bilgi import kurallar

    kelime_dk = 163.0  # ÖLÇÜLDÜ, varsayım değil
    for k in (kurallar.KELIME_MIN, kurallar.KELIME_MAKS):
        sn = k / (kelime_dk / 60)
        assert 15.0 <= sn <= 23.0, f"{k} kelime {sn:.1f} sn — hedef bant dışında"


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
    assert "TOPLAM METİN" in p, "prompt 'tüm metin' dediğini açıkça yazmalı"
    assert "200-300" not in p
    assert "20-22 saniye" in p or "İLK 2 SANİYE" in p


def test_r8_tum_metni_sayar_gercek_olcum():
    """R8 soru+cevap+sonuç HEPSİNİ saymalı — 2026-11-13 canlı koşu kanıtı.

    Koşu 43403370045 metni: 86 kelime (cevap 62, soru+sonuç 24) → TTS 31.68 sn.
    Eski R8 yalnız 'cevap'a bakıp 62 kelimeyi geçiriyordu; video 31 sn çıktı.
    Yeni R8 tüm metni sayar → MAKS aşılır → ihlal yakalanır.
    """
    from modules.ilginc_bilgi import kurallar

    bolumler = {
        kurallar.BASLIK_SORU: "Okyanusun en derin yerine ne kadar çok ışık tutarsan",
        kurallar.BASLIK_CEVAP: " ".join(["kelime"] * 62),
        kurallar.BASLIK_SONUC: " ".join(["kapanis"] * 24),
    }
    ihlal = kurallar.k8_kelime_sayisi("", bolumler, {})
    assert ihlal is not None, "tüm metin MAKS'ı aştı, ihlal olmalı"
    assert ihlal.kod == "R8"
    # Tüm metin sayıldığının kanıtı: ayrıntıdaki sayı 'cevap'ın 62 kelimesinden
    # belirgin biçimde büyük (soru + sonuç da eklendi) ve MAKS'ı aşıyor.
    sayi = int(ihlal.ayrinti.split()[0])
    assert sayi > kurallar.KELIME_MAKS, ihlal.ayrinti
    assert sayi > 62, f"yalnız 'cevap' sayılmış olmalı değil: {ihlal.ayrinti}"

    # Bant içi: 50 kelime tüm metin → ihlal yok
    bolumler[kurallar.BASLIK_CEVAP] = " ".join(["kelime"] * 30)
    bolumler[kurallar.BASLIK_SONUC] = " ".join(["kapanis"] * 10)
    assert kurallar.k8_kelime_sayisi("", bolumler, {}) is None
