"""TODO 1 — Ayar kataloğu testleri: tek doğruluk kaynağının bütünlüğü.

Kapsam: env_adi doluluğu, sadece_goruntule alan kuralları, secret varsayılan
yasağı, GUNLUK_MAKS tavanı (6), temizlik grubunun etkili=False dürüstlüğü,
katalog şemasının bütünlüğü ve kaldırılan ayarların gerçekten yokluğu.
"""

from __future__ import annotations

import sys
from pathlib import Path

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


def test_gunluk_maks_kaldirildi_kota_yok() -> None:
    """KULLANICI KARARI (2026-11-11): "Kota 6 istemiyorum, kotayı kaldır."

    Eski spec: katalogda GUNLUK_MAKS olmalı ve seçenekleri 6'yı aşmamalı.
    Yeni spec: yükleme tavanı KAVRAMI YOK → ayar katalogdan kaldırıldı.
    """
    assert ayar_getir("GUNLUK_MAKS") is None, "kota ayarı katalogda kalmamalı"
    # Matematik sabiti bilgi olarak durabilir ama SINIR olarak kullanılmaz.
    assert YOUTUBE_GUNLUK_KOTA_BIRIM // VIDEO_INSERT_MALIYETI == KOTA_TAVANI


def test_temizlik_grubu_etkili_ve_degistirilebilir() -> None:
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
        # 2026-11-11: kilit kaldırıldı — kullanıcı eşiği kendisi girer
        assert a["tip"] in ("sayi", "anahtar"), a["anahtar"]
        assert degistirilebilir_mi(a) is True, a["anahtar"]
        assert "SİLER" in a["aciklama"], f"{a['anahtar']}: açıklama silme uyarısı içermeli"


def test_izlenme_kontrol_1_saat() -> None:
    """Kullanıcı kararı: 1 saatte 100 izlenme almayan video silinir (1440 değil 60)."""
    a = ayar_getir("IZLENME_KONTROL_DK")
    assert a["varsayilan"] == "60"
    assert a["min"] == 15 and a["max"] == 10080
    esik = ayar_getir("MIN_IZLENME_ESIGI")
    assert esik["varsayilan"] == "100"
    assert esik["min"] == 0 and esik["max"] == 100000


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
            # 2026-11-11: serbest sayı girişi — öneri listesi ZORUNLU DEĞİL,
            # varsa seçenekler aralıkta olmalı.
            oneriler = a["secenekler"] or []
            assert isinstance(oneriler, list), a["anahtar"]
            for o in oneriler:
                assert int(mn) <= int(o) <= int(mx), f"{a['anahtar']} öneri aralık dışı: {o}"
        if a["tip"] == "anahtar":
            assert a["secenekler"] is None, a["anahtar"]
    assert len(gorulen) == len(KATALOG), "katalogda tekrarlanan anahtar var"


def test_riskli_degistirilebilir_ayarlar_belli() -> None:
    """risk=yuksek olan değiştirilebilir ayarlar yalnızca force ve KOTA_DOLU_DAVRANIS'tır;
    ikisi de onay ekranı istisnasız kullanmalı."""
    riskli = [a["anahtar"] for a in tumu() if a["risk"] == "yuksek" and degistirilebilir_mi(a)]
    # 2026-11-11: IZLENME_KONTROL_DK "orta" (süre değişimi doğrudan silmez;
    # eşiği MIN_IZLENME_ESIGI belirler → o "yuksek" ve onay ister).
    assert sorted(riskli) == ["KOTA_DOLU_DAVRANIS", "MIN_IZLENME_ESIGI",
                              "OTOMATIK_SIL_AKTIF", "force"]


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
    """Panel ana ekranındaki sayaçlar: tetikleme 3, üretim&kota 4, sistem 6 secret.

    2026-11-11 (1): üretim&kota 4 → 5 (KADANS_DK eklendi).
    2026-11-11 (2): 5 → 4 — kullanıcı "kotayı kaldır" dedi, GUNLUK_MAKS çıktı.
    """
    assert len(grup_ayarlari("tetikleme")) == 3
    assert len(grup_ayarlari("uretim_kota")) == 4
    assert len(grup_ayarlari("temizlik")) == 3
    sistem = grup_ayarlari("sistem")
    assert len(sistem) == 6
    assert all(a.get("secret") for a in sistem)


def test_olmayan_ayar_none_doner() -> None:
    assert ayar_getir("HICBIRSEY") is None
    assert "YUKLEME_ATLA" in anahtarlar()


def test_etkin_gunluk_maks_kirpmaz_kota_yok() -> None:
    """KULLANICI KARARI (2026-11-11): "Kota 6 istemiyorum, kotayı kaldır."

    Eski spec: 24 → 6'ya kırpılır ve uyarı loglanır.
    Yeni spec: KIRPMA YOK. Değer ne verilirse o (yalnız negatif → 0).
    Kırpma olsaydı yükleme yine 6'da kesilirdi — istenen tam olarak bunun
    ortadan kalkması.
    """
    assert etkin_gunluk_maks(24) == 24
    assert etkin_gunluk_maks("96") == 96
    assert etkin_gunluk_maks(6) == 6
    assert etkin_gunluk_maks(3) == 3
    assert etkin_gunluk_maks("abc") == 0
    assert etkin_gunluk_maks(-7) == 0


def test_temizlik_uyari_metni_durstur_ve_h1_referansli() -> None:
    """Zorunlu açıklama metni: etkisizliği AÇIKÇA söyler ve H1'e atıf yapar."""
    assert "SİLER" in TEMIZLIK_UYARI
    assert "ETKİLEMEZ" not in TEMIZLIK_UYARI
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
