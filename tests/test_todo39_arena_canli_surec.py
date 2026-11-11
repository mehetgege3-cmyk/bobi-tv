"""Arena canlı süreç testleri (2026-11-11 kullanıcı isteği).

Kullanıcı:
  "Timeout kullanma, bazen Arena AI uzun düşünüyor; bunu anlık olarak pipeline
   içinde gösterirsek yanıtın oluşturma sürecini varsayımsal değil, gerçek
   olarak göstermiş oluruz."

Bu dosya o sözü kilitler:
  1. `_arena_sorgusu_yap` SABİT süre sınırı kullanmaz (idle/maks frenleri ayrı),
     varsayılanları çok geniş ve env ile ayarlanır.
  2. Her ~10 sn'de canlı ilerleme satırı basar (flush=True → Actions'ta anında).
  3. Gerçek yanıt süresi `bobi_tv/state/arena_sure.json`'a yazılır.
  4. Canlı test workflow'u tek video üretir, kuyruğu kilitlemez (concurrency yok).
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import yaml

KOK = Path(__file__).resolve().parents[1]
ARENA = KOK / "modules/arena_api.py"
CANLI = KOK / ".github/workflows/canli_test.yml"


def _kaynak() -> str:
    return inspect.getsource(__import__("modules.arena_api", fromlist=["x"]))


# ---------------------------------------------------------------------------
# 1) Sabit timeout yok, frenler env'den
# ---------------------------------------------------------------------------


def test_arena_sorgusunda_sabit_timeout_yok():
    """Eski imza `timeout=130` idi: Arena 3 dk düşünürse cevap çöpe gidiyordu."""
    kaynak = _kaynak()
    assert "timeout: int = 130" not in kaynak
    assert "timeout=130" not in kaynak
    assert "timeout=120" not in kaynak
    # Yeni güvenlik frenleri env ile ayarlanır
    assert "ARENA_IDLE_DK" in kaynak and "ARENA_MAKS_DK" in kaynak


def test_arena_frenleri_cevabi_kaybetmez():
    """Fren devreye girse bile yeterli metin varsa CEVAP DÖNDÜRÜLÜR."""
    kaynak = _kaynak()
    assert "return cevap if len(cevap) >= min_cevap_uzunlugu else None" in kaynak


def test_arena_canli_ilerleme_satiri_basar():
    """Her 10 sn'de tek satır: saat · durum · karakter · son değişim."""
    kaynak = _kaynak()
    assert "son_kalp" in kaynak, "canlı ilerleme sayacı yok"
    assert "düşünüyor" in kaynak and "karakter" in kaynak
    assert "flush=True" in kaynak, "Actions'ta anında görünmesi için flush şart"


def test_arena_kendi_dusunme_suresini_de_yazar():
    """Arena arayüzü 'Thought for 12 seconds' gösteriyor; loglanmalı."""
    assert "Thought for" in _kaynak()


# ---------------------------------------------------------------------------
# 2) Süre kaydı (panel/rapor varsayım değil ÖLÇÜM gösterir)
# ---------------------------------------------------------------------------


def test_arena_sure_kaydi_yazilir(tmp_path, monkeypatch):
    import modules.arena_api as aa

    hedef = tmp_path / "arena_sure.json"
    monkeypatch.setattr(aa, "ARENA_SURE_YOLU", hedef)
    aa._arena_sure_kaydet(41.0, 820, "12 seconds")
    aa._arena_sure_kaydet(63.0, 900, "20 seconds")
    veri = json.loads(hedef.read_text(encoding="utf-8"))
    assert veri["son"]["saniye"] == 63.0
    assert veri["ortalama"] == 52.0
    assert veri["en_uzun"] == 63.0
    assert veri["ornek"] == 2
    assert len(veri["olcumler"]) == 2


def test_arena_sure_kaydi_20_olcumle_sinirli(tmp_path, monkeypatch):
    import modules.arena_api as aa

    hedef = tmp_path / "arena_sure.json"
    monkeypatch.setattr(aa, "ARENA_SURE_YOLU", hedef)
    for i in range(30):
        aa._arena_sure_kaydet(float(i), 100)
    veri = json.loads(hedef.read_text(encoding="utf-8"))
    assert veri["ornek"] == 20, "dosya şişmesin"


def test_panel_arena_suresini_gosterir(tmp_path, monkeypatch):
    import modules.arena_api as aa
    import modules.telegram_bot as tb

    hedef = tmp_path / "arena_sure.json"
    monkeypatch.setattr(aa, "ARENA_SURE_YOLU", hedef)
    aa._arena_sure_kaydet(55.0, 640, "17 seconds")
    metin = tb._arena_sure_ozeti()
    assert "55 sn" in metin and "17 seconds" in metin


def test_panel_olcum_yoksa_satir_uydurmaz(tmp_path, monkeypatch):
    import modules.arena_api as aa
    import modules.telegram_bot as tb

    monkeypatch.setattr(aa, "ARENA_SURE_YOLU", tmp_path / "yok.json")
    assert tb._arena_sure_ozeti() == ""


# ---------------------------------------------------------------------------
# 3) Canlı test workflow'u
# ---------------------------------------------------------------------------


def _canli() -> dict:
    return yaml.safe_load(CANLI.read_text(encoding="utf-8"))


def test_canli_test_workflow_var_ve_tek_video():
    veri = _canli()
    job = veri["jobs"]["canli-test"]
    env = {a["name"]: a for a in job["steps"] if a.get("env")}
    ortam = {}
    for ad in env.values():
        ortam.update(ad["env"])
    assert ortam.get("TUR_BASINA_URETIM") == "1"
    assert ortam.get("URETIM_TAVANI") == "1", "canlı test 1 video üretmeli"
    assert ortam.get("CANLI_TEST") == "1"


def test_canli_test_kuyrugu_kilitlemez():
    """8 saatlik üretim job'u açıkken bile test HEMEN başlamalı → concurrency YOK."""
    veri = _canli()
    assert "concurrency" not in veri["jobs"]["canli-test"]
    assert "concurrency" not in veri


def test_canli_test_arena_frenlerini_env_ile_verir():
    veri = _canli()
    ortam = {}
    for ad in veri["jobs"]["canli-test"]["steps"]:
        ortam.update(ad.get("env") or {})
    assert ortam.get("ARENA_IDLE_DK") == "15"
    assert ortam.get("ARENA_MAKS_DK") == "45"
    assert ortam.get("PYTHONUNBUFFERED") == "1", "log anlık aksın"


def test_canli_test_yukleme_ve_kapak_icin_gerekli_secretlari_gecirir():
    veri = _canli()
    ortam = {}
    for ad in veri["jobs"]["canli-test"]["steps"]:
        ortam.update(ad.get("env") or {})
    for gerekli in ("YOUTUBE_TOKEN", "YOUTUBE_CLIENT_SECRET", "ARENA_COOKIES_JSON",
                    "TELEGRAM_BOT_TOKEN"):
        assert gerekli in ortam, f"{gerekli} geçirilmiyor"
        assert ortam[gerekli].startswith("${{ secrets."), "secret olarak geçmeli"


def test_canli_test_ozet_ve_artifact_uretir():
    veri = _canli()
    adlar = [a.get("name", "") for a in veri["jobs"]["canli-test"]["steps"]]
    assert any("özet" in a.lower() for a in adlar)
    assert any("artifact" in a.lower() for a in adlar)
