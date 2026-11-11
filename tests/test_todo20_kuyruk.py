"""TODO 20 — Stok (kuyruk) yönetimi: görüntüle, sebebe göre ayır, onaylı at, geri al.

Kurallar test edilir: uydurma sayı yok, videos.json'a yazılmaz, silme yerine
taşıma, path traversal reddedilir, bozuk kayıt sessizce yok edilmez.
"""
from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import modules.kuyruk_yonetimi as ky  # noqa: E402

SIMDI = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _ortam(monkeypatch, tmp_path):
    """Kuyruk ve çöp dizinlerini tmp'ye al — gerçek stok dosyalarına dokunulmaz."""
    monkeypatch.setattr(ky, "KUYRUK_DIZINI", tmp_path / "queue")
    monkeypatch.setattr(ky, "ATILAN_DIZINI", tmp_path / "arsiv" / "atilan")
    (tmp_path / "queue").mkdir()
    return tmp_path


def _kayit_ekle(dizin: Path, adi: str, **alanlar) -> Path:
    veri = {
        "dosya_adi": adi,
        "baslik": alanlar.pop("baslik", f"Başlık {adi}"),
        "stok_sebep": alanlar.pop("stok_sebep", "kota"),
        "deneme": alanlar.pop("deneme", 0),
        "olusturuldu": alanlar.pop("olusturuldu", (SIMDI - timedelta(hours=2)).isoformat()),
        "final_video": alanlar.pop("final_video", ""),
    }
    veri.update(alanlar)
    yol = dizin / f"{adi}.json"
    yol.write_text(json.dumps(veri, ensure_ascii=False), encoding="utf-8")
    return yol


# --- Okuma / özet ---------------------------------------------------------


def test_bos_kuyruk_sifir_dondurur_ve_cokmez():
    o = ky.ozet(SIMDI)
    assert o["toplam"] == 0
    assert o["bozuk"] == 0
    assert "Stok boş" in ky.panel_metni(SIMDI)


def test_dizin_yoksa_da_cokmez(monkeypatch, tmp_path):
    monkeypatch.setattr(ky, "KUYRUK_DIZINI", tmp_path / "yok")
    o = ky.ozet(SIMDI)
    assert o["toplam"] == 0
    assert ky.kayitlari_oku(SIMDI)["dizin_var"] is False


def test_sebebe_gore_dagilim():
    d = ky.KUYRUK_DIZINI
    _kayit_ekle(d, "a", stok_sebep="kota")
    _kayit_ekle(d, "b", stok_sebep="kota")
    _kayit_ekle(d, "c", stok_sebep="gecici")
    o = ky.ozet(SIMDI)
    assert o["toplam"] == 3
    assert o["sebep_dagilimi"]["kota"] == 2
    assert o["sebep_dagilimi"]["gecici"] == 1


def test_bilinmeyen_sebep_uydurulmaz():
    _kayit_ekle(ky.KUYRUK_DIZINI, "x", stok_sebep="uzayli_saldirisi")
    o = ky.ozet(SIMDI)
    assert o["sebep_dagilimi"] == {"bilinmiyor": 1}
    assert "bilinmiyor" in ky.panel_metni(SIMDI)


def test_bozuk_json_silinmez_ve_raporlanir():
    (ky.KUYRUK_DIZINI / "bozuk.json").write_text("{bu json degil", encoding="utf-8")
    o = ky.ozet(SIMDI)
    assert o["bozuk"] == 1
    assert (ky.KUYRUK_DIZINI / "bozuk.json").exists(), "bozuk kayıt sessizce yok edilmemeli"
    assert "Bozuk kayıt" in ky.panel_metni(SIMDI)


def test_yas_ve_deneme_hesaplanir():
    _kayit_ekle(ky.KUYRUK_DIZINI, "y", deneme=3, olusturuldu=(SIMDI - timedelta(days=9)).isoformat())
    k = ky.ozet(SIMDI)["kayitlar"][0]
    assert k["yas_gun"] == 9
    assert k["deneme"] == 3
    assert ky.ozet(SIMDI)["bayat"] == 1


def test_okunamayan_tarih_bilinmiyor_kalir():
    _kayit_ekle(ky.KUYRUK_DIZINI, "z", olusturuldu="dün akşam")
    k = ky.ozet(SIMDI)["kayitlar"][0]
    assert k["yas_gun"] is None
    assert "bilinmiyor" in ky.panel_metni(SIMDI)


def test_mp4_diskte_yoksa_uyari_cikar(tmp_path):
    _kayit_ekle(ky.KUYRUK_DIZINI, "m", final_video=str(tmp_path / "yok.mp4"))
    o = ky.ozet(SIMDI)
    assert o["video_yok"] == 1
    assert "MP4" in ky.panel_metni(SIMDI)


def test_mp4_varsa_uyari_yok(tmp_path):
    mp4 = tmp_path / "var.mp4"
    mp4.write_bytes(b"x")
    _kayit_ekle(ky.KUYRUK_DIZINI, "m2", final_video=str(mp4))
    o = ky.ozet(SIMDI)
    assert o["video_yok"] == 0


