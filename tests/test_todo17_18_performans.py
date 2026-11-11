"""TODO 17 + 18 — Performans ekranı + izlenme snapshot'ı (Hakan/Kaan).

Kurallar: uydurma sayı yok; medyan 0 ise skor hesaplanmaz; saatlik veri
API'de olmadığı için kendi snapshot'ımızı üretiyoruz (+1h/+24h/+72h);
yeterli örnek yoksa "veri yetersiz".
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import modules.performans as pf  # noqa: E402


@pytest.fixture
def arsiv(monkeypatch, tmp_path):
    yol = tmp_path / "videos.json"
    monkeypatch.setattr(pf, "ARSIV", yol)
    return yol


def _kayit(vid: str, saat_once: float, izlenme: dict | None = None, saat: int = 12) -> dict:
    an = datetime(2026, 11, 10, saat, 0, tzinfo=timezone.utc) - timedelta(hours=saat_once)
    k = {"video_id": vid, "durum": "yayinda", "baslik": f"Video {vid}", "tarih": an.isoformat()}
    if izlenme:
        k["izlenme_snapshots"] = izlenme
    return k


SIMDI = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)


def test_snapshot_zamani_gelmeyen_alinmaz(arsiv):
    """Yüklemeden 30 dk sonra +1h snapshot'ı HENÜZ alınmaz.

    NOT: `simdi` AÇIKÇA verilir; gerçek saate bırakılırsa test tarihi
    geçmişte kaldığı için kayıt "eski" görünür ve test yanlış kırılır.
    """
    kayitlar = [_kayit("a", saat_once=0.5)]
    assert pf.snapshot_gerekenler(kayitlar, simdi=SIMDI) == []


def test_snapshot_1_saat_sonra_alinir(arsiv):
    kayitlar = [_kayit("a", saat_once=2)]
    assert [g["anahtar"] for g in pf.snapshot_gerekenler(kayitlar, simdi=SIMDI)] == ["+1h"]


def test_snapshot_72_saatte_ucu_de_alinir(arsiv):
    kayitlar = [_kayit("a", saat_once=80)]
    assert [g["anahtar"] for g in pf.snapshot_gerekenler(kayitlar, simdi=SIMDI)] == ["+1h", "+24h", "+72h"]


def test_alinmis_snapshot_tekrar_alinmaz(arsiv):
    kayitlar = [_kayit("a", saat_once=2, izlenme={"+1h": {"izlenme": 5}})]
    assert pf.snapshot_gerekenler(kayitlar, simdi=SIMDI) == []


def test_snapshot_guncelle_yazar(arsiv, monkeypatch):
    arsiv.write_text(json.dumps([_kayit("a", saat_once=2)]), encoding="utf-8")
    monkeypatch.setattr(pf, "izlenmeleri_oku", lambda idler: ({"a": 137}, ""))
    sonuc = pf.snapshotlari_guncelle()
    assert sonuc["yazilan"] == 1
    veri = json.loads(arsiv.read_text(encoding="utf-8"))
    assert veri[0]["izlenme_snapshots"]["+1h"]["izlenme"] == 137


def test_snapshot_youtube_hatasinda_cokmez(arsiv, monkeypatch):
    arsiv.write_text(json.dumps([_kayit("a", saat_once=2)]), encoding="utf-8")
    monkeypatch.setattr(pf, "izlenmeleri_oku", lambda idler: (None, "kota dolu"))
    sonuc = pf.snapshotlari_guncelle()
    assert sonuc["yazilan"] == 0 and "kota" in sonuc["sebep"]


def test_snapshot_tek_cagrida_okur(arsiv, monkeypatch):
    """Kota dostu: 60 video olsa da izlenmeler 2 çağrıda (50'lik gruplar) okunur."""
    kayitlar = [_kayit(f"v{i}", saat_once=2) for i in range(60)]
    arsiv.write_text(json.dumps(kayitlar), encoding="utf-8")
    cagri = []

    def sahte_oku(idler):
        cagri.append(len(idler))
        return ({i: 10 for i in idler}, "")

    monkeypatch.setattr(pf, "izlenmeleri_oku", sahte_oku)
    pf.snapshotlari_guncelle()
    assert cagri == [60], "snapshot için tek çağrı yapılmalı"


def test_performans_medyan_ve_skor(arsiv, monkeypatch):
    kayitlar = [_kayit(f"v{i}", saat_once=i + 1) for i in range(5)]
    arsiv.write_text(json.dumps(kayitlar), encoding="utf-8")
    monkeypatch.setattr(
        pf, "izlenmeleri_oku",
        lambda idler: ({"v0": 100, "v1": 100, "v2": 100, "v3": 100, "v4": 200}, ""),
    )
    sonuc = pf.performans_ozeti()
    assert sonuc["hata"] == ""
    assert sonuc["medyan"] == 100
    v0 = next(v for v in sonuc["videolar"] if v["video_id"] == "v4")
    assert v0["skor"] == 2.0


def test_medyan_sifirsa_skor_uydurulmaz(arsiv, monkeypatch):
    """Bölme yapılmaz: medyan 0 → skor None (uydurma çarpan yazılmaz)."""
    arsiv.write_text(json.dumps([_kayit("a", saat_once=2)]), encoding="utf-8")
    monkeypatch.setattr(pf, "izlenmeleri_oku", lambda idler: ({"a": 0}, ""))
    sonuc = pf.performans_ozeti()
    assert sonuc["medyan"] == 0
    assert sonuc["videolar"][0]["skor"] is None


def test_youtube_token_yoksa_hata_doner(arsiv, monkeypatch):
    arsiv.write_text(json.dumps([_kayit("a", saat_once=2)]), encoding="utf-8")
    monkeypatch.delenv("YOUTUBE_TOKEN", raising=False)
    sonuc = pf.performans_ozeti()
    assert sonuc["hata"], "token yokken hata sebebi dönmeli"


def test_saat_analizi_yeterli_ornek_yoksa_uyarir(arsiv):
    arsiv.write_text(json.dumps([_kayit("a", saat_once=2, izlenme={"+1h": {"izlenme": 5}})]), encoding="utf-8")
    sonuc = pf.saat_analizi()
    assert sonuc["yeterli"] is False
    assert "yetersiz" in sonuc["sebep"]


def test_saat_analizi_yeterli_veride_gruplar(arsiv):
    kayitlar = [
        _kayit(f"v{i}", saat_once=i + 1, izlenme={"+1h": {"izlenme": 100 + i}}, saat=9 + (i % 2) * 6)
        for i in range(6)
    ]
    arsiv.write_text(json.dumps(kayitlar), encoding="utf-8")
    sonuc = pf.saat_analizi()
    assert sonuc["yeterli"] is True
    assert len(sonuc["gruplar"]) >= 2


def test_en_iyi_en_kotu_siralama():
    videolar = [{"video_id": str(i), "izlenme": i * 10, "baslik": str(i)} for i in range(5)]
    iyi, kotu = pf.en_iyi_en_kotu(videolar, 3)
    assert iyi[0]["izlenme"] == 40
    assert kotu[0]["izlenme"] == 0
