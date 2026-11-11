"""TODO 28 — Poller gecikmesi: tasarım notu + tur başına iş sınırı.

Not: `docs/POLLER_GECIKMESI.md` kararları (webhook yok, poller kalır) ve
uygulanan hafifletmeler burada KODLA tutarlı mı diye doğrulanır.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import modules.tekillestirme as tk  # noqa: E402
import modules.telegram_bot as tb  # noqa: E402

NOT = Path("docs/POLLER_GECIKMESI.md")
POLLER = Path(".github/workflows/telegram_bot.yml")


@pytest.fixture(autouse=True)
def _ortam(monkeypatch, tmp_path):
    monkeypatch.setattr(tb, "CHAT_ID", "123456789")
    monkeypatch.setattr(tb, "BOT_TOKEN", "fake:token")
    monkeypatch.setattr(tb, "MENU_STATE_YOLU", tmp_path / "menu.json")
    tk.sifirla()


def _update(uid: int, metin: str = "/start") -> dict:
    return {
        "update_id": uid,
        "message": {
            "message_id": uid,
            "text": metin,
            "chat": {"id": 123456789},
            "from": {"id": 123456789},
        },
    }


# --- Tur başına iş sınırı ------------------------------------------------


def test_tur_azami_ile_fazla_update_bekletilir(monkeypatch):
    islenen_metinler: list[str] = []
    monkeypatch.setattr(tb, "handle_message", lambda m: islenen_metinler.append(m))
    updates = [_update(1000 + i) for i in range(50)]
    yeni_offset, islenen, reddedilen, kesinti = tb.updates_isle(updates, 1000, azami=20)
    assert islenen == 20, "tek turda en fazla 20 update işlenmeli"
    assert kesinti is False
    assert yeni_offset == 1020, "offset YALNIZ işlenen update kadar ilerlemeli"


def test_kalan_update_ler_kaybolmaz(monkeypatch):
    """Sınır sonrası kalanlar sonraki turda işlenir; offset bunu garanti eder."""
    islenen: list[str] = []
    monkeypatch.setattr(tb, "handle_message", lambda m: islenen.append(m))
    updates = [_update(2000 + i, f"m{i}") for i in range(5)]
    yeni_offset, _, _, _ = tb.updates_isle(updates, 2000, azami=2)
    assert yeni_offset == 2002
    kalanlar = [u for u in updates if u["update_id"] >= yeni_offset]
    tb.updates_isle(kalanlar, yeni_offset, azami=2)
    assert islenen == ["m0", "m1", "m2", "m3"]


def test_azami_sifir_sinirsiz_demektir(monkeypatch):
    islenen: list[str] = []
    monkeypatch.setattr(tb, "handle_message", lambda m: islenen.append(m))
    updates = [_update(3000 + i) for i in range(7)]
    tb.updates_isle(updates, 3000, azami=0)
    assert len(islenen) == 7


def test_tekrar_edilen_update_sinir_icinde_de_yutulur(monkeypatch):
    islenen: list[str] = []
    monkeypatch.setattr(tb, "handle_message", lambda m: islenen.append(m))
    ayni = _update(4000)
    tb.updates_isle([ayni, ayni], 4000, azami=10)
    assert len(islenen) == 1


# --- Workflow sözleşmesi -------------------------------------------------


def _poller_adimi() -> dict:
    d = yaml.safe_load(POLLER.read_text(encoding="utf-8"))
    for job in d["jobs"].values():
        for step in job["steps"]:
            if "PYEOF" in step.get("run", ""):
                return step
    raise AssertionError("poller adımı bulunamadı")


def test_workflow_tur_azami_env_ve_cagri_icerir():
    adim = _poller_adimi()
    assert "TELEGRAM_TUR_AZAMI" in (adim.get("env") or {})
    assert "azami=tur_azami" in adim["run"], "döngü sınırı çağrıya geçirilmeli"


def test_workflow_offset_kaybi_olmadan_ilerler():
    govde = _poller_adimi()["run"]
    assert "updates_isle(" in govde
    assert "offset = yeni_offset" in govde


# --- Tasarım notu --------------------------------------------------------


def test_tasarim_notu_var_ve_kararlari_yazar():
    metin = NOT.read_text(encoding="utf-8")
    assert "webhook" in metin.lower()
    assert "poller" in metin.lower()
    assert "24 saat" in metin, "Telegram penceresi yazılmalı"
    assert "Mini App" in metin


def test_tasarim_notu_uygulananlar_bolumu_kodla_uyusuyor():
    """Notta 'uygulandı' denen hafifletmeler gerçekten kodda olmalı."""
    metin = NOT.read_text(encoding="utf-8")
    assert "Panel temizliği" in metin and hasattr(tb, "eski_panelleri_sil")
    assert "Boşluk uyarısı" in metin and hasattr(tb, "bosuk_uyarisi_gonder")
    assert "Tekilleştirme" in metin and hasattr(tk, "tekrar_mi")
    assert "POLLER_TUR_AZAMI" in metin and hasattr(tb, "POLLER_TUR_AZAMI")
