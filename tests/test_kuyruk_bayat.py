"""TODO 4 — Kuyruk bayat kayıt koruması testleri.

Kapsam: dizin pathspec'inin silmeleri stage ettiği (glob'un etmediği), workflow'un
doğru komutu kullandığı ve zaten yayınlanmış kuyruk paketinin render edilmeden
tüketildiği. main_pipeline dinamik olarak import edilir (mypy build'ine ek hata
sürüklememek için statik import kullanılmaz).
"""

from __future__ import annotations

import importlib
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_KOK = Path(__file__).resolve().parent.parent
WORKFLOW = REPO_KOK / ".github" / "workflows" / "hourly_production.yml"


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)


def _gecici_git_repo(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert _git(["init", "-q"], repo).returncode == 0
    _git(["config", "user.email", "test@test"], repo)
    _git(["config", "user.name", "test"], repo)
    kuyruk = repo / "bobi_tv" / "queue"
    kuyruk.mkdir(parents=True)
    (kuyruk / "paket.json").write_text("{}\n", encoding="utf-8")
    assert _git(["add", "-f", "bobi_tv/queue/"], repo).returncode == 0
    assert _git(["commit", "-q", "-m", "init"], repo).returncode == 0
    (kuyruk / "paket.json").unlink()  # tüketildi (yükleme sonrası yerel silme)
    return repo, kuyruk


def test_dizin_pathspec_silmeyi_stage_eder(tmp_path: Path) -> None:
    """TODO 4a: `git add -f bobi_tv/queue/` tüketilen (silinen) kuyruk kaydının
    silmesini de stage eder — kayıt repodan düşer, bayat kuyruk oluşmaz."""
    repo, _ = _gecici_git_repo(tmp_path)
    assert _git(["add", "-f", "bobi_tv/queue/"], repo).returncode == 0
    staged = _git(["diff", "--staged", "--name-status"], repo).stdout
    assert "D" in staged and "paket.json" in staged


def test_glob_silmeleri_kacirir_kuyrukta_baska_dosya_varsa(tmp_path: Path) -> None:
    """Eski davranışın kanıtı: kabuk glob'u yalnızca VAR OLAN dosyaları genişletir.
    Kuyrukta başka dosya dururken tüketilen kaydın silmesi stage'e GİRMEZ →
    silme commit'lenmez → bayat kayıt repoda kalır (C1'in gerçek mekanizması).
    Dizin pathspec'i bu yarışı ortadan kaldırır."""
    repo = tmp_path / "repo"
    repo.mkdir()
    assert _git(["init", "-q"], repo).returncode == 0
    _git(["config", "user.email", "test@test"], repo)
    _git(["config", "user.name", "test"], repo)
    kuyruk = repo / "bobi_tv" / "queue"
    kuyruk.mkdir(parents=True)
    (kuyruk / "tuketilen.json").write_text("{}\n", encoding="utf-8")
    (kuyruk / "kota_bekleyen.json").write_text("{}\n", encoding="utf-8")
    assert _git(["add", "-f", "bobi_tv/queue/"], repo).returncode == 0
    assert _git(["commit", "-q", "-m", "init"], repo).returncode == 0

    (kuyruk / "tuketilen.json").unlink()  # tüketildi (yükleme sonrası yerel silme)
    eski = subprocess.run(
        ["bash", "-lc", "git add -f bobi_tv/queue/*.json || true"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    assert eski.returncode == 0
    staged = _git(["diff", "--staged", "--name-status"], repo).stdout
    assert "tuketilen.json" not in staged, (
        "Glob yalnızca var olanları genişletir: silme stage'e girmemeli (eski hata)"
    )

    # Yeni komut aynı durumda silmeyi de alır:
    assert _git(["add", "-f", "bobi_tv/queue/"], repo).returncode == 0
    staged_yeni = _git(["diff", "--staged", "--name-status"], repo).stdout
    assert "D" in staged_yeni and "tuketilen.json" in staged_yeni


def test_workflow_kuyruk_commit_dizin_pathspec_kullanir() -> None:
    veri: object = yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    assert isinstance(veri, dict)
    adimlar: Any = veri["jobs"]["uret-ve-yayinla"]["steps"]
    commit_adim = next(adim for adim in adimlar if "kuyruk durumunu commit et" in str(adim.get("name", "")))
    yazi = str(commit_adim.get("run", ""))
    assert "git add -f bobi_tv/queue/" in yazi, "Dizin pathspec'i kullanılmalı"
    assert "queue/*.json" not in yazi, "Kabuk glob'u silmeleri stage etmez — kaldırılmalı"


def _yasak_fonksiyon(ad: str) -> Any:
    def cagirilmamali(*args: object, **kwargs: object) -> None:
        raise AssertionError(f"{ad} çağrılmamalıydı (bayat paket render edilmemeli)")

    return cagirilmamali


def test_yuklenmis_paket_render_edilmeden_tuketilir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """TODO 4b: published kaydı dolu kuyruk paketi → render YOK, kayıt tüketilir."""
    mp: Any = importlib.import_module("main_pipeline")
    kuyruk = tmp_path / "queue"
    kuyruk.mkdir()
    kayit = {"dosya_adi": "20261111_0001_x", "baslik": "Test", "final_video": ""}
    hedef = kuyruk / "20261111_0001_x.json"
    hedef.write_text(json.dumps(kayit), encoding="utf-8")

    monkeypatch.setattr(mp, "KUYRUK_YOLU", kuyruk)
    monkeypatch.setattr(mp, "LOG_YOLU", tmp_path / "logs")
    monkeypatch.setattr(mp, "zaten_yuklendi_mi", lambda dosya_adi: "vid123")
    for ad in ("senaryo_seslendir", "video_render", "kapak_uret"):
        monkeypatch.setattr(mp, ad, _yasak_fonksiyon(ad))

    paket, dosya = mp.kuyruktan_paket_hazirla()
    assert paket is None and dosya is None
    assert not hedef.exists(), "Bayat kuyruk kaydı tüketilmeli (silinmeli)"


def test_yuklenmemis_paket_render_yolu_korunur(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """published kaydı yoksa mevcut davranış korunur: kota kuyruğu render edilip
    döner ve kayıt silinmez (silme yükleme başarısından sonradır)."""
    mp: Any = importlib.import_module("main_pipeline")
    kuyruk = tmp_path / "queue"
    kuyruk.mkdir()
    kayit = {"dosya_adi": "20261111_0002_y", "baslik": "Test2", "final_video": "yok.mp4"}
    hedef = kuyruk / "20261111_0002_y.json"
    hedef.write_text(json.dumps(kayit), encoding="utf-8")

    monkeypatch.setattr(mp, "KUYRUK_YOLU", kuyruk)
    monkeypatch.setattr(mp, "LOG_YOLU", tmp_path / "logs")
    monkeypatch.setattr(mp, "zaten_yuklendi_mi", lambda dosya_adi: None)
    monkeypatch.setattr(mp, "senaryo_seslendir", lambda paket: paket)
    monkeypatch.setattr(mp, "video_render", lambda paket: None)
    monkeypatch.setattr(mp, "kapak_uret", lambda paket: None)

    paket, dosya = mp.kuyruktan_paket_hazirla()
    assert paket is not None and dosya is not None
    assert hedef.exists(), "Yüklenmemiş paket tüketilmemeli (kota kuyruğu korunur)"
