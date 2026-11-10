"""Tests for the expanded v7 line and character schema."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

import modules.senaryo_v7.models as model_module
from modules.senaryo_v7.models import (
    AltyaziStili,
    Diyalog,
    DiyalogRolu,
    Duygu,
    KameraHareketi,
    Karakter,
    Sablon,
)
from modules.senaryo_v7.sablonlar import load_sablonlar


def test_emotion_labels_are_canonical_enum_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """Historical misspellings normalize and unknown feelings warn with closest enum value."""
    assert Diyalog.from_dict({"ses": "suprized", "metin": "Bunu hiç beklemiyordum!"}).ses is Duygu.SASIRMIS
    assert Diyalog.from_dict({"ses": "bikeyn", "metin": "Yine mi toplantı?"}).ses is Duygu.BIKKIN
    assert Diyalog.from_dict({"ses": "soğuk", "metin": "Cevap hayır."}).ses is Duygu.SOGUK
    messages: list[str] = []

    def capture_warning(message: str, *args: object) -> None:
        messages.append(message % args)

    monkeypatch.setattr(model_module._LOG, "warning", capture_warning)
    unexpected = Diyalog.from_dict({"ses": "enerjikx", "metin": "Bu gerçekten çok şaşırtıcı!"})
    assert unexpected.ses is Duygu.ENERJIK
    assert any("en yakın" in message for message in messages)


def test_line_fields_are_populated_and_ranges_validated() -> None:
    """Each line receives bounded speed, estimated emphasis words, production cues and story role."""
    line = Diyalog.from_dict(
        {
            "karakter": "EMEL",
            "metin": "Yılın en büyük sürprizi kapının arkasındaymış!",
            "hiz": 1.8,
            "duraklamams": 4000,
            "altyazistili": "renkli",
            "kamera": "whippan",
            "emojioverlay": "🎉",
            "rol": "twist",
            "twist": True,
        },
        index=2,
        count=5,
    )
    assert line.hiz == 1.25  # out-of-range multiplier is clamped to the supported maximum
    assert line.duraklamams == 3000
    assert line.vurgukelimeler
    assert line.altyazistili is AltyaziStili.RENKLI
    assert line.kamera is KameraHareketi.WHIPPAN
    assert line.rol is DiyalogRolu.TWIST and line.twist
    assert line.emojioverlay == "🎉"
    assert line.tahminisuresn > 0
    assert Diyalog.from_dict({"metin": "Bir söz daha.", "emojioverlay": "🎉 hello"}).emojioverlay is None
    assert line.to_dict()["vurgu_kelimeler"] == line.vurgukelimeler


def test_character_voice_ids_are_fixed_by_gender() -> None:
    """Ahmet/Emel speaker identities override an incompatible incoming voice ID."""
    ahmet = Karakter.from_dict(
        {"ref": "anlatici", "ad": "Anlatıcı", "cinsiyet": "erkek", "sesid": "tr-TR-EmelNeural"}
    )
    emel = Karakter.from_dict({"ref": "arkadas", "ad": "Arkadaş", "cinsiyet": "kadın", "sesid": "custom"})
    assert ahmet.sesid == "tr-TR-AhmetNeural"
    assert emel.sesid == "tr-TR-EmelNeural"
    row = Diyalog.from_dict(
        {
            "karakter_ref": "arkadas",
            "metin": "Bugün çok güzel bir haber aldım!",
            "sesid": "tr-TR-AhmetNeural",
        },
        {"arkadas": emel},
    )
    assert row.karakter == "Arkadaş"
    assert row.sesid == emel.sesid


def test_template_json_uses_refs_and_has_full_metadata() -> None:
    """All shipped templates use character refs, complete line fields, and publish metadata."""
    path = Path("modules/senaryo_v7/sablonlar/veri.json")
    raw = json.loads(path.read_text(encoding="utf-8"))
    for template_data in raw:
        assert template_data["karakterler"]
        assert template_data["etiketler"]
        assert template_data["hedefkitle"]
        assert "mevsimsellik" in template_data
        assert template_data["tekrarkullanimgunsayisi"] > 0
        assert "performanspuani" in template_data
        assert template_data["yasakkelimekontrolugecti"] is True
        for row in template_data["diyaloglar"]:
            assert "karakter_ref" in row and "karakter" not in row
            assert row["ses"] in {feeling.value for feeling in Duygu}
            assert 0.85 <= row["hiz"] <= 1.25
            assert row["duraklamams"] >= 0
            assert row["vurgukelimeler"]
            assert row["altyazistili"] in {style.value for style in AltyaziStili}
            assert row["kamera"] in {camera.value for camera in KameraHareketi}
            assert "tahminisuresn" in row
            assert row["rol"] in {role.value for role in DiyalogRolu}
        roles = [row["rol"] for row in template_data["diyaloglar"]]
        assert roles[0] == "hook" and roles[-1] == "loopkapanis"
        assert roles.count("twist") == 1
        assert sum(bool(row["twist"]) for row in template_data["diyaloglar"]) == 1
    loaded = load_sablonlar(path)
    assert isinstance(loaded[0], Sablon)
    assert loaded[0].diyaloglar[0].karakter


def test_legacy_twist_index_becomes_line_role() -> None:
    """Old index is accepted on input but only the line role is stored by the typed model."""
    template = Sablon.from_dict(
        {
            "kategori": "deneme",
            "baslik": "Twist testi",
            "twist_indeksi": 1,
            "diyaloglar": [
                {"karakter": "A", "metin": "İlk giriş cümlesi geliyor."},
                {"karakter": "B", "metin": "Asıl ters köşe tam şimdi geldi!"},
                {"karakter": "A", "metin": "Şimdi başa dönüp yeniden dinle."},
            ],
        }
    )
    assert not hasattr(template, "twist_indeksi")
    assert template.diyaloglar[1].rol is DiyalogRolu.TWIST
    assert template.diyaloglar[1].twist
    assert template.to_dict()["twist_indeksi"] == 1  # legacy serialization alias


def test_star_import_calisir():
    """from modules.senaryo_v7.models import * AttributeError vermemeli (TODO 1)."""
    import subprocess
    r = subprocess.run(
        [sys.executable, "-c", "from modules.senaryo_v7.models import *; print('ok')"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    assert "ok" in r.stdout


def test_all_icindeki_isimler_gercekten_var():
    """__all__'daki her isim modülde tanımlı olmalı."""
    import modules.senaryo_v7.models as m
    for isim in m.__all__:
        assert hasattr(m, isim), f"__all__ içinde tanımsız isim: {isim}"


def test_saskin_alias_kanonik_degeri():
    """TODO2: şaşkın/saskin SASIRMIS_TR'ye, suprized SASIRMIS'e gider."""
    from modules.senaryo_v7.models import duyguyu_normalize_et, Duygu
    assert duyguyu_normalize_et("şaşkın") is Duygu.SASIRMIS_TR
    assert duyguyu_normalize_et("saskin") is Duygu.SASIRMIS_TR
    assert duyguyu_normalize_et("suprized") is Duygu.SASIRMIS
    assert duyguyu_normalize_et("surprised") is Duygu.SASIRMIS


def test_duygu_aliases_anahtar_tekil():
    """TODO2: _DUYGU_ALIASES sözcüğünde aynı anahtar iki kez tanımlanmamalı (sessizce son kazanır)."""
    import ast
    src = open("modules/senaryo_v7/models.py", encoding="utf-8").read()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "_DUYGU_ALIASES":
                    keys = [ast.literal_eval(k) for k in node.value.keys]
                    assert len(keys) == len(set(keys)), f"Tekrarlanan alias anahtarı: {[k for k in keys if keys.count(k)>1]}"
                    return
    raise AssertionError("_DUYGU_ALIASES bulunamadı")
