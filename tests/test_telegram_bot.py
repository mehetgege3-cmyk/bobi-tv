"""modules/telegram_bot.py güvenlik testleri — yetki kontrolü, PAT sızıntısı, sahte başarı."""

import json
import sys
from pathlib import Path
from typing import Any
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
    update = {
        "update_id": 3,
        "callback_query": {
            "id": "cb1",
            "data": "trigger_now",
            "message": {"chat": {"id": 123456789}},
            "from": {"id": 123456789},
        },
    }
    assert tb.update_authorized(update) is True


def test_callback_yabanci_reddedilir():
    update = {
        "update_id": 4,
        "callback_query": {
            "id": "cb2",
            "data": "trigger_now",
            "message": {"chat": {"id": 111111111}},
            "from": {"id": 111111111},
        },
    }
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
    """TODO 3: ana menü 6 düğmeden 4'e iner (2 satır). İstatistik + Kalite +
    Kota 'Rapor' altına girer; Ayarlar kendi düğmesini alır."""
    buttons = tb.get_main_menu_buttons()
    assert len(buttons) == 2
    callback_datalar = [b["callback_data"] for satir in buttons for b in satir]
    assert len(callback_datalar) == 4, f"4 düğme beklenir, gelen: {callback_datalar}"
    assert "status_now" in callback_datalar
    assert "uret_menu" in callback_datalar
    assert "rapor_goster" in callback_datalar
    assert "ay:kok" in callback_datalar


def test_run_bot_entry_point_kaldirilmis():
    """Ölü tüketici noktası kaldırılmalı (çift getUpdates çakışması)."""
    assert not hasattr(tb, "run_bot")


def test_panel_html_escape_veri_alanlari_ama_b_etiketi_korunur(monkeypatch):
    """TODO6: panel metnindeki & < > escape edilir ama <b></b> etiketleri korunur."""
    import modules.telegram_bot as tb

    monkeypatch.setattr(tb, "BOT_TOKEN", "fake:token")
    monkeypatch.setattr(tb, "CHAT_ID", "12345")
    yakalanan = {}

    def sahte_post(url, json=None, timeout=None):
        yakalanan.update(json or {})

        class R:
            status_code = 200

            def json(self):
                return {"ok": True}

        return R()

    monkeypatch.setattr(tb.requests, "post", sahte_post)
    tb.send_message_with_buttons("Merhaba & <b>dünya</b> < 5", [[{"text": "x", "callback_data": "y"}]])
    gonderilen = yakalanan["text"]
    assert "&amp;" in gonderilen  # & escape edildi
    assert "&lt; 5" in gonderilen  # tek başına < escape edildi
    assert "<b>dünya</b>" in gonderilen  # <b> etiketi korundu
    assert "&lt;b&gt;" not in gonderilen  # escape edilmiş <b> kalmamalı


# ---------- 5. Menü spam'i düzeltmeleri (TODO 2) ----------
def _telegram_yakalayici() -> tuple[list[tuple[str, dict[str, Any]]], Any]:
    """requests.post'u yakalar; (yöntem, payload) listesi döndürür.
    Her çağrı için ok:true + message_id:777 yanıtı verir."""
    cagrilar: list[tuple[str, dict[str, Any]]] = []

    def sahte_post(url: str, json: dict[str, Any] | None = None, timeout: float | None = None) -> Any:
        yontem = str(url).rsplit("/", 1)[-1]
        cagrilar.append((yontem, json or {}))

        class R:
            status_code = 200

            def json(self) -> dict[str, Any]:
                return {"ok": True, "result": {"message_id": 777}}

        return R()

    return cagrilar, sahte_post