# --- Plan / atma ---------------------------------------------------------


def test_plan_hicbir_sey_silmez():
    _kayit_ekle(ky.KUYRUK_DIZINI, "p1")
    _kayit_ekle(ky.KUYRUK_DIZINI, "p2")
    plan = ky.atma_plani(None, SIMDI)
    assert plan["adet"] == 2
    assert len(list(ky.KUYRUK_DIZINI.glob("*.json"))) == 2, "plan yalnız OKUMALI"


def test_bos_liste_hepsini_atmaz():
    """Yanlışlıkla 'hepsini at' tetiklenmesin: boş liste = hiçbir şey."""
    _kayit_ekle(ky.KUYRUK_DIZINI, "b1")
    assert ky.atma_plani([], SIMDI)["adet"] == 0


def test_atma_silmek_degil_tasimak(tmp_path):
    _kayit_ekle(ky.KUYRUK_DIZINI, "t1")
    sonuc = ky.toplu_at(None, SIMDI)
    assert sonuc["atilan"] == 1
    assert not list(ky.KUYRUK_DIZINI.glob("*.json"))
    atilan = list(ky.ATILAN_DIZINI.glob("*.json"))
    assert len(atilan) == 1, "kayıt çöp kutusuna taşınmalı (geri alınabilir)"


def test_geri_al_kuyruga_dondurur():
    _kayit_ekle(ky.KUYRUK_DIZINI, "g1")
    ky.toplu_at(None, SIMDI)
    sonuc = ky.geri_al()
    assert sonuc["geri_alinan"] == 1
    assert (ky.KUYRUK_DIZINI / "g1.json").exists()
    assert ky.ozet(SIMDI)["toplam"] == 1


def test_geri_al_bos_copte_sifir_doner():
    assert ky.geri_al()["geri_alinan"] == 0


def test_tek_kayit_atma_secimli():
    _kayit_ekle(ky.KUYRUK_DIZINI, "s1")
    _kayit_ekle(ky.KUYRUK_DIZINI, "s2")
    sonuc = ky.toplu_at(["s1"], SIMDI)
    assert sonuc["atilan"] == 1
    kalan = [k["dosya_adi"] for k in ky.ozet(SIMDI)["kayitlar"]]
    assert kalan == ["s2"]


def test_path_traversal_reddedilir(tmp_path):
    """Kuyruk dışına işaret eden kayıt TAŞINMAZ (dosya sistemi korunur)."""
    disarida = tmp_path / "disarida.json"
    disarida.write_text("{}", encoding="utf-8")
    assert ky.at({"dosya_yolu": disarida}, SIMDI) is False
    assert disarida.exists(), "kuyruk dışı dosya silinmemeli"


def test_toplu_at_en_fazla_limitte_dokunur(monkeypatch):
    monkeypatch.setattr(ky, "TOPLU_AZAMI", 2)
    for i in range(4):
        _kayit_ekle(ky.KUYRUK_DIZINI, f"l{i}")
    sonuc = ky.toplu_at(None, SIMDI)
    assert sonuc["atilan"] == 2
    assert ky.ozet(SIMDI)["toplam"] == 2


# --- Panel metinleri -----------------------------------------------------


def test_onay_metni_geri_alinabilir_oldugunu_soyler():
    _kayit_ekle(ky.KUYRUK_DIZINI, "o1")
    metin = ky.onay_metni(None, SIMDI)
    assert "ONAY GEREKİYOR" in metin
    assert "SİLİNMEZ" in metin
    assert "Geri al" in metin


def test_onay_metni_bos_kuyrukta_durust():
    assert "Atılacak kayıt yok" in ky.onay_metni(None, SIMDI)


def test_panel_15_satiri_gecmez():
    for i in range(20):
        _kayit_ekle(ky.KUYRUK_DIZINI, f"c{i}", olusturuldu=(SIMDI - timedelta(days=i)).isoformat())
    metin = ky.panel_metni(SIMDI)
    assert len([s for s in metin.split("\n") if s.strip()]) <= 15


def test_videos_json_a_yazilmaz(tmp_path, monkeypatch):
    """Kuyruk işlemleri videos.json'a hiçbir şey yazmamalı."""
    arsiv = tmp_path / "videos.json"
    arsiv.write_text("[]", encoding="utf-8")
    _kayit_ekle(ky.KUYRUK_DIZINI, "v1")
    ky.toplu_at(None, SIMDI)
    ky.geri_al()
    assert arsiv.read_text(encoding="utf-8") == "[]"


def test_yas_esigi_sorgusu():
    _kayit_ekle(ky.KUYRUK_DIZINI, "e1", olusturuldu=(SIMDI - timedelta(days=8)).isoformat())
    _kayit_ekle(ky.KUYRUK_DIZINI, "e2", olusturuldu=(SIMDI - timedelta(days=1)).isoformat())
    assert ky.yas_esigi_asildi("e1", 7, SIMDI) is True
    assert ky.yas_esigi_asildi("e2", 7, SIMDI) is False
    assert ky.yas_esigi_asildi("yok", 7, SIMDI) is False
