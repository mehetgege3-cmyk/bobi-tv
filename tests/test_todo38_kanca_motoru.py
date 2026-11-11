"""A1 — Kanca (hook) sertleştirme testleri (2026-11-11).

Kullanıcı kararı: "A ile yapalım" = akışa girişi (%0) yukarı çekmek için
içerik/kanca güçlendirme. Bu dosya, kanca motorunun ÖLÇÜLEBİLİR sözlerini
kilitler:

  1. Uydurma sayı YOK (eski motor random.choice([3,5,7,10]) ile sayı ekliyordu).
  2. Clickbait kelime metne UYGULANARAK yumuşatılır (eskiden yalnız öneriliyordu).
  3. Kanca senaryoya GERÇEKTEN yazılır (eskiden `onerilen_varyant` hiç
     kullanılmıyordu — motorun çıktısı süstü).
  4. Kanca ≤ 12 kelime (ilk 1.5 saniye kuralı) ve puanı eşiğin üstünde.
  5. Form rotasyonu deterministik (rastgele değil) ve A/B grubu kaydedilir.
  6. Arşive `kanca_formu` yazılır — form bazlı performans ölçümü mümkün.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.senaryo_v7 import kanca_motoru as km  # noqa: E402

ORNEK = "Patron toplantıda herkesin maaşını açıkladı"


# ---------------------------------------------------------------------------
# 1) Form üretimi — uydurma yok
# ---------------------------------------------------------------------------


def test_sayi_formu_sayi_yoksa_uretilmez():
    """Eski motor metinde sayı yoksa RASTGELE sayı ekliyordu (uydurma veri).

    Yeni motor: sayı yoksa 'sayi' formu hiç üretilmez."""
    adaylar = km.aday_uret("Asansörde mahsur kaldık")
    assert "sayi" not in {a.form for a in adaylar}


def test_sayi_formu_metindeki_sayiyi_korur():
    adaylar = km.aday_uret("Asansörde 3 kişi mahsur kaldık")
    sayi = next(a for a in adaylar if a.form == "sayi")
    assert "3" in sayi.metin


def test_tum_formlar_12_kelimeyi_asmaz():
    uzun = "Patron toplantıda herkesin maaşını açıkladı ve sonra odadan çıktı"
    for aday in km.aday_uret(uzun):
        assert len(aday.metin.split()) <= km.MAKS_KELIME + 2, aday


# ---------------------------------------------------------------------------
# 2) Clickbait yumuşatma — UYGULANIR
# ---------------------------------------------------------------------------


def test_yasakli_kelime_yumusatilir():
    assert "şok" not in km.yumusat("ŞOK! Herkes dondu").lower()
    assert "inanılmaz" not in km.yumusat("İnanılmaz bir gün").lower()


def test_yumusatma_cumle_basini_buyuk_tutar():
    """"ŞOK! ..." → "Beklenmedik! ..." (eskiden "beklenmedik! ..." oluyordu)."""
    sonuc = km.yumusat("ŞOK! Herkes dondu")
    assert sonuc[0].isupper()
    assert sonuc.startswith("Beklenmedik")


def test_yasakli_kelime_puani_dusurur():
    temiz_puan, _ = km.puanla("Patron toplantıda maaşları açıkladı?")
    kirli_puan, gerekce = km.puanla("İnanılmaz patron şok etti")
    assert kirli_puan < temiz_puan
    assert "yasaklı" in gerekce


# ---------------------------------------------------------------------------
# 3) Senaryoya UYGULAMA — eski motorda eksikti
# ---------------------------------------------------------------------------


def test_paket_kancasini_uygula_senaryoyu_yazar():
    paket = {
        "senaryo": {
            "hook_ust_bant": ORNEK,
            "tts_metinleri": [ORNEK],
            "diyaloglar": [{"metin": ORNEK}, {"metin": "Ben de duydum"}],
        }
    }
    ozet = km.paket_kancasini_uygula(paket, video_no=0)
    senaryo = paket["senaryo"]
    assert ozet["uygulandi"] is True
    assert senaryo["hook_ust_bant"] == ozet["metin"]
    assert senaryo["tts_metinleri"][0] == ozet["metin"]
    assert senaryo["diyaloglar"][0]["metin"] == ozet["metin"]
    assert senaryo["kanca_formu"] == ozet["form"]
    assert senaryo["kanca_ab"] in {"A", "B", "C"}
    assert senaryo["kanca_puan"] >= km.KANCA_ESIGI


def test_paket_kancasi_tekrar_uygulaninca_metin_cogalmaz():
    """Kanca kendi üstüne uygulanırsa "...oldu? — ve bu gerçekten oldu?" gibi
    bozuk metin çıkıyordu → özgün kaynak `kanca_kaynak` alanında saklanır."""
    paket = {"senaryo": {"hook_ust_bant": ORNEK, "tts_metinleri": [ORNEK]}}
    ilk = km.paket_kancasini_uygula(paket, video_no=0)
    ikinci = km.paket_kancasini_uygula(paket, video_no=2)
    assert paket["senaryo"]["kanca_kaynak"] == ORNEK
    assert "oldu?" not in ikinci["metin"].replace("açıkladı?", "")
    assert ilk["metin"] != ikinci["metin"]  # form rotasyonu çalışıyor


def test_paket_kancasi_bos_senaryoda_cokmez():
    ozet = km.paket_kancasini_uygula({"senaryo": {}})
    assert ozet["uygulandi"] is False
    assert ozet["gerekce"]


def test_paket_kancasi_senaryo_sozluk_degilse_cokmez():
    ozet = km.paket_kancasini_uygula({"senaryo": "metin"})
    assert ozet["uygulandi"] is False


# ---------------------------------------------------------------------------
# 4) Rotasyon ve A/B
# ---------------------------------------------------------------------------


def test_form_rotasyonu_deterministik_ve_cesitli():
    ilk_dort = [km.siradaki_form(i) for i in range(4)]
    assert len(set(ilk_dort)) == 4  # 4 farklı form denenir
    assert ilk_dort == [km.siradaki_form(i) for i in range(4)]  # deterministik
    assert km.siradaki_form(None) == km.ROTASYON[0]


def test_tercih_edilen_form_secilebilir():
    adaylar = km.aday_uret(ORNEK)
    itiraflar = [a for a in adaylar if a.form == "itiraf"]
    assert itiraflar and itiraflar[0].gecerli


# ---------------------------------------------------------------------------
# 5) Arşiv kaydı — form bazlı ölçüm için
# ---------------------------------------------------------------------------


def test_arsiv_kaydina_kanca_alanlari_yazilir(tmp_path, monkeypatch):
    from modules import youtube_upload as yu

    arsiv = tmp_path / "videos.json"
    monkeypatch.setattr(yu, "ARSIV_YOLU", arsiv)
    yu.arsive_ekle(
        "v1", "Test başlık",
        {"kategori": "komedi", "kanca_formu": "soru", "kanca_ab": "A",
         "kanca_puan": 95, "hook_ust_bant": "Neden kimse gelmedi?"},
        "vid123",
    )
    kayit = json.loads(arsiv.read_text(encoding="utf-8"))[0]
    assert kayit["kanca_formu"] == "soru"
    assert kayit["kanca_ab"] == "A"
    assert kayit["kanca_puan"] == 95
    assert kayit["hook_ust_bant"] == "Neden kimse gelmedi?"


# ---------------------------------------------------------------------------
# 6) Form bazlı performans ölçümü (kanal sağlığı)
# ---------------------------------------------------------------------------


def test_kanca_formu_performansi_ortalama_verir(tmp_path, monkeypatch):
    from datetime import UTC, datetime, timedelta

    from modules import kanal_sagligi as ks

    simdi = datetime(2026, 11, 11, 12, tzinfo=UTC)
    kayitlar = [
        {"kanca_formu": "soru", "silinme_izlenme": 120,
         "tarih": (simdi - timedelta(days=1)).isoformat()},
        {"kanca_formu": "soru", "silinme_izlenme": 80,
         "tarih": (simdi - timedelta(days=2)).isoformat()},
        {"kanca_formu": "itiraf", "silinme_izlenme": 5,
         "tarih": (simdi - timedelta(days=1)).isoformat()},
        {"kanca_formu": "itiraf", "silinme_izlenme": 7,
         "tarih": (simdi - timedelta(days=2)).isoformat()},
    ]
    monkeypatch.setattr(ks, "_arsiv", lambda: kayitlar)
    sonuc = ks.kanca_formu_performansi(7, simdi)
    assert sonuc["form_verisi"]["soru"]["video"] == 2
    assert sonuc["form_verisi"]["soru"]["ortalama"] == 100.0
    assert sonuc["en_iyi_form"] == "soru"


def test_kanca_formu_performansi_tek_video_ile_kazanan_secmez(monkeypatch):
    """Tek video ile 'en iyi form' demek yanıltıcı → asgari 2 video aranır."""
    from datetime import UTC, datetime

    from modules import kanal_sagligi as ks

    simdi = datetime(2026, 11, 11, tzinfo=UTC)
    kayitlar = [{"kanca_formu": "iddia", "silinme_izlenme": 500,
                 "tarih": simdi.isoformat()}]
    monkeypatch.setattr(ks, "_arsiv", lambda: kayitlar)
    sonuc = ks.kanca_formu_performansi(7, simdi)
    assert sonuc["en_iyi_form"] == ""
    assert sonuc["form_verisi"]["iddia"]["video"] == 1


# ---------------------------------------------------------------------------
# 7) Ölçüm geçmişi — etki ancak geçmişle ölçülür
# ---------------------------------------------------------------------------


def test_kanal_sagligi_gecmisi_gunleri_biriktirir(tmp_path, monkeypatch):
    """Her gün tek kayıt: aynı gün iki kez koşarsa satır ÇOĞALMAZ, güncellenir."""
    from modules import kanal_sagligi as ks

    dosya = tmp_path / "gecmis.json"
    ozet1 = {"zaman": "2026-11-11T07:00:00+00:00", "uretilen": 3, "silinen": 1,
             "izlenme_ornek": 6, "ortalama_izlenme": 12.0, "akisa_girme_orani": 33,
             "kanca": {"en_iyi_form": "soru"}}
    ozet2 = {"zaman": "2026-11-11T19:00:00+00:00", "uretilen": 6, "silinen": 2,
             "izlenme_ornek": 9, "ortalama_izlenme": 20.0, "akisa_girme_orani": 44,
             "kanca": {"en_iyi_form": "itiraf"}}
    ks.ozeti_birlestir(ozet1, dosya)
    ks.ozeti_birlestir(ozet2, dosya)
    import json as _json

    veri = _json.loads(dosya.read_text(encoding="utf-8"))
    assert len(veri["gunler"]) == 1, "aynı gün → tek kayıt"
    assert veri["gunler"][0]["uretilen"] == 6, "gün içi son ölçüm kazanır"
    assert veri["gunler"][0]["kanca_en_iyi_form"] == "itiraf"
