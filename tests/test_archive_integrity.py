"""Arşiv bütünlük testi — bobi_tv/archive/videos.json.

API olmadan kanal kontrolü yapılamaz; şema + tekillik + durum geçerliliği
yeterlidir. Kayıtlar asla silinmez; durum alanıyla işaretlenir.
"""
from __future__ import annotations

import json
from pathlib import Path

ARCHIVE = Path("bobi_tv/archive/videos.json")
GECEERLI_DURUMLAR = {"yayinda", "kaldirildi"}


def _load() -> list[dict]:
    assert ARCHIVE.exists(), "Arşiv dosyası bulunamadı"
    data = json.loads(ARCHIVE.read_text(encoding="utf-8"))
    assert isinstance(data, list), "videos.json bir dizi olmalı"
    return data


def test_archive_records_have_video_id() -> None:
    for i, rec in enumerate(_load()):
        assert isinstance(rec, dict), f"Kayıt {i} nesne olmalı"
        vid = rec.get("video_id")
        assert isinstance(vid, str) and vid.strip(), f"Kayıt {i} video_id eksik"


def test_archive_no_duplicate_video_id() -> None:
    ids = [rec["video_id"] for rec in _load()]
    assert len(ids) == len(set(ids)), f"Yinelenen video_id: {[i for i in set(ids) if ids.count(i) > 1]}"


def test_archive_durum_valid_when_present() -> None:
    # Eski kayıtlarda durum alanı olmayabilir (legacy); varsa geçerli olmalı.
    for rec in _load():
        if "durum" in rec:
            assert rec["durum"] in GECEERLI_DURUMLAR, (
                f"{rec['video_id']} durum='{rec['durum']}' geçersiz; "
                f"olası değerler: {sorted(GECEERLI_DURUMLAR)}"
            )


def test_archive_kaldirildi_records_keep_reason_metadata() -> None:
    # Kaldırılan kayıtlar gövdede durur; silinme nedeni (varsa) korunmalı.
    for rec in _load():
        if rec.get("durum") == "kaldirildi":
            assert "url" in rec or "baslik" in rec, (
                f"{rec['video_id']} kaldirildi kaydı en az url/baslik taşımalı"
            )


def test_archive_yayinda_records_have_url() -> None:
    for rec in _load():
        if rec.get("durum") == "yayinda":
            assert rec.get("url", "").startswith("https://"), (
                f"{rec['video_id']} yayinda kaydında geçerli url olmalı"
            )
