"""TODO dosyası madde 5 — Arşiv ↔ kanal periyodik eşitleme testleri.

Kritik güvenlik kuralları ölçülür:
- kanaldan düşen kayıt SİLİNMEZ, `durum: kaldirildi` işaretlenir;
- kararsız sonuç (ağ hatası/gizli video) kaydı DEĞİŞTİRMEZ;
- aynı koşuda çok sayıda video yok görünürse (kanal askıya alınmış olabilir)
  eşitleme DURUR ve arşiv olduğu gibi kalır.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import modules.arsiv_esitleme as ae  # noqa: E402

SIMDI = datetime(2026, 11, 11, 9, 0, tzinfo=UTC)


@pytest.fixture()
def arsiv(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    yol = tmp_path / "videos.json"
    yol.write_text(
        json.dumps(
            [
                {"video_id": "AAA", "baslik": "bir", "durum": "yayinda"},
                {"video_id": "BBB", "baslik": "iki", "durum": "yayinda"},
                {"video_id": "CCC", "baslik": "üç", "durum": "kaldirildi"},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(ae, "ARSIV", yol)
    monkeypatch.setattr(ae, "DURUM_RAPORU", tmp_path / "esitleme.json")
    monkeypatch.setattr(ae, "HEPSI_ESIGI", 2)
    return yol


def test_yok_olan_kayit_silinmez_isaretlenir(arsiv: Path) -> None:
    sonuc = ae.esitle(
        simdi=SIMDI, kontrol=lambda v: ae.YOK if v == "AAA" else ae.VAR
    )
    kayitlar = json.loads(arsiv.read_text(encoding="utf-8"))
    assert [k["video_id"] for k in kayitlar] == ["AAA", "BBB", "CCC"], "kayıt silinmemeli"
    a = next(k for k in kayitlar if k["video_id"] == "AAA")
    assert a["durum"] == "kaldirildi"
    assert a["kaldirilma_kaynagi"] == "arsiv_esitleme"
    assert a["kaldirilma_tespit"].startswith("2026-11-11")
    assert sonuc.kaldirildi_isaretli == ["AAA"]
    assert sonuc.yazildi is True
    # Zaten kaldirildi olan kayıt yeniden kontrol edilmez.
    assert sonuc.zaten_isaretli == 1
    assert sonuc.kontrol_edilen == 2


def test_bilinmeyen_sonuc_kaydi_degistirmez(arsiv: Path) -> None:
    sonuc = ae.esitle(simdi=SIMDI, kontrol=lambda v: ae.BILINMIYOR)
    kayitlar = json.loads(arsiv.read_text(encoding="utf-8"))
    assert all(k["durum"] == "yayinda" or k["durum"] == "kaldirildi" for k in kayitlar)
    assert not sonuc.kaldirildi_isaretli
    assert sorted(sonuc.bilinmeyen) == ["AAA", "BBB"]
    assert sonuc.yazildi is False


def test_hepsi_yoksa_durur(arsiv: Path) -> None:
    """Kontrol edilen TÜM kayıtlar yoksa (kanal kapanmış olabilir) → arşiv DEĞİŞMEZ."""
    sonuc = ae.esitle(simdi=SIMDI, kontrol=lambda v: ae.YOK)
    assert sonuc.durduruldu
    assert sonuc.yazildi is False
    kayitlar = json.loads(arsiv.read_text(encoding="utf-8"))
    assert {k["video_id"] for k in kayitlar} == {"AAA", "BBB", "CCC"}
    assert sum(1 for k in kayitlar if k.get("durum") == "yayinda") == 2
    assert sorted(sonuc.bekleyen) == ["AAA", "BBB"]
    assert sonuc.kaldirildi_isaretli == [], "durdurulan koşuda işaretlenen listesi boş olmalı"


def test_az_sayida_kayip_normal_isaretlenir(arsiv: Path) -> None:
    """Tek tek kaldırılan videolar (oran düşükse) işaretlenir — koruma bloklamaz."""
    sonuc = ae.esitle(simdi=SIMDI, kontrol=lambda v: ae.YOK if v == "AAA" else ae.VAR)
    assert sonuc.durduruldu == ""
    assert sonuc.kaldirildi_isaretli == ["AAA"]


def test_dry_run_arsivi_yazmaz(arsiv: Path) -> None:
    sonuc = ae.esitle(
        simdi=SIMDI, kontrol=lambda v: ae.YOK if v == "BBB" else ae.VAR, yaz=False, kitle_esigi=9
    )
    assert sonuc.kaldirildi_isaretli == ["BBB"]
    assert sonuc.yazildi is False
    kayitlar = json.loads(arsiv.read_text(encoding="utf-8"))
    assert next(k for k in kayitlar if k["video_id"] == "BBB")["durum"] == "yayinda"


def test_oembed_404_yok_diger_her_sey_bilinmiyor(monkeypatch: pytest.MonkeyPatch) -> None:
    class R:
        def __init__(self, kod: int) -> None:
            self.status_code = kod

    monkeypatch.setattr("requests.get", lambda *a, **k: R(404))
    assert ae.oembed_kontrol("AAA") == ae.YOK
    monkeypatch.setattr("requests.get", lambda *a, **k: R(401))
    assert ae.oembed_kontrol("AAA") == ae.BILINMIYOR
    monkeypatch.setattr("requests.get", lambda *a, **k: R(200))
    assert ae.oembed_kontrol("AAA") == ae.VAR

    def patlat(*a, **k):
        raise OSError("ağ yok")

    monkeypatch.setattr("requests.get", patlat)
    assert ae.oembed_kontrol("AAA") == ae.BILINMIYOR


def test_iki_kontrol_ayrisirsa_yok_denmez(monkeypatch: pytest.MonkeyPatch) -> None:
    """oembed 404 + watch VAR (gizli/yaş kısıtlı video) → BILINMIYOR."""
    monkeypatch.setattr(ae, "oembed_kontrol", lambda v: ae.YOK)
    monkeypatch.setattr(ae, "izleme_sayfasi_kontrol", lambda v: ae.VAR)
    assert ae.video_var_mi("AAA") == ae.BILINMIYOR
    monkeypatch.setattr(ae, "izleme_sayfasi_kontrol", lambda v: ae.YOK)
    assert ae.video_var_mi("AAA") == ae.YOK
    monkeypatch.setattr(ae, "izleme_sayfasi_kontrol", lambda v: ae.BILINMIYOR)
    assert ae.video_var_mi("AAA") == ae.BILINMIYOR


def test_rapor_state_yazilir_ve_okunur(arsiv: Path) -> None:
    ae.esitle(simdi=SIMDI, kontrol=lambda v: ae.YOK if v == "AAA" else ae.VAR)
    rapor = ae.son_esitleme()
    assert rapor["kontrol_edilen"] == 2
    assert "AAA" in rapor["isaretlenen"]
    assert rapor["ozet"].startswith("🔎")
    assert rapor["zaman"] == SIMDI.isoformat()


def test_arşiv_yoksa_durur_veya_bos_doner(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(ae, "ARSIV", tmp_path / "yok.json")
    monkeypatch.setattr(ae, "DURUM_RAPORU", tmp_path / "r.json")
    sonuc = ae.esitle(simdi=SIMDI, kontrol=lambda v: ae.VAR)
    assert sonuc.durduruldu
    assert sonuc.kontrol_edilen == 0
