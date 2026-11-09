"""Senaryo v7 migration, compatibility, settings, IO and determinism tests."""

from __future__ import annotations

import json
import logging
import random
from dataclasses import MISSING, fields, replace
from pathlib import Path
from typing import Any

import pytest

import modules.scenario as legacy
from modules.senaryo_v7.arsiv import ArsivDeposu
from modules.senaryo_v7.ayarlar import Ayarlar
from modules.senaryo_v7.cikti import CiktiYazici
from modules.senaryo_v7.dogrulama.migration import migrate
from modules.senaryo_v7.exceptions import ArsivHatasi, CiktiHatasi, KuyrukHatasi, SablonHatasi, SenaryoHatasi
from modules.senaryo_v7.kuyruk import KuyrukDeposu
from modules.senaryo_v7.loglama import JsonLogFormatter
from modules.senaryo_v7.models import Diyalog, Karakter, Sablon, Senaryo, SenaryoPaketi
from modules.senaryo_v7.sablonlar import load_sablonlar
from modules.senaryo_v7.service import SenaryoUretici


def _ayarlar(tmp_path: Path) -> Ayarlar:
    """Testleri repo arşiv/çıktı dosyalarından izole eden ayarlar oluşturur."""
    defaults = Ayarlar.ortamdan({})
    return replace(
        defaults,
        arsiv_yolu=tmp_path / "videos.json",
        senaryo_yolu=tmp_path / "scripts",
        arena_kuyruk_yolu=tmp_path / "arena",
    )


