"""TODO 29 — Callback/update tekilleştirme: aynı iş iki kez başlamasın.

Senaryo: poller yeniden başlar, Telegram aynı update'i tekrar teslim eder;
veya kullanıcı düğmeye iki kez hızlı basar. Sonuç iki üretim tetiklemesi olabilir.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import modules.tekillestirme as tk  # noqa: E402
import modules.telegram_bot as tb  # noqa: E402


@pytest.fixture(autouse=True)
def _ortam(monkeypatch, tmp_path):
    monkeypatch.setattr(tb, "CHAT_ID", "123456789")
    monkeypatch.setattr(tb, "BOT_TOKEN", "fake:token")
    monkeypatch.setattr(tb, "MENU_STATE_YOLU", tmp_path / "menu.json")
    tk.sifirla()
    return tmp_path


def _update(uid: int = 100) -> dict:
    # Yetkili sohbet bilgisi şart: process_update önce yetki kontrolü yapar.
    return {
        "update_id": uid,
        "message": {
            "message_id": 5,
            "text": "/start",
            "chat": {"id": 123456789},
            "from": {"id": 123456789},
        },
    }


# --- Anahtar üretimi ----------------------------------------------------


def test_anahtar_update_id_ile():
    assert tk.anahtar(_update(42)) == "u:42"


def test_anahtar_update_id_yoksa_callback_id():
    assert tk.anahtar({"callback_query": {"id": "cb-7"}}) == "c:cb-7"


def test_anahtar_mesaj_id_yedegi():
    assert tk.anahtar({"message": {"message_id": 9}}) == "m:9"


def test_anahtar_yoksa_bos():
    assert tk.anahtar({}) == ""
    assert tk.anahtar(None) == ""


# --- Tekrar tespiti -----------------------------------------------------


def test_ilk_gelis_tekrar_degil_ikinci_gelis_tekrar():
    assert tk.tekrar_mi(_update(), simdi=1000.0) is False
    assert tk.tekrar_mi(_update(), simdi=1001.0) is True
    assert tk.gorulme_sayisi(_update()) == 2


def test_ttl_dolunca_yeniden_islenir():
    assert tk.tekrar_mi(_update(), simdi=1000.0) is False
    assert tk.tekrar_mi(_update(), simdi=1000.0 + tk.TTL_SN + 1) is False


def test_farkli_update_tekrar_sayilmaz():
    assert tk.tekrar_mi(_update(1), simdi=1000.0) is False
    assert tk.tekrar_mi(_update(2), simdi=1001.0) is False


def test_anahtarsiz_update_yutulmaz():
    """update_id yoksa tekilleştirme uygulanmaz — mesaj kaybı riski alınmaz."""
    assert tk.tekrar_mi({}, simdi=1000.0) is False
    assert tk.tekrar_mi({}, simdi=1001.0) is False


def test_bellek_sinirsiz_buyumez(monkeypatch):
    monkeypatch.setattr(tk, "AZAMI_KAYIT", 5)
    for i in range(20):
        tk.tekrar_mi(_update(i), simdi=1000.0 + i)
    assert len(tk._GORULEN) <= 5


def test_bayat_kayitlar_temizlenir():
    tk.tekrar_mi(_update(1), simdi=1000.0)
    tk.tekrar_mi(_update(2), simdi=1000.0 + tk.TTL_SN + 5)
    assert "u:1" not in tk._GORULEN


# --- Uçuş kilidi (aynı eylemi iki kez başlatma) -------------------------


def test_ucus_kilidi_ikinci_istegi_reddeder():
    assert tk.ucusa_izin("uret", simdi=1000.0) is True
    assert tk.ucusa_izin("uret", simdi=1001.0) is False
    assert tk.ucusta_mi("uret", simdi=1001.0) is True


def test_ucus_kilidi_ttl_sonunda_acilir():
    assert tk.ucusa_izin("uret", simdi=1000.0) is True
    assert tk.ucusa_izin("uret", simdi=1000.0 + tk.UCUS_TTL_SN + 1) is True


def test_ucustan_cikarinca_yeniden_izin():
    tk.ucusa_izin("sil", simdi=1000.0)
    tk.ucustan_cikar("sil")
    assert tk.ucusa_izin("sil", simdi=1001.0) is True


def test_farkli_eylemler_birbirini_kilitlemez():
    assert tk.ucusa_izin("a", simdi=1000.0) is True
    assert tk.ucusa_izin("b", simdi=1000.0) is True


# --- process_update entegrasyonu ---------------------------------------


def test_ayni_update_iki_kez_islenmez(monkeypatch):
    cagrilar = []
    monkeypatch.setattr(tb, "handle_message", lambda metin: cagrilar.append(metin))
    assert tb.process_update(_update(500)) is True
    assert tb.process_update(_update(500)) is True  # yutulur ama True döner
    assert len(cagrilar) == 1, "mesaj iki kez işlenmemeli"


def test_tekrar_yutuldugunda_loglanir(monkeypatch, capsys):
    monkeypatch.setattr(tb, "handle_message", lambda metin: None)
    tb.process_update(_update(501))
    tb.process_update(_update(501))
    cikti = capsys.readouterr().out
    assert "Tekrar eden update yutuldu" in cikti, "sessiz yutma yasak"


def test_farkli_updateler_ikisi_de_islenir(monkeypatch):
    cagrilar = []
    monkeypatch.setattr(tb, "handle_message", lambda metin: cagrilar.append(metin))
    tb.process_update(_update(600))
    tb.process_update(_update(601))
    assert len(cagrilar) == 2


def test_tekrar_callback_ikinci_kez_calismaz(monkeypatch):
    """Aynı callback update'i tekrar gelirse panel/tetikleme ikinci kez dönmez."""
    sayac = []
    monkeypatch.setattr(tb, "handle_callback", lambda *a, **k: sayac.append(1))
    update = {"update_id": 700, "callback_query": {"id": "cb-1", "data": "menu_main",
             "message": {"chat": {"id": 123456789}}, "from": {"id": 123456789}}}
    tb.process_update(update)
    tb.process_update(update)
    assert len(sayac) == 1
