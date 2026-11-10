"""modules/telegram_bot.py güvenlik testleri — yetki kontrolü, PAT sızıntısı, sahte başarı."""
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Repo kökünü import yoluna ekle (tests/ altından çalıştırılırken)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import modules.telegram_bot as tb  # noqa: E402


@pytest.fixture(autouse=True)
def _chat_id(monkeypatch):
    monkeypatch.setattr(tb, "CHAT_ID", "123456789")
    monkeypatch.setattr(tb, "BOT_TOKEN", "fake:token")


# ---------- 1. Yetki kontrolü (en acil güvenlik açığı) ----------
def test_mesaj_izinli_sohbetten_kabul_edilir():
    update = {"update_id": 1, "message": {"chat": {"id": 123456789}, "text": "/start"}}
    assert tb.update_authorized(update) is True


def test_mesaj_yabanci_sohbetten_reddedilir():
    update = {"update_id": 2, "message": {"chat": {"id": 999999999}, "text": "/trigger"}}
    assert tb.update_authorized(update) is False


def test_callback_izinli_sohbetten_kabul_edilir():
    update = {"update_id": 3, "callback_query": {"id": "cb1", "data": "trigger_now",
              "message": {"chat": {"id": 123456789}}, "from": {"id": 123456789}}}
    assert tb.update_authorized(update) is True


def test_callback_yabanci_reddedilir():
    update = {"update_id": 4, "callback_query": {"id": "cb2", "data": "trigger_now",
              "message": {"chat": {"id": 111111111}}, "from": {"id": 111111111}}}
    assert tb.update_authorized(update) is False


def test_process_update_yabanciyi_islemez_ve_false_doner():
    update = {"update_id": 5, "message": {"chat": {"id": 999999999}, "text": "/trigger"}}
    with patch.object(tb, "handle_message") as hm:
        assert tb.process_update(update) is False
        hm.assert_not_called()


def test_coklu_chat_id_virgulle_desteklenir(monkeypatch):
    monkeypatch.setattr(tb, "CHAT_ID", "111,222, 333")
    assert tb.update_authorized({"message": {"chat": {"id": 222}}}) is True
    assert tb.update_authorized({"message": {"chat": {"id": 999}}}) is False


# ---------- 2+3. trigger_production: PAT argv'de değil, HTTP kodu zorunlu ----------
def test_trigger_token_yoksa_hata_doner(monkeypatch):
    monkeypatch.delenv("GH_TOKEN", raising=False)
    sonuc = tb.trigger_production()
    assert "❌" in sonuc
    assert "tetiklendi" not in sonuc


def test_trigger_204_basari_doner(monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "fake-pat")
    mock_resp = MagicMock(status_code=204, text="")
    with patch.object(tb.requests, "post", return_value=mock_resp) as mp:
        sonuc = tb.trigger_production()
    assert "✅" in sonuc
    # token header'da, argv'de DEĞİL — post çağrısı header içermeli
    _, kwargs = mp.call_args
    assert "Authorization" in kwargs["headers"]
    assert "fake-pat" in kwargs["headers"]["Authorization"]


def test_trigger_401_hatayi_belli_eder_sahte_basari_yok(monkeypatch):
    monkeypatch.setenv("GH_TOKEN", "fake-pat")
    mock_resp = MagicMock(status_code=401, text="Bad credentials")
    with patch.object(tb.requests, "post", return_value=mock_resp):
        sonuc = tb.trigger_production()
    assert "❌" in sonuc
    assert "401" in sonuc
    assert "tetiklendi" not in sonuc


def test_trigger_subprocess_kaldirilmis():
    """Güvenlik: subprocess modülü artık import edilmemeli (PAT argv sızıntısı)."""
    assert not hasattr(tb, "subprocess")


# ---------- 4. Saf fonksiyonlar ----------
def test_ana_menu_butonlari_yapisi():
    buttons = tb.get_main_menu_buttons()
    assert len(buttons) == 3
    callback_datalar = [b["callback_data"] for satir in buttons for b in satir]
    assert "trigger_now" in callback_datalar
    assert "status_now" in callback_datalar


def test_run_bot_entry_point_kaldirilmis():
    """Ölü tüketici noktası kaldırılmalı (çift getUpdates çakışması)."""
    assert not hasattr(tb, "run_bot")
