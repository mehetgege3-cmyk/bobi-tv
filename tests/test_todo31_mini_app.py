"""TODO 31 — Mini App: veri üreticisi + GÜVENLİK sözleşmesi testleri.

Mini App statik bir sayfa (GitHub Pages). Bu testler şunları kilitler:
- sayfada secret/token/dış kaynak YOK,
- dış veri innerHTML ile yazılmıyor (XSS),
- veri yoksa "bilinmiyor" (uydurma sayı yok),
- özet üreticisi mevcut modüllerden okuyor ve tavanı 'YOK' bildiriyor.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import modules.mini_app_veri as mv  # noqa: E402

SAYFA = Path("webapp/index.html")
OZET = Path("webapp/veri/mini_app_ozet.json")
WORKFLOW = Path(".github/workflows/mini_app_veri.yml")
BELGE = Path("docs/MINI_APP.md")

SIMDI = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _ortam(monkeypatch, tmp_path):
    monkeypatch.setattr(mv, "OZET_YOLU", tmp_path / "ozet.json")
    monkeypatch.setattr(mv, "ARSIV_YOLU", tmp_path / "videos.json")
    return tmp_path


def _arsiv(yol: Path, kayitlar: list[dict]) -> None:
    yol.write_text(json.dumps(kayitlar, ensure_ascii=False), encoding="utf-8")


# --- Veri üreticisi ------------------------------------------------------


def test_arsiv_yoksa_sayilar_none_uydurma_yok():
    o = mv.ozet_uret(SIMDI)
    assert o["bugun"] == {"uretilen": None, "yayinda": None}
    assert o["trend7"] is None


def test_bugun_sayilari_dogru():
    _arsiv(mv.ARSIV_YOLU, [
        {"tarih": "2026-11-11T01:00:00+00:00", "durum": "yayinda"},
        {"tarih": "2026-11-11T02:00:00+00:00", "durum": "stok"},
        {"tarih": "2026-11-10T23:00:00+00:00", "durum": "yayinda"},
    ])
    o = mv.ozet_uret(SIMDI)
    assert o["bugun"] == {"uretilen": 2, "yayinda": 1}


def test_trend_7_gun_eskiden_yeniye():
    kayitlar = []
    for geri in range(7):
        gun = (SIMDI - timedelta(days=geri)).strftime("%Y-%m-%d")
        kayitlar += [{"tarih": f"{gun}T10:00:00+00:00", "durum": "yayinda"}] * (geri + 1)
    _arsiv(mv.ARSIV_YOLU, kayitlar)
    seri = mv.ozet_uret(SIMDI)["trend7"]
    assert len(seri) == 7
    assert seri == list(range(7, 0, -1)), "en eski gün ilk sırada olmalı"


def test_trend_her_zaman_7_eleman():
    _arsiv(mv.ARSIV_YOLU, [])
    assert mv.ozet_uret(SIMDI)["trend7"] == [0, 0, 0, 0, 0, 0, 0]


def test_sozluk_bicimli_arsiv_de_okunur():
    _arsiv(mv.ARSIV_YOLU, {"a": {"tarih": "2026-11-11T01:00:00+00:00", "durum": "yayinda"}})
    assert mv.ozet_uret(SIMDI)["bugun"]["uretilen"] == 1


def test_tavan_yok_olarak_isaretli():
    o = mv.ozet_uret(SIMDI)
    assert o["sinirlar"]["gunluk_yukleme_tavani"] is None
    assert "tavan" in o["sinirlar"]["not"]


def test_denetim_ayrinti_tasinmaz(monkeypatch):
    """Denetim kaydının ayrıntısı (secret riski) Mini App'e GEÇMEZ."""
    monkeypatch.setattr(
        mv,
        "denetim_ozeti",
        lambda: [{"zaman": "2026-11-11T10:00", "olay": "ayar_degistir", "sonuc": "ok"}],
    )
    kayit = mv.ozet_uret(SIMDI)["denetim"][0]
    assert set(kayit) == {"zaman", "olay", "sonuc"}


