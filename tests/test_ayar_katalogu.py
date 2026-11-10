"""TODO 1 — Ayar kataloğu testleri: tek doğruluk kaynağının bütünlüğü.

Kapsam: env_adi doluluğu, sadece_goruntule alan kuralları, secret varsayılan
yasağı, GUNLUK_MAKS tavanı (6), temizlik grubunun etkili=False dürüstlüğü,
katalog şemasının bütünlüğü ve kaldırılan ayarların gerçekten yokluğu.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Repo kökünü import yoluna ekle (tests/ altından çalıştırılırken)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.ayar_katalogu import (  # noqa: E402
    GRUPLAR,
    KATALOG,
    KOTA_TAVANI,
    RISKLER,
    TEMIZLIK_UYARI,
    TIPLER,
    VIDEO_INSERT_MALIYETI,
    YOUTUBE_GUNLUK_KOTA_BIRIM,
    anahtarlar,
    ayar_getir,
    degistirilebilir_mi,
    etkin_gunluk_maks,
    grup_ayarlari,
    tumu,
)


def test_her_ayarin_env_adi_dolu() -> None:
    """P4 test sözleşmesi: env köprüsü her ayarda bir env adı bulabilmeli."""
    for a in tumu():
        assert isinstance(a["env_adi"], str), a["anahtar"]
        assert a["env_adi"].strip() != "", a["anahtar"]


def test_sadece_goruntule_tipinde_secenek_min_max_yok() -> None:
    """Görüntüleme ayarları uygulanmaz; seçenek/aralık alanları anlamsızdır ve YOK'tur."""
    for a in tumu():
        if a["tip"] == "sadece_goruntule":
            assert a["secenekler"] is None, a["anahtar"]
            assert a["min"] is None, a["anahtar"]
            assert a["max"] is None, a["anahtar"]


def test_hicbir_secretin_varsayilan_degeri_yok() -> None:
    """Secret'ın katalogda varsayılanı OLMAZ — değer yalnızca GitHub Secrets'ta yaşar."""
    for a in tumu():
        if a.get("secret"):
            assert a["varsayilan"] is None, a["anahtar"]
            assert a["tip"] == "sadece_goruntule", a["anahtar"]


def test_gunluk_maks_seceneklerinin_maksimumu_6() -> None:
    """P4: 10000/1600 = 6 — katalogda 7+ seçenek YOK, varsayılan tavanın altında."""
    a = ayar_getir("GUNLUK_MAKS")
    assert a is not None, "GUNLUK_MAKS katalogda yok"
    secenekler = a["secenekler"]
    assert isinstance(secenekler, list) and secenekler
    sayilar = [int(s) for s in secenekler]
    assert max(sayilar) == 6, f"tavan 6 olmalı, gelen: {sayilar}"
    assert KOTA_TAVANI == 6
    assert YOUTUBE_GUNLUK_KOTA_BIRIM // VIDEO_INSERT_MALIYETI == KOTA_TAVANI


def test_temizlik_grubu_etkili_ama_kilitli() -> None:
    """TODO 11 düzeltmesi (2026-11-11): temizlik ayarları ETKİLİDİR, kilitlidir.

    Önceki sözleşme "etkili DEĞİLDİR (H1)" diyordu — YANLIŞTI. Gerçek:
    main_pipeline.py:145-152 bu env'leri okuyup dusuk_izlenmeli_videolari_temizle()
    çağırıyor ve youtube_upload.py:279-290 videos.delete ile GERÇEK video siliyor.
    H1 yalnızca İKİNCİ mekanizma (cleanup_low_views.yml) için geçerlidir.

    Kilit (sadece_goruntule + degistirilebilir_mi False) korunur: kaza koruması.
    Açıklama, kullanıcıyı yanlış yönlendirmemek için "SİLER" demek ZORUNDA.
    """
    temizlik = grup_ayarlari("temizlik")
    assert len(temizlik) == 3
    for a in temizlik:
        assert a["etkili"] is True, f"{a['anahtar']} gerçekten etkili (video siler)"
        assert a["tip"] == "sadece_goruntule", a["anahtar"]
        assert degistirilebilir_mi(a) is False, a["anahtar"]
        assert "SİLER" in a["aciklama"], f"{a['anahtar']}: açıklama silme uyarısı içermeli"


def test_belgede_etkilemez_yalani_yok() -> None:
    """docs/AYARLAR.md temizlik ayarları için 'ETKİLEMEZ' dememeli (yanlış bilgi)."""
    belge = Path("docs/AYARLAR.md")
    assert belge.exists(), "docs/AYARLAR.md yok"
    icerik = belge.read_text(encoding="utf-8")
    assert "ETKİLEMEZ" not in icerik, "belge hâlâ yanlış 'ETKİLEMEZ' ifadesini içeriyor"
    assert "SİLER" in icerik, "belge gerçek silme davranışını yazmalı"