def test_legacy_one_argument_api_remains_compatible(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Eski `senaryo_paketi_olustur(video_no)` çağrısı dict sözleşmesini korur."""
    monkeypatch.setattr(legacy, "ARSIV_YOLU", tmp_path / "videos.json")
    monkeypatch.setattr(legacy, "SENARYO_YOLU", tmp_path / "scripts")
    monkeypatch.setattr(legacy, "ARENA_KUYRUK_YOLU", tmp_path / "arena")
    package = legacy.senaryo_paketi_olustur(73)
    assert isinstance(package, dict)
    assert package["video_no"] == 73
    assert package["semaversiyonu"] == "7.0"
    assert package["senaryo"]["semaversiyonu"] == "7.0"
    scenario = package["senaryo"]
    assert scenario["karakterler"]
    assert "etiketler" in scenario and "hedefkitle" in scenario
    rows = scenario["diyaloglar"]
    assert rows and all(row["vurgukelimeler"] and row["sesid"] for row in rows)
    assert all("hiz" in row and "duraklamams" in row and "tahminisuresn" in row for row in rows)
    assert any(row["rol"] == "twist" and row["twist"] for row in rows)
    assert (tmp_path / "scripts" / f"{package['dosya_adi']}.json").exists()


def test_v6_satirlar_migration_adds_v7_schema_and_roles() -> None:
    """Eski `satirlar` kaydı konuşmacılı diyaloglara yükseltilir."""
    old = {"semaversiyonu": "6.0", "satirlar": ["MERT: İlk cümle.", "AYŞE: İkinci cümle."]}
    updated = migrate(old)
    assert updated["semaversiyonu"] == "7.0"
    assert updated["diyaloglar"][0]["karakter"] == "MERT"
    assert updated["diyaloglar"][1]["cinsiyet"] == "kadin"
    assert updated["diyaloglar"][1]["karakter_ref"]
    assert updated["diyaloglar"][1]["sesid"] == "tr-TR-EmelNeural"
    assert updated["diyaloglar"][0]["rol"] == "hook"
    assert updated["diyaloglar"][0]["vurgukelimeler"]
    assert "satirlar" in updated  # migration non-destructive, legacy source retained


def test_nested_package_migration() -> None:
    """Legacy v6 package ve iç Senaryo beraber v7 sürümüne taşınır."""
    package = {"video_no": 4, "senaryo": {"satirlar": ["A: bir", "B: iki", "A: üç"]}}
    migrated = migrate(package)
    assert migrated["semaversiyonu"] == "7.0"
    assert migrated["senaryo"]["semaversiyonu"] == "7.0"
    assert len(migrated["senaryo"]["diyaloglar"]) == 3


def test_future_schema_is_not_silently_downgraded() -> None:
    """Bilinmeyen v8 şeması açık bir SenaryoHatasi ile reddedilir."""
    with pytest.raises(SenaryoHatasi, match="Daha yeni şema"):
        migrate({"semaversiyonu": "8.0", "diyaloglar": []})


def test_seeded_generation_is_byte_equivalent(tmp_path: Path) -> None:
    """Aynı seed/video_no ile model ve paket alanları deterministiktir."""
    settings = _ayarlar(tmp_path)
    first = SenaryoUretici(settings, seed=2027).senaryo_paketi_olustur(11)
    second = SenaryoUretici(settings, seed=2027).senaryo_paketi_olustur(11)
    assert json.dumps(first, ensure_ascii=False, sort_keys=True) == json.dumps(
        second, ensure_ascii=False, sort_keys=True
    )


def test_injected_random_object_is_used(tmp_path: Path) -> None:
    """Caller-provided `random.Random` controls category and template selection."""
    settings = _ayarlar(tmp_path)
    first = SenaryoUretici(settings, rng=random.Random(4)).senaryo_paketi_olustur(12)
    second = SenaryoUretici(settings, rng=random.Random(4)).senaryo_paketi_olustur(12)
    assert first["senaryo"]["kategori"] == second["senaryo"]["kategori"]
    assert first["senaryo"]["baslik"] == second["senaryo"]["baslik"]


def test_settings_environment_override_and_validation() -> None:
    """Magic-number settings are centrally configurable and validated."""
    settings = Ayarlar.ortamdan(
        {
            "BOBI_SCENARIO_HOOK_BANT_AZAMI": "42",
            "BOBI_SCENARIO_TAHMINI_SANIYE_KELIME": "0.4",
            "BOBI_SCENARIO_MINIMUM_YAYIN_SURESI": "17",
            "BOBI_SCENARIO_HEDEF_TAHMINI_SURE": "20",
        }
    )
    assert settings.hook_bant_azami == 42
    assert settings.tahmini_saniye_kelime == 0.4
    assert settings.minimum_yayin_suresi == 17
    with pytest.raises(SenaryoHatasi, match="tam sayı"):
        Ayarlar.ortamdan({"BOBI_SCENARIO_HOOK_BANT_AZAMI": "uzun"})


def test_all_domain_model_fields_have_default_and_description() -> None:
    """Diyalog, Senaryo, Paket ve Şablon alanları typed/documented defaults taşır."""
    for model in (Karakter, Diyalog, Senaryo, SenaryoPaketi, Sablon):
        for item in fields(model):
            assert item.metadata.get("description"), (model.__name__, item.name)
            assert item.default is not MISSING or item.default_factory is not MISSING


def test_broken_template_has_domain_error(tmp_path: Path) -> None:
    """Bozuk şablon JSON'u SablonHatasi olarak ve dosya adıyla raporlanır."""
    path = tmp_path / "bad.json"
    path.write_text("{broken", encoding="utf-8")
    with pytest.raises(SablonHatasi, match="Şablon dosyası okunamadı"):
        load_sablonlar(path)


def test_broken_queue_is_reported_and_removed(tmp_path: Path) -> None:
    """Kuyruk okuyucusu bozuk JSON'u KuyrukHatasi ile bildirir."""
    settings = _ayarlar(tmp_path)
    settings.arena_kuyruk_yolu.mkdir(parents=True)
    path = settings.arena_kuyruk_yolu / "arena_bad.json"
    path.write_text("not-json", encoding="utf-8")
    queue = KuyrukDeposu(settings)
    with pytest.raises(KuyrukHatasi, match="Kuyruk kaydı okunamadı"):
        queue.oku(path)
    queue.tuket(path)
    assert not path.exists()


def test_service_skips_corrupt_queue_and_falls_back(tmp_path: Path) -> None:
    """Servis bozuk kuyruğu loglayıp tüketir; fallback'te üretimi sürdürebilir."""
    settings = _ayarlar(tmp_path)
    settings.arena_kuyruk_yolu.mkdir(parents=True)
    (settings.arena_kuyruk_yolu / "arena_bad.json").write_text("{", encoding="utf-8")
    logger = logging.getLogger("test.senaryo.queue")
    logger.handlers.clear()
    logger.addHandler(logging.NullHandler())
    logger.propagate = False
    service = SenaryoUretici(settings, seed=1, logger=logger)
    assert service.kuyruktan_arena_senaryosu_al(1) is None
    assert not list(settings.arena_kuyruk_yolu.glob("arena_*.json"))


def test_unwritable_output_uses_cikti_hatasi(tmp_path: Path) -> None:
    """Dosya yerine dizin beklenen path verilince yazıcı CiktiHatasi yükseltir."""
    blocker = tmp_path / "not-a-directory"
    blocker.write_text("file", encoding="utf-8")
    settings = replace(_ayarlar(tmp_path), senaryo_yolu=blocker)
    writer = CiktiYazici(settings)
    package = SenaryoPaketi(video_no=1, dosya_adi="test")
    with pytest.raises(CiktiHatasi, match="Senaryo paketi yazılamadı"):
        writer.yaz(package)


def test_output_write_failure_preserves_arena_queue(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Çıktı yazımı başarısızsa geçerli Arena girdisi kuyrukta bırakılır."""
    settings = _ayarlar(tmp_path)
    settings.arena_kuyruk_yolu.mkdir(parents=True)
    path = settings.arena_kuyruk_yolu / "arena_retry.json"
    path.write_text(json.dumps({"senaryo": {"diyaloglar": []}}), encoding="utf-8")
    service = SenaryoUretici(settings, seed=1)
    scenario = Senaryo(baslik="Test", diyaloglar=[Diyalog(karakter="A", metin="Örnek.")])
    monkeypatch.setattr(service, "senaryo_dogrula_ve_zenginlestir", lambda raw, video_no: scenario)

    def fail_write(package: SenaryoPaketi) -> Path:
        raise CiktiHatasi("diske yazılamadı")

    monkeypatch.setattr(service.cikti, "yaz", fail_write)
    with pytest.raises(CiktiHatasi, match="diske yazılamadı"):
        service.kuyruktan_arena_senaryosu_al(2)
    assert path.exists()


def test_malformed_archive_uses_arsiv_hatasi(tmp_path: Path) -> None:
    """Bozuk yayın geçmişi sessizce boş sayılmaz, ArsivHatasi olarak yükselir."""
    settings = _ayarlar(tmp_path)
    settings.arsiv_yolu.write_text("not-json", encoding="utf-8")
    with pytest.raises(ArsivHatasi, match="Video arşivi okunamadı"):
        ArsivDeposu(settings).yukle()


def test_json_logging_formatter_outputs_structured_fields() -> None:
    """JSON log formatter en az seviye/logger/mesaj alanlarını üretir."""
    record = logging.LogRecord("test", logging.WARNING, __file__, 1, "Örnek %s", ("olay",), None)
    payload: dict[str, Any] = json.loads(JsonLogFormatter().format(record))
    assert payload["seviye"] == "WARNING"
    assert payload["mesaj"] == "Örnek olay"
    assert payload["logger"] == "test"
