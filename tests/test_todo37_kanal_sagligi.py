"""Kanal sağlığı ölçümü testleri (2026-11-11 kadans/silme değişikliği sonrası).

Kural: ölçüm UYDURMAZ. Veri yoksa "bilinmiyor"/"veri yetersiz" der; az örnekle
"iyileşti" demez; akışa giriş oranı yalnız gerçek izlenme kayıtlarından gelir.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import modules.kanal_sagligi as ks  # noqa: E402

SIMDI = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)


@pytest.fixture()
def ortam(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    arsiv = tmp_path / "videos.json"
    monkeypatch.setattr(ks, "ARSIV", arsiv)
    monkeypatch.setattr(ks, "RAPOR", tmp_path / "kanal_sagligi.json")
    kalite = tmp_path / "quality"
    kalite.mkdir()
    monkeypatch.setattr(ks, "KALITE_DIZINI", kalite)
    return tmp_path


def _yaz(arsiv: Path, kayitlar: list[dict]) -> None:
    arsiv.write_text(json.dumps(kayitlar, ensure_ascii=False), encoding="utf-8")


def _gun_once(gun: int) -> str:
    return (SIMDI - timedelta(days=gun)).isoformat()


def test_veri_yoksa_yorum_yapmaz(ortam: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ks, "ARSIV", ortam / "yok.json")
    ozet = ks.saglik_ozeti(7, SIMDI)
    assert ozet["uretilen"] == 0
    assert ozet["kalite_ortalama"] is None
    assert "veri yetersiz" in ozet["yorum"]
    assert ks.panel_satiri().startswith("🩺 Kanal: ölçüm yok") or "veri yetersiz" in ks.panel_satiri()


def test_az_ornekle_iyilesme_iddiasi_yok(ortam: Path) -> None:
    _yaz(
        ortam / "videos.json",
        [
            {"video_id": "a", "tarih": _gun_once(1), "durum": "yayinda", "izlenme": 250},
            {"video_id": "b", "tarih": _gun_once(1), "durum": "yayinda", "izlenme": 400},
        ],
    )
    ozet = ks.saglik_ozeti(7, SIMDI)
    assert ozet["izlenme_ornek"] == 2
    assert "veri yetersiz" in ozet["yorum"], "2 örnekle yorum yapılmamalı"


def test_akis_orani_gercek_kayitlardan(ortam: Path) -> None:
    kayitlar = [{"video_id": f"v{i}", "tarih": _gun_once(1), "durum": "yayinda"} for i in range(6)]
    for i, izlenme in enumerate([120, 300, 150, 5, 0, 2]):
        kayitlar[i]["izlenme"] = izlenme
    _yaz(ortam / "videos.json", kayitlar)
    ozet = ks.saglik_ozeti(7, SIMDI)
    assert ozet["akisa_giren"] == 3
    assert ozet["akisa_girme_orani"] == 50
    assert ozet["en_yuksek_izlenme"] == 300
    assert ozet["yorum"].startswith("🟢")


def test_silinme_kaydi_izlenme_olarak_sayilir(ortam: Path) -> None:
    """Silinen videonun son izlenmesi de sinyal (arşivde silinme_izlenme)."""
    _yaz(
        ortam / "videos.json",
        [
            {
                "video_id": "x",
                "tarih": _gun_once(2),
                "durum": "silindi_dusuk_izlenme",
                "silinme_izlenme": 3,
            }
        ],
    )
    ozet = ks.saglik_ozeti(7, SIMDI)
    assert ozet["silinen"] == 1
    assert ozet["ortalama_izlenme"] == 3


def test_kalite_puanlari_jsonl_okunur(ortam: Path) -> None:
    gun = SIMDI.strftime("%Y-%m-%d")
    (ortam / "quality" / f"{gun}.jsonl").write_text(
        "\n".join(
            json.dumps({"toplam_puan": p, "gecti": p >= 70}) for p in (72, 81, 65)
        ),
        encoding="utf-8",
    )
    puanlar = ks.kalite_puanlari(7, SIMDI)
    assert puanlar == [72.0, 81.0, 65.0]
    _yaz(ortam / "videos.json", [{"video_id": "a", "tarih": _gun_once(1), "izlenme": 1}])
    ozet = ks.saglik_ozeti(7, SIMDI)
    assert ozet["kalite_ornek"] == 3
    assert ozet["kalite_ortalama"] == 72.7


def test_snapshot_izlenmesi_kullanilir(ortam: Path) -> None:
    _yaz(
        ortam / "videos.json",
        [
            {
                "video_id": "s",
                "tarih": _gun_once(1),
                "durum": "yayinda",
                "izlenme_snapshots": {"1": 7, "24": 140},
            }
        ],
    )
    ozet = ks.saglik_ozeti(7, SIMDI)
    assert ozet["en_yuksek_izlenme"] == 140, "en yeni snapshot kullanılmalı"


def test_sadece_son_gunler_sayilir(ortam: Path) -> None:
    _yaz(
        ortam / "videos.json",
        [
            {"video_id": "eski", "tarih": _gun_once(30), "izlenme": 900},
            {"video_id": "yeni", "tarih": _gun_once(1), "izlenme": 4},
        ],
    )
    ozet = ks.saglik_ozeti(7, SIMDI)
    assert ozet["uretilen"] == 1
    assert ozet["en_yuksek_izlenme"] == 4


def test_rapor_yaz_ve_panel_satiri(ortam: Path) -> None:
    _yaz(ortam / "videos.json", [{"video_id": "a", "tarih": _gun_once(1), "izlenme": 200}])
    ks.rapor_yaz(SIMDI, 7)
    satir = ks.panel_satiri()
    assert "🩺 Kanal" in satir and "ort. 200 izlenme" in satir
    assert json.loads((ortam / "kanal_sagligi.json").read_text(encoding="utf-8"))[
        "akisa_girme_orani"
    ] == 100
