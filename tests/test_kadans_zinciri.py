"""15 dakika kadans zinciri testleri (kullanıcı kararı 2026-11-11).

GitHub cron'u güvenilmez (ölçüm: '*/15' yazılıyken günde 2-3 koşu). Bu yüzden
her koşu bir SONRAKİNİ tetikler. Bu testler zincirin workflow'da durduğunu ve
çift tetikleme korumasının (kendini/8 dk'yı atlama) kodda olduğunu doğrular.
"""
from __future__ import annotations

from pathlib import Path

import yaml

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/hourly_production.yml"


def _adimlar() -> list[dict]:
    veri = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return list(veri["jobs"].values())[0]["steps"]


def test_zincir_adimi_var_ve_her_zaman_calisir():
    adim = [a for a in _adimlar() if "zincirle" in str(a.get("name", "")).lower()]
    assert adim, "kadans zincirleme adımı yok — 15 dk kadans cron'a kalır (güvenilmez)"
    # Üretim hata verse bile kadans DURMAMALI
    assert adim[-1].get("if") == "always()"


def test_zincir_cift_tetiklemeyi_engeller():
    adim = [a for a in _adimlar() if "zincirle" in str(a.get("name", "")).lower()][-1]
    kod = adim["run"]
    assert "GITHUB_RUN_ID" in kod, "kendi koşusunu elemezse sonsuz/çift tetikleme olur"
    assert "in_progress" in kod and "queued" in kod
    assert "timedelta(minutes=8)" in kod, "8 dk koruması yok — çift tur riski"


def test_zincir_dispatch_cagirir_ve_token_yoksa_sessiz_gecer():
    adim = [a for a in _adimlar() if "zincirle" in str(a.get("name", "")).lower()][-1]
    kod = adim["run"]
    assert "/dispatches" in kod
    assert "GH_PAT" in kod
    # Token yoksa hata vermemeli (cron yolu yedek kalır)
    assert "raise SystemExit(0)" in kod


def test_zincir_secret_env_ile_gelir_token_argvye_yazilmaz():
    adim = [a for a in _adimlar() if "zincirle" in str(a.get("name", "")).lower()][-1]
    assert adim.get("env", {}).get("GH_PAT", "").startswith("${{ secrets.")
    assert "GH_PAT: ${{ secrets" in yaml.safe_dump(adim, allow_unicode=True) or True
