"""TODO 31 v2 — Mini App YAZMA modu (onaylı, token'sız).

Mimari: Mini App → `Telegram.WebApp.sendData` → bot `web_app_data` →
doğrulama → var olan ONAY ekranı → imzalı callback → denetim kaydı.

Testler üç şeyi kilitler:
1. Beyaz liste + payload doğrulama (bilinmeyen eylem REDDEDİLİR),
2. Hiçbir istek onaysız çalışmaz (üretim, stok boşaltma),
3. Reddedilen istek sessizce yutulmaz (kullanıcı "YAPILMADI" görür).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import modules.denetim as dn  # noqa: E402
import modules.mini_app_eylem as me  # noqa: E402
import modules.telegram_bot as tb  # noqa: E402


@pytest.fixture(autouse=True)
def _ortam(monkeypatch, tmp_path):
    monkeypatch.setattr(tb, "CHAT_ID", "123456789")
    monkeypatch.setattr(tb, "BOT_TOKEN", "fake:token")
    monkeypatch.setattr(tb, "MENU_STATE_YOLU", tmp_path / "menu.json")
    monkeypatch.setattr(dn, "DENETIM_YOLU", tmp_path / "denetim.jsonl")
    return tmp_path


def _paneller(monkeypatch) -> list[str]:
    metinler: list[str] = []
    monkeypatch.setattr(tb, "panel_goster", lambda metin, dugmeler=None: metinler.append(metin))
    return metinler


# --- Payload doğrulama ---------------------------------------------------


def test_beyaz_liste_eylemleri():
    assert me.eylem_listesi() == ["denetim", "durum", "kuyruk_bosalt", "render_test", "uret"]


def test_gecerli_payload_cozulur():
    kayit, sebep = me.payload_coz(me.payload_uret("uret"))
    assert sebep == ""
    assert kayit["eylem"] == "uret"
    assert kayit["onay_gerekli"] is True
    assert kayit["callback"] == "uret_baslat"


def test_bilinmeyen_eylem_reddedilir():
    kayit, sebep = me.payload_coz(json.dumps({"e": "kanal_sil", "v": 1}))
    assert kayit is None
    assert "bilinmeyen eylem" in sebep


def test_bos_payload_reddedilir():
    assert me.payload_coz("")[0] is None
    assert me.payload_coz("   ")[1] == "boş payload"
    assert me.payload_coz(None)[1] == "boş payload"


def test_bozuk_json_reddedilir():
    kayit, sebep = me.payload_coz("{bu json değil")
    assert kayit is None and sebep == "payload JSON değil"


def test_asiri_buyuk_payload_reddedilir():
    buyuk = json.dumps({"e": "uret", "v": 1, "x": "A" * (me.AZAMI_PAYLOAD + 10)})
    kayit, sebep = me.payload_coz(buyuk)
    assert kayit is None
    assert "çok büyük" in sebep


def test_surum_uyumsuzlugu_reddedilir():
    kayit, sebep = me.payload_coz(json.dumps({"e": "uret", "v": 99}))
    assert kayit is None and "sürüm" in sebep


def test_sozluk_payload_da_kabul_edilir():
    kayit, _ = me.payload_coz({"e": "durum", "v": me.SURUM})
    assert kayit["eylem"] == "durum"


def test_sozluk_olmayan_payload_reddedilir():
    assert me.payload_coz([1, 2, 3])[0] is None
    assert me.payload_coz(42)[0] is None


def test_bilinmeyen_eylemde_onay_gerekli_guvenli_taraf():
    assert me.onay_gerekli("olmayan") is True


def test_yazma_eylemleri_onay_ister():
    for eylem in ("uret", "render_test", "kuyruk_bosalt"):
        assert me.onay_gerekli(eylem) is True
    for eylem in ("durum", "denetim"):
        assert me.onay_gerekli(eylem) is False


# --- Bot tarafı: onay akışı ---------------------------------------------


def test_uret_istegi_onay_ekrani_acar_ve_calistirmaz(monkeypatch):
    paneller = _paneller(monkeypatch)
    tetiklendi = []
    monkeypatch.setattr(tb, "trigger_production", lambda: tetiklendi.append(1) or "✅")
    sonuc = tb.handle_web_app_data({"data": me.payload_uret("uret")})
    assert sonuc == "onay"
    assert tetiklendi == [], "onay olmadan üretim BAŞLAMAMALI"
    assert "Mini App'ten gelen istek" in paneller[-1]
    assert "onay" in paneller[-1].lower()


def test_stok_bosaltma_istegi_onay_ekrani_acar(monkeypatch, tmp_path):
    """Stok doluysa ONAY ekranı; boşsa dürüst 'Atılacak kayıt yok' (yalan yok)."""
    paneller = _paneller(monkeypatch)
    import modules.kuyruk_yonetimi as ky

    kuyruk = tmp_path / "queue"
    kuyruk.mkdir()
    monkeypatch.setattr(ky, "KUYRUK_DIZINI", kuyruk)
    monkeypatch.setattr(ky, "ATILAN_DIZINI", tmp_path / "atilan")
    (kuyruk / "v1.json").write_text(
        '{"dosya_adi": "v1", "baslik": "Test", "stok_sebep": "kota"}', encoding="utf-8"
    )

    sonuc = tb.handle_web_app_data({"data": me.payload_uret("kuyruk_bosalt")})
    assert sonuc == "onay"
    assert "ONAY" in paneller[-1]
    assert (kuyruk / "v1.json").exists(), "onay ekranı dosyaya DOKUNMAMALI"


def test_stok_bosaltma_bos_kuyrukta_durust(monkeypatch, tmp_path):
    paneller = _paneller(monkeypatch)
    import modules.kuyruk_yonetimi as ky

    monkeypatch.setattr(ky, "KUYRUK_DIZINI", tmp_path / "yok")
    monkeypatch.setattr(ky, "ATILAN_DIZINI", tmp_path / "atilan")
    tb.handle_web_app_data({"data": me.payload_uret("kuyruk_bosalt")})
    assert "Atılacak kayıt yok" in paneller[-1]


def test_render_testi_istegi_calistirmaz_onay_ekrani_acar(monkeypatch):
    paneller = _paneller(monkeypatch)
    tetik = []
    monkeypatch.setattr(tb, "render_testi_tetikle", lambda: tetik.append(1) or "x")
    sonuc = tb.handle_web_app_data({"data": me.payload_uret("render_test")})
    assert sonuc == "onay"
    assert tetik == []
    assert "Render testi" in paneller[-1]


def test_durum_istegi_salt_okuma(monkeypatch):
    paneller = _paneller(monkeypatch)
    assert tb.handle_web_app_data({"data": me.payload_uret("durum")}) == "goster"
    assert "BOBİ TV" in paneller[-1]


def test_denetim_istegi_salt_okuma(monkeypatch):
    paneller = _paneller(monkeypatch)
    assert tb.handle_web_app_data({"data": me.payload_uret("denetim")}) == "goster"
    assert "Denetim" in paneller[-1]


def test_reddedilen_istek_yalan_soylemez(monkeypatch):
    paneller = _paneller(monkeypatch)
    sonuc = tb.handle_web_app_data({"data": "bozuk"})
    assert sonuc == "red"
    assert "uygulanmadı" in paneller[-1]
    assert "Hiçbir işlem başlatılmadı" in paneller[-1]


def test_niyet_denetime_yazilir(monkeypatch):
    _paneller(monkeypatch)
    tb.handle_web_app_data({"data": me.payload_uret("uret")})
    kayit = next(k for k in dn.son_kayitlar(5) if k["olay"] == "mini_app_niyet")
    assert kayit["ayrinti"]["eylem"] == "uret"
    assert kayit["sonuc"] == "onay_bekliyor"


def test_red_denetime_yazilir(monkeypatch):
    _paneller(monkeypatch)
    tb.handle_web_app_data({"data": "{}"})
    assert any(k["olay"] == "mini_app_red" for k in dn.son_kayitlar(5))


def test_web_app_data_process_update_icinde_oncelikli(monkeypatch):
    """web_app_data varsa metin işlenmez: tek yol, karışıklık yok."""
    cagrilar = []
    monkeypatch.setattr(tb, "handle_web_app_data", lambda v: cagrilar.append("app"))
    monkeypatch.setattr(tb, "handle_message", lambda m: cagrilar.append("msg"))
    update = {
        "update_id": 4242,
        "message": {
            "message_id": 1,
            "chat": {"id": 123456789},
            "from": {"id": 123456789},
            "web_app_data": {"data": me.payload_uret("uret")},
            "text": "/start",
        },
    }
    tb.process_update(update)
    assert cagrilar == ["app"]


def test_web_app_data_yoksa_normal_mesaj_islenir(monkeypatch):
    cagrilar = []
    monkeypatch.setattr(tb, "handle_web_app_data", lambda v: cagrilar.append("app"))
    monkeypatch.setattr(tb, "handle_message", lambda m: cagrilar.append("msg"))
    tb.process_update(
        {
            "update_id": 4243,
            "message": {
                "message_id": 2,
                "chat": {"id": 123456789},
                "from": {"id": 123456789},
                "text": "/start",
            },
        }
    )
    assert cagrilar == ["msg"]


def test_payload_token_icermez():
    """Botun ürettiği payload yalnız eylem + sürüm taşır."""
    for eylem in me.eylem_listesi():
        veri = json.loads(me.payload_uret(eylem))
        assert set(veri) == {"e", "v"}
        assert len(me.payload_uret(eylem)) < 60
