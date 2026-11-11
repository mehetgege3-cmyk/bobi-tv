"""TODO dosyası madde 4 — Cron cadans gözlemi testleri.

Kural: cron ifadesi "10 dakikada bir" dese de panel ÖLÇÜLMÜŞ sayıyı gösterir;
veri yoksa "bilinmiyor" der.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import modules.cadans_olcum as co  # noqa: E402

SIMDI = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _izole(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(co, "RAPOR_YOLU", tmp_path / "cadans.json")


def test_duzenli_kosular_tam_oran_verir() -> None:
    # 24 saatte 10 dakikada bir → 144 koşu; ölçüm %100 olmalı.
    zamanlar = [SIMDI - timedelta(minutes=10 * i) for i in range(144)]
    r = co.cadans_olc("hourly_production.yml", 10, SIMDI, zamanlar)
    assert r["durum"] == "olculdu"
    assert r["medyan_aralik_dk"] == 10
    assert r["son_24saat_kosu"] == 144
    assert r["oran"] == 1.0


def test_seyrek_kosular_dusuk_oran_verir() -> None:
    # Gerçek gözlem: günde 2 koşu, aralarında 168 dk.
    zamanlar = [SIMDI - timedelta(hours=2), SIMDI - timedelta(hours=2, minutes=168)]
    r = co.cadans_olc("hourly_production.yml", 10, SIMDI, zamanlar)
    assert r["son_24saat_kosu"] == 2  # 2 sa + 4.8 sa önce → ikisi de 24 sa içinde
    assert r["medyan_aralik_dk"] == 168
    assert r["oran"] < 0.05
    assert r["en_uzun_aralik_dk"] == 168


def test_okunamayan_gecmis_bilinmiyor_der(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(co, "kosulari_oku", lambda *a, **k: None)
    r = co.cadans_olc("hourly_production.yml", 10, SIMDI)
    assert r["durum"] == co.BILINMIYOR
    assert "sebep" in r
    assert co.panel_satiri().startswith("📉 Cadans: bilinmiyor")


def test_bos_gecmis_bilinmiyor_der() -> None:
    r = co.cadans_olc("hourly_production.yml", 10, SIMDI, [])
    assert r["durum"] == co.BILINMIYOR


def test_beklenen_aralik_kadanstan_gelir() -> None:
    """Beklenen aralık SABİT 10 dk değil, modules/kadans.py'den okunur."""
    from modules.kadans import KADANS_DK

    assert co._beklenen_dk() == KADANS_DK


def test_eski_olcum_yaniltici_oran_gostermez(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Kadans değiştiyse panel eski oranı değil 'ölçüm eski' der."""
    (tmp_path / "cadans.json").write_text(
        json.dumps(
            {
                "olcumler": {
                    "hourly_production.yml": {
                        "durum": "olculdu",
                        "beklenen_dk": 10,  # eski kadans
                        "oran": 0.3,
                        "son_24saat_kosu": 43,
                        "medyan_aralik_dk": 15,
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    satir = co.panel_satiri()
    assert "ölçüm eski" in satir
    assert "%30" not in satir, "eski kadansın oranı gösterilmemeli"


def test_tumunu_olc_state_yazar(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        co,
        "cadans_olc",
        lambda w, d, s: {"workflow": w, "durum": "olculdu", "beklenen_dk": d,
                         "oran": 0.8, "son_24saat_kosu": 115,
                         "medyan_aralik_dk": 12.5, "son5_medyan_dk": d},
    )
    rapor = co.tumunu_olc(SIMDI)
    # İzlenen küme: sabitler + kadans kaynağından gelen üretim workflow'u.
    assert set(rapor["olcumler"]) == set(co.IZLENEN)
    assert rapor["olcumler"]["hourly_production.yml"]["beklenen_dk"] == co._beklenen_dk()
    veri = json.loads((tmp_path / "cadans.json").read_text(encoding="utf-8"))
    assert veri["zaman"] == SIMDI.isoformat()
    satir = co.panel_satiri()
    assert "Cadans" in satir and "✅ hedefte" in satir


def test_panel_satiri_hedefe_oturmayi_anlatir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Panel, "oran %" yerine SON aralıkların hedefe oturup oturmadığını söyler."""
    hedef = co._beklenen_dk()
    for son_medyan, isaret in (
        (hedef, "✅ hedefte"),
        (hedef * 0.5, "⚠️ hedeften sık"),
        (hedef * 0.05, "⏳ geçiş"),
    ):
        (tmp_path / "cadans.json").write_text(
            json.dumps(
                {
                    "olcumler": {
                        "hourly_production.yml": {
                            "durum": "olculdu",
                            "beklenen_dk": hedef,
                            "oran": 1.0,
                            "son_24saat_kosu": 5,
                            "medyan_aralik_dk": hedef,
                            "son5_medyan_dk": son_medyan,
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        assert isaret in co.panel_satiri(), f"{son_medyan} için {isaret} beklenirdi"


def test_gecis_donemi_eski_rejimi_guncel_sanmaz() -> None:
    """15 dk → 480 dk geçişinde son aralıklar güncel kadanstan gelir."""
    # Son 5 aralık 480 dk (yeni rejim), daha eskiler 15 dk (eski rejim).
    zamanlar = [SIMDI - timedelta(minutes=480 * i) for i in range(1, 7)]
    zamanlar += [zamanlar[-1] - timedelta(minutes=15 * i) for i in range(1, 20)]
    r = co.cadans_olc("hourly_production.yml", 480, SIMDI, zamanlar)
    assert r["son5_medyan_dk"] == 480
    assert r["medyan_aralik_dk"] == 15, "tüm geçmiş eski rejimi gösterir"
