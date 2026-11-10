"""TODO 1 — Üretim tetikleyicisi testleri.

Kapsam: hourly_production.yml iki dış tetikleyici tanımalı, cron saatliğe
dönmeli, "son koşu süresi" adımı mevcut olmalı ve tetikleyici dokümanı token
değeri İÇERMEMELİ.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

REPO_KOK = Path(__file__).resolve().parent.parent
WORKFLOW = REPO_KOK / ".github" / "workflows" / "hourly_production.yml"
DOCS = REPO_KOK / "docs" / "TETIKLEYICI_KURULUM.md"
DISPATCH_TIPI = "bobi-tv-produce"


def _workflow_yukle() -> dict[str, Any]:
    veri: object = yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    assert isinstance(veri, dict), "hourly_production.yml sözlük olmalı"
    return veri


def test_hourly_hem_workflow_hem_repository_dispatch_tanimli() -> None:
    tetikler = _workflow_yukle()["on"]
    assert "workflow_dispatch" in tetikler, "workflow_dispatch tetikleyicisi eksik"
    assert "repository_dispatch" in tetikler, "repository_dispatch tetikleyicisi eksik"
    tipler = tetikler["repository_dispatch"]["types"]
    assert DISPATCH_TIPI in tipler


def test_hourly_cron_saatlik_yedek() -> None:
    """10 dk cron yanılsaması kaldırılır: yedek cron saat başıdır."""
    program = _workflow_yukle()["on"]["schedule"]
    crons = [str(kayit["cron"]) for kayit in program]
    assert crons == ["0 * * * *"], f"Beklenen tek saatlik cron, gelen: {crons}"


def test_hourly_son_kosu_suresi_adimi_var() -> None:
    adimlar = _workflow_yukle()["jobs"]["uret-ve-yayinla"]["steps"]
    isimler = [str(adim.get("name", "")) for adim in adimlar]
    assert any("Son koşudan" in isim for isim in isimler), (
        "Gözlemlenebilirlik adımı eksik: 'Son koşudan bu yana geçen süreyi logla'"
    )


def test_force_kosullari_tetik_ciktilarini_kullanir() -> None:
    """github.event.inputs.force doğrudan repository_dispatch'ta çalışmaz;
    koşullar steps.tetik.outputs.force üzerinden okumalı."""
    yazi = WORKFLOW.read_text(encoding="utf-8")
    adimlar = _workflow_yukle()["jobs"]["uret-ve-yayinla"]["steps"]
    if_kosullari = [str(adim.get("if", "")) for adim in adimlar]
    ilgili = [k for k in if_kosullari if "force" in k]
    assert ilgili, "force kullanan koşul yok"
    for kosul in ilgili:
        assert "github.event.inputs.force" not in kosul, kosul
        assert "steps.tetik.outputs.force" in kosul, kosul
    # id: tetik adımı gerçekten tanımlı olmalı
    assert any(str(adim.get("id", "")) == "tetik" for adim in adimlar)
    assert "repository_dispatch" in yazi


def test_tetikleyici_docs_var_ve_token_degeri_icermez() -> None:
    assert DOCS.exists(), "docs/TETIKLEYICI_KURULUM.md eksik"
    metin = DOCS.read_text(encoding="utf-8")
    assert "dispatches" in metin
    assert "Actions: write" in metin, "Gerekli token yetkisi (Actions: write) belgelenmeli"
    assert "secret" in metin.lower()
    # Gerçek token kalıbı asla dokümante edilmez
    assert not re.search(r"gh[pousr]_[A-Za-z0-9]{20,}", metin), "Belgede gerçek token kalıbı var!"
    assert not re.search(r"github_pat_[A-Za-z0-9_]{20,}", metin), "Belgede gerçek token kalıbı var!"
    assert "mehetgege3-cmyk/bobi-tv" in metin, "Doğru repo uç noktası belgelenmeli"
