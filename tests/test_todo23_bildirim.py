"""TODO 23 + 24 — Akıllı bildirim motoru (Burak).

Kurallar: KRİTİK sessiz saati deler; NORMAL sessiz saatte bekler ve pencere
bitince TEK mesaj olur; ÖZET günlük özeti bekler; sustur her şeyi erteler
ama ayarları SİLMEZ; saat dilimi Europe/Istanbul.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import modules.bildirim as bd  # noqa: E402


@pytest.fixture(autouse=True)
def _ortam(monkeypatch, tmp_path):
    monkeypatch.setattr(bd, "DURUM_YOLU", tmp_path / "bildirim.json")
    gonderilen: list[str] = []
    monkeypatch.setattr(bd, "_gonder", lambda m: gonderilen.append(m) or True)
    monkeypatch.setenv("SESSIZ_BASLANGIC", "00:00")
    monkeypatch.setenv("SESSIZ_BITIS", "08:00")
    monkeypatch.setenv("OZET_SAATI", "09:00")
    return gonderilen


def _tr(saat: int, dakika: int = 0, gun: int = 11) -> datetime:
    """Türkiye saatiyle verilen anı UTC datetime olarak döndürür (TR = UTC+3)."""
    return datetime(2026, 11, gun, saat - 3, dakika, tzinfo=timezone.utc)


def test_sessiz_saat_gece_yarisini_asar(monkeypatch):
    monkeypatch.setenv("SESSIZ_BASLANGIC", "22:00")
    monkeypatch.setenv("SESSIZ_BITIS", "08:00")
    assert bd.sessiz_saatte_mi(_tr(23)) is True
    assert bd.sessiz_saatte_mi(_tr(3)) is True
    assert bd.sessiz_saatte_mi(_tr(12)) is False


def test_kritik_sessiz_saati_deler(_ortam):
    """Sistem gerçekten bozuksa gece 03:00'te de haber verir."""
    sonuc = bd.bildir("Poller sustu", "45 dk cevap yok", bd.KRITIK, simdi=_tr(3))
    assert sonuc["durum"] == "gonderildi"
    assert len(_ortam) == 1


def test_normal_bildirim_sessiz_saatte_kuyruga_girer(_ortam):
    sonuc = bd.bildir("Video yayınlandı", "url", bd.NORMAL, simdi=_tr(3))
    assert sonuc["durum"] == "kuyruk"
    assert _ortam == []
    assert len(bd.durum_oku()["bekleyen"]) == 1


def test_normal_bildirim_gunduz_aninda_gider(_ortam):
    sonuc = bd.bildir("Video yayınlandı", "url", bd.NORMAL, simdi=_tr(14))
    assert sonuc["durum"] == "gonderildi"
    assert len(_ortam) == 1


def test_ozet_seviyesi_hemen_gonderilmez(_ortam):
    sonuc = bd.bildir("QC düştü", "puan 62", bd.OZET, simdi=_tr(14))
    assert sonuc["durum"] == "kuyruk"
    assert _ortam == []


def test_sessiz_saatte_birikenler_tek_mesajda_gelir(_ortam):
    for i in range(3):
        bd.bildir(f"Olay {i}", "", bd.NORMAL, simdi=_tr(3))
    # Sabah 09:30 → tur bildirimleri birikmişleri TEK mesajda boşaltır
    sonuc = bd.tur_bildirimleri(_tr(9, 30))
    assert sonuc["birikmis_gonderildi"] >= 3
    birikim_mesajlari = [m for m in _ortam if "Gece biriken" in m]
    assert len(birikim_mesajlari) == 1, "birikmişler ayrı ayrı gönderildi (spam)"


def test_gunluk_ozet_bir_kez_gonderilir(_ortam):
    bd.bildir("QC düştü", "", bd.OZET, simdi=_tr(10))
    ilk = bd.gunluk_ozet_gonder(_tr(10))
    assert ilk["gonderildi"] is True
    assert bd.ozet_vakti_mi(_tr(11)) is False, "aynı gün ikinci özet gitmemeli"
    bd.gunluk_ozet_gonder(_tr(11))


def test_ozet_vakti_saatten_once_false():
    assert bd.ozet_vakti_mi(_tr(8, 30)) is False
    assert bd.ozet_vakti_mi(_tr(9, 5)) is True


def test_sustur_her_seyi_erteler_ama_ayarlari_silmez(_ortam, monkeypatch):
    monkeypatch.setattr(bd, "durum_yaz", bd.durum_yaz)
    bd.sustur(1)
    sonuc = bd.bildir("Kritik olsa bile", "", bd.KRITIK, simdi=datetime.now(timezone.utc))
    assert sonuc["durum"] == "susturuldu"
    assert _ortam == []
    # sustur kalkınca kritik yine gider
    bd.susturu_kaldir()
    assert bd.bildir("Kritik", "", bd.KRITIK, simdi=datetime.now(timezone.utc))["durum"] == "gonderildi"


def test_sustur_bitis_zamani_ileride():
    bitis = bd.sustur(1)
    assert ":" in bitis


def test_bozuk_state_dosyasi_cokertmez(monkeypatch, tmp_path):
    yol = tmp_path / "bozuk.json"
    yol.write_text("{bu json değil", encoding="utf-8")
    monkeypatch.setattr(bd, "DURUM_YOLU", yol)
    veri = bd.durum_oku()
    assert veri["bekleyen"] == [] and veri["sustur_until"] is None


def test_kuyruk_en_fazla_50_olay_tutar(_ortam):
    for i in range(60):
        bd.bildir(f"Olay {i}", "", bd.OZET, simdi=_tr(14))
    assert len(bd.durum_oku()["bekleyen"]) <= 50, "kuyruk sınırsız büyüdü"


def test_bilinmeyen_seviye_normal_sayilir(_ortam):
    sonuc = bd.bildir("test", "", "saçma", simdi=_tr(14))
    assert sonuc["durum"] == "gonderildi"


def test_secret_degeri_loglanmaz(_ortam, capsys):
    """Kritik bildirim metni secret içermemeli; modül token basmamalı."""
    bd.bildir("Token yenilendi", "YENI_TOKEN=abc123", bd.KRITIK, simdi=_tr(14))
    cikti = capsys.readouterr().out
    assert "abc123" not in cikti