def test_taninmayan_metin_cevap_vermez(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tanınmayan metin → 0 mesaj (yalnızca log). Ekran görüntüsündeki
    '3 menü alt alta' spam'inin kök nedeni buydu."""
    cagrilar, sahte_post = _telegram_yakalayici()
    monkeypatch.setattr("modules.telegram_bot.requests.post", sahte_post)
    tb.handle_message("selam naber nasılsın")
    assert cagrilar == [], "Tanınmayan metne mesaj gönderilmemeli"


def test_menu_komutu_tek_menyu_gonderir_ve_id_saklanir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    menu_yolu = tmp_path / "menu.json"
    monkeypatch.setattr(tb, "MENU_STATE_YOLU", menu_yolu)
    cagrilar, sahte_post = _telegram_yakalayici()
    monkeypatch.setattr("modules.telegram_bot.requests.post", sahte_post)
    tb.handle_message("/menu")
    assert sum(1 for yontem, _ in cagrilar if yontem == "sendMessage") == 1
    saklanan = json.loads(menu_yolu.read_text(encoding="utf-8"))
    assert saklanan["message_id"] == 777
    assert saklanan["chat_id"] == "123456789"


def test_uc_ust_uste_menyu_toplam_bir_mesaj(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """3 × /start → TAM 1 panel + 2 düzenleme (ekranda tek menü).

    2026-11-11 düzeltmesi: önceki sözleşme "her /start yeni panel" idi ve
    kullanıcının şikâyeti olan "üst üste menüler"i bizzat üretiyordu.
    Poller geciktiğinde biriken /start'lar toplu işlenir (kanıt: tek koşuda
    5 × "/start"); bu yüzden tekrar eden /start panel ÇOĞALTMAZ.
    """
    monkeypatch.setattr(tb, "MENU_STATE_YOLU", tmp_path / "menu.json")
    cagrilar, sahte_post = _telegram_yakalayici()
    monkeypatch.setattr("modules.telegram_bot.requests.post", sahte_post)
    for _ in range(3):
        tb.handle_message("/start")
    yeni_menuler = sum(1 for yontem, _ in cagrilar if yontem == "sendMessage")
    guncellemeler = sum(1 for yontem, _ in cagrilar if yontem == "editMessageText")
    eski_yol = sum(1 for yontem, _ in cagrilar if yontem == "editMessageReplyMarkup")
    assert yeni_menuler == 1, f"3 /start tek panel olmalı, gelen: {yeni_menuler}"
    assert guncellemeler == 2, f"sonraki 2 /start düzenlemeli, gelen: {guncellemeler}"
    assert eski_yol == 0


def test_bayat_menu_silinmisse_yeni_menyu_acilir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """TODO 4: saklanan panel mesajı Telegram'da silinmişse (edit 404) bayat kayıt
    düşülür ve tek yeni panel açılır (editMessageText yolu)."""
    menu_yolu = tmp_path / "menu.json"
    monkeypatch.setattr(tb, "MENU_STATE_YOLU", menu_yolu)
    cagrilar: list[str] = []

    def sahte_post(url: str, json: dict[str, Any] | None = None, timeout: float | None = None) -> Any:
        yontem = str(url).rsplit("/", 1)[-1]
        cagrilar.append(yontem)

        class R:
            status_code = 200

            def json(self) -> dict[str, Any]:
                if yontem == "editMessageText":
                    return {"ok": False, "description": "Bad Request: message to edit not found"}
                return {"ok": True, "result": {"message_id": 888}}

        return R()

    monkeypatch.setattr("modules.telegram_bot.requests.post", sahte_post)
    tb.handle_message("/menu")  # ilk menü → sendMessage
    tb.handle_message("/menu")  # bayat id → edit bulunamadı → yeni menü
    assert cagrilar == ["sendMessage", "editMessageText", "sendMessage"]
    assert json.loads(menu_yolu.read_text(encoding="utf-8"))["message_id"] == 888


def test_komut_cevabi_duz_mesajdir_butonsuz(monkeypatch: pytest.MonkeyPatch) -> None:
    """Menü dışı komut cevapları reply_markup İÇERMEZ (butonlar sadece ana menüde)."""
    cagrilar, sahte_post = _telegram_yakalayici()
    monkeypatch.setattr("modules.telegram_bot.requests.post", sahte_post)
    tb.handle_message("/status")
    cevaplar = [payload for yontem, payload in cagrilar if yontem == "sendMessage"]
    assert len(cevaplar) == 1
    assert "reply_markup" not in cevaplar[0]


def test_menu_main_callback_yeni_menyu_spamlamaz(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """'🏠 Menü' butonu tekrar tekrar basılsa bile yeni menü mesajı açılmaz."""
    monkeypatch.setattr(tb, "MENU_STATE_YOLU", tmp_path / "menu.json")
    cagrilar, sahte_post = _telegram_yakalayici()
    monkeypatch.setattr("modules.telegram_bot.requests.post", sahte_post)
    tb.handle_callback("menu_main", "cb1")
    tb.handle_callback("menu_main", "cb2")
    assert sum(1 for yontem, _ in cagrilar if yontem == "sendMessage") == 1