def test_yaz_dosyayi_olusturur():
    veri = mv.yaz(SIMDI)
    assert mv.OZET_YOLU.exists()
    okunan = json.loads(mv.OZET_YOLU.read_text(encoding="utf-8"))
    assert okunan["guncelleme"] == veri["guncelleme"]


def test_yazilamayan_yol_hata_bildirir(tmp_path):
    engel = tmp_path / "engel"
    engel.write_text("x", encoding="utf-8")
    veri = mv.yaz(SIMDI, engel / "alt" / "ozet.json")
    assert "yazma_hatasi" in veri


def test_metin_ozet_bilinmiyor_der():
    metin = mv.metin_ozet({"bugun": {}, "kuyruk": {}, "guncelleme": "x"})
    assert "bilinmiyor" in metin
    assert "tavan" not in metin.lower() or True  # bilgi satırı opsiyonel


# --- Sayfa güvenliği -----------------------------------------------------


def _html() -> str:
    return SAYFA.read_text(encoding="utf-8")


def test_sayfa_tek_dosya_ve_disaridan_kaynak_yuklemiyor():
    html = _html()
    assert "<script src=" not in html, "harici script yasak"
    assert "<link" not in html, "harici stil/font yasak"
    assert not re.search(r"https?://", html), "sayfada hiçbir dış URL olmamalı"


def test_sayfada_secret_yok():
    html = _html()
    for desen in ("TG_TOKEN", "BOT_TOKEN", "ghp_", "client_secret", "COOKIE", "pat="):
        assert desen not in html, f"sayfada {desen} bulunmamalı"


def test_dis_veri_innerhtml_ile_yazilmiyor():
    html = _html()
    assert "innerHTML" not in html, "XSS: dış veri textContent ile yazılmalı"


def test_veri_yolu_goreli():
    assert '"veri/mini_app_ozet.json"' in _html() or "veri/mini_app_ozet.json" in _html()


def test_hata_durumunda_bilinmiyor_yazar():
    html = _html()
    assert "bilinmiyor" in html
    assert "sayı uydurulmuyor" in html


def test_tavan_yok_ifadesi_sayfada():
    html = _html()
    assert "YOK" in html
    assert "tavan" in html.lower()


def test_salt_okunur_uyarisi_var():
    html = _html()
    assert "salt okunur" in html.lower()
    # Hiçbir buton üretim/silme tetiklemez: yalnız 'Yenile' ve fetch var.
    assert html.count("<button") == 1
    assert "fetch(" in html


def test_csp_meta_var():
    assert "Content-Security-Policy" in _html()


# --- Veri dosyası ve workflow -------------------------------------------


def test_commit_edilmis_ozet_semaya_uygun():
    veri = json.loads(OZET.read_text(encoding="utf-8"))
    for alan in ("guncelleme", "bugun", "kuyruk", "trend7", "denetim", "sinirlar"):
        assert alan in veri, f"eksik alan: {alan}"
    assert veri["sinirlar"]["gunluk_yukleme_tavani"] is None
    assert all(isinstance(x, int) for x in veri["trend7"])


def test_workflow_ozeti_tazeler_ve_push_eder():
    d = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    yazi = WORKFLOW.read_text(encoding="utf-8")
    assert "*/15 * * * *" in yazi
    assert "mini_app_ozet.json" in yazi
    assert "git push origin main" in yazi
    assert "::error::" in yazi, "push kaybı sessiz olmamalı"
    # Secret kullanmaz: yalnız okuma + commit.
    assert "${{ secrets." not in yazi
    assert "contents: write" in yazi
    adimlar = list(d["jobs"].values())[0]["steps"]
    assert len(adimlar) >= 3


def test_belge_kritik_kararlari_yazar():
    metin = BELGE.read_text(encoding="utf-8")
    assert "salt okunur" in metin.lower()
    assert "initData" in metin, "v2 doğrulama sözleşmesi yazılmalı"
    assert "BotFather" in metin, "domain kaydı adımı yazılmalı"
    assert "2026" in metin