def test_katalog_semasi_tam_ve_gecerli() -> None:
    """Her kayıtta zorunlu alanlar dolu ve tipleri doğru olmalı."""
    zorunlu = (
        "anahtar",
        "etiket",
        "grup",
        "tip",
        "secenekler",
        "varsayilan",
        "min",
        "max",
        "env_adi",
        "risk",
        "kalici",
        "etkili",
    )
    gorulen: set[str] = set()
    for a in tumu():
        for alan in zorunlu:
            assert alan in a, f"{a.get('anahtar', '?')} alanı eksik: {alan}"
        assert a["grup"] in GRUPLAR, a["anahtar"]
        assert a["tip"] in TIPLER, a["anahtar"]
        assert a["risk"] in RISKLER, a["anahtar"]
        assert isinstance(a["etkili"], bool), a["anahtar"]
        assert isinstance(a["kalici"], bool), a["anahtar"]
        gorulen.add(str(a["anahtar"]))
        if a["tip"] == "secim":
            secenekler = a["secenekler"]
            assert isinstance(secenekler, list) and len(secenekler) >= 2, a["anahtar"]
            assert str(a["varsayilan"]) in [str(s) for s in secenekler], a["anahtar"]
        if a["tip"] == "sayi":
            mn, mx = a["min"], a["max"]
            assert mn is not None and mx is not None, a["anahtar"]
            assert int(mn) <= int(a["varsayilan"]) <= int(mx), a["anahtar"]
            oneriler = a["secenekler"]
            assert isinstance(oneriler, list) and oneriler, a["anahtar"]
            for o in oneriler:
                assert int(mn) <= int(o) <= int(mx), f"{a['anahtar']} öneri aralık dışı: {o}"
        if a["tip"] == "anahtar":
            assert a["secenekler"] is None, a["anahtar"]
    assert len(gorulen) == len(KATALOG), "katalogda tekrarlanan anahtar var"


def test_riskli_degistirilebilir_ayarlar_belli() -> None:
    """risk=yuksek olan değiştirilebilir ayarlar yalnızca force ve KOTA_DOLU_DAVRANIS'tır;
    ikisi de onay ekranı istisnasız kullanmalı."""
    riskli = [a["anahtar"] for a in tumu() if a["risk"] == "yuksek" and degistirilebilir_mi(a)]
    assert sorted(riskli) == ["KOTA_DOLU_DAVRANIS", "force"]


def test_sadece_goruntuleme_ayarlarina_degistirme_yolu_yok() -> None:
    """temizlik + sistem kayıtları için panel değiştirme düğmesi üretemez."""
    for a in tumu():
        if a["tip"] == "sadece_goruntule":
            assert not degistirilebilir_mi(a), a["anahtar"]


def test_cikarilan_ayarlar_katalogda_yok() -> None:
    """TETIK_DK / SESSIZ_SAAT / OTOMATIK_URETIM yalan ayar olarak eklenmedi
    (gerekçe modül docstring'inde)."""
    for k in ("TETIK_DK", "SESSIZ_SAAT", "OTOMATIK_URETIM"):
        assert ayar_getir(k) is None, f"{k} kataloğa alınmamalı"


def test_grup_ayarlari_sayilari_beklentiyle_uyumlu() -> None:
    """Panel ana ekranındaki sayaçlar: tetikleme 3, üretim&kota 5, sistem 6 secret.

    2026-11-11: üretim&kota 4 → 5 (KADANS_DK eklendi — "her 15 dakikada bir" kararı).
    """
    assert len(grup_ayarlari("tetikleme")) == 3
    assert len(grup_ayarlari("uretim_kota")) == 5
    assert len(grup_ayarlari("temizlik")) == 3
    sistem = grup_ayarlari("sistem")
    assert len(sistem) == 6
    assert all(a.get("secret") for a in sistem)


def test_olmayan_ayar_none_doner() -> None:
    assert ayar_getir("HICBIRSEY") is None
    assert "YUKLEME_ATLA" in anahtarlar()


def test_etkin_gunluk_maks_tavani_dayatir_ve_uyarir(capsys: pytest.CaptureFixture[str]) -> None:
    """TODO 10: env/state 24 bile derse etkin değer 6'dır + log uyarısı çıkar."""
    assert etkin_gunluk_maks(24) == 6
    assert etkin_gunluk_maks("96") == 6
    assert etkin_gunluk_maks(6) == 6
    assert etkin_gunluk_maks(3) == 3
    assert etkin_gunluk_maks("abc") == KOTA_TAVANI
    assert etkin_gunluk_maks(-7) == 0
    cikti = capsys.readouterr().out
    assert "kota tavanını aşıyor" in cikti, "kırpma sessiz olmamalı (log uyarısı şart)"
    assert "6" in cikti


def test_temizlik_uyari_metni_durstur_ve_h1_referansli() -> None:
    """Zorunlu açıklama metni: etkisizliği AÇIKÇA söyler ve H1'e atıf yapar."""
    assert "ETKİLEMEZ" in TEMIZLIK_UYARI
    assert "H1" in TEMIZLIK_UYARI
    assert "cleanup_low_views.yml" in TEMIZLIK_UYARI


def test_katalog_secret_deger_tasiimaz() -> None:
    """Savunma katmanı: kataloğun herhangi bir alanı 40+ karakterlik bir
    belirteç benzeri değer taşıyamaz (secret sızıntısı şeması)."""
    for a in tumu():
        for alan, deger in a.items():
            if isinstance(deger, str):
                assert len(deger) < 40 or " " in deger, f"{a['anahtar']}.{alan} belirteç benzeri"


def test_tumu_katalogu_eslesme_sirayla_dondurur() -> None:
    """tumu() katalog sırasını korur; panel ekranları bu sırayla düğme üretir."""
    assert [a["anahtar"] for a in tumu()] == [a["anahtar"] for a in KATALOG]
    assert tumu()[0]["grup"] == "tetikleme"
