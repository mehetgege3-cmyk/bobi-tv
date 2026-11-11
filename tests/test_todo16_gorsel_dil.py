"""TODO 16 — Görsel dil: tek emoji sözlüğü, ilerleme çubuğu, sparkline,
renkli buton + API reddederse düz butona düşme."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import modules.telegram_bot as tb  # noqa: E402


@pytest.fixture(autouse=True)
def _ortam(monkeypatch, tmp_path):
    monkeypatch.setattr(tb, "CHAT_ID", "123456789")
    monkeypatch.setattr(tb, "BOT_TOKEN", "fake:token")
    monkeypatch.setattr(tb, "MENU_STATE_YOLU", tmp_path / "menu.json")


def test_emoji_sozlugu_tek_yerde():
    assert tb.EMOJI["tamam"] == "✅"
    assert tb.EMOJI["dikkat"] == "⚠️"
    assert tb.EMOJI["engel"] == "⛔"
    assert tb.EMOJI["test"] == "🧪"
    assert tb.EMOJI["sil"] == "🗑️"
    assert len(set(tb.EMOJI.values())) == len(tb.EMOJI), "aynı emoji iki anlama geliyor"


def test_ilerleme_cubugu_sinirlari():
    assert tb._ilerleme_cubugu(0) == "▱" * 6
    assert tb._ilerleme_cubugu(1) == "▰" * 6
    assert tb._ilerleme_cubugu(-5) == "▱" * 6
    assert tb._ilerleme_cubugu(9) == "▰" * 6


def test_sparkline_dogru_sekilde_olceklenir():
    s = tb._sparkline([0, 1, 2, 3])
    assert len(s) == 4
    assert s[0] == "▁" and s[-1] == "█"
    # artan seri monoton artmalı
    assert list(s) == sorted(s)


def test_sparkline_duz_seride_yaniltici_zirve_cizmez():
    assert tb._sparkline([3, 3, 3]) == "▄▄▄"


def test_sparkline_bos_listede_satir_duser():
    """Veri yoksa sparkline satırı HİÇ eklenmez (uydurma grafik çizilmez)."""
    assert tb._sparkline([]) == ""
    assert tb._sparkline([1.0]) == "▄"      # tek gün → tek karakter


def test_renkli_buton_renk_alani_tasir():
    b = tb.renkli_buton("✅ Evet", "uret_onay", "onay")
    assert b["style"] == "success"
    assert b["callback_data"] == "uret_onay"
    # renksiz tür: style alanı EKLENMEZ (API'yi gereksiz zorlamayız)
    assert "style" not in tb.renkli_buton("Vazgeç", "uret_menu", "vazgec")


def test_renk_reddedilirse_duz_butona_duser(monkeypatch):
    """KRİTİK: renk desteklenmeyen API'de panel ÇÖKMEZ, düz butonla devam eder."""
    denemeler = []

    def sahte_api(yontem, veri):
        denemeler.append(veri["reply_markup"]["inline_keyboard"])
        if len(denemeler) == 1:
            return {"ok": False, "description": "Bad Request: unknown field style"}
        return {"ok": True}

    monkeypatch.setattr(tb, "api_call", sahte_api)
    sonuc = tb.butonlari_renkle_gonder(
        "sendMessage", {"chat_id": "1", "text": "x"}, [[tb.renkli_buton("✅", "a", "onay")]]
    )
    assert sonuc and sonuc.get("ok"), "fallback sonrası gönderim başarısız"
    assert len(denemeler) == 2
    assert "style" in denemeler[0][0][0]
    assert "style" not in denemeler[1][0][0]


def test_diger_hatalarda_tekrar_denenmez(monkeypatch):
    """Sadece renk/parse hatasında tekrar denenir; diğer hatalar yutulmaz."""
    sayac = []
    monkeypatch.setattr(
        tb, "api_call",
        lambda y, v: sayac.append(1) or {"ok": False, "description": "chat not found"},
    )
    tb.butonlari_renkle_gonder("sendMessage", {"chat_id": "1", "text": "x"}, [[{"text": "a"}]])
    assert len(sayac) == 1
