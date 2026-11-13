"""Workspace bütçe bekçisi testleri.

Gerçek olay (2026-11-13): 86 MB video indirildi → 179 MB → 33 dosya kaydedilmedi.
"""

import subprocess
import sys
from pathlib import Path

from tools import disk_bekci


def test_insan_bicimlendirme():
    assert disk_bekci.insan(500) == "500 B"
    assert disk_bekci.insan(2048) == "2 KB"
    assert "MB" in disk_bekci.insan(5 * 1024 * 1024)


def test_yasak_uzantilar_tanimi():
    assert ".mp4" in disk_bekci.YASAK
    assert ".mov" in disk_bekci.YASAK
    assert ".jpg" not in disk_bekci.YASAK


def test_tarama_calisir(tmp_path):
    (tmp_path / "kucuk.jpg").write_bytes(b"x" * 100)
    (tmp_path / "alt").mkdir()
    (tmp_path / "alt" / "orta.txt").write_bytes(b"y" * 200)
    toplam, sayi, _ = disk_bekci.tara(tmp_path)
    assert sayi == 2
    assert toplam == 300


def test_buyuk_mp4_ihlal_eder(tmp_path):
    """4 MB mp4 → çıkış kodu 1 (yasak dosya)."""
    (tmp_path / "kanit.mp4").write_bytes(b"0" * (4 * 1024 * 1024))
    s = subprocess.run(
        [sys.executable, str(Path(disk_bekci.__file__)), "--kok", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert s.returncode == 1
    assert "YASAK DOSYA" in s.stdout


def test_bos_dizin_gecer(tmp_path):
    (tmp_path / "a.jpg").write_bytes(b"x" * 50)
    s = subprocess.run(
        [sys.executable, str(Path(disk_bekci.__file__)), "--kok", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert s.returncode == 0
    assert "Bütçe içinde" in s.stdout
