"""TODO 3 — Telegram offset güvenliği testleri.

Kapsam: updates_isle offset semantiği (istisnada ilerletmeme, sıralı yeniden
deneme), red kararının tüketim sayılması ve boşluk uyarısı gövdesi.
"""

from __future__ import annotations

from typing import Any

import pytest

import modules.telegram_bot as tb

CHAT_ID = 123456789


def _mesaj(update_id: int, text: str = "/menu") -> dict[str, Any]:
    return {"update_id": update_id, "message": {"chat": {"id": CHAT_ID}, "text": text}}


def test_basariyla_islenen_update_offset_ilertir(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tb, "process_update", lambda u: True)
    yeni, islenen, reddedilen, kesinti = tb.updates_isle([_mesaj(100), _mesaj(101)], 100)
    assert yeni == 102
    assert islenen == 2
    assert reddedilen == 0
    assert kesinti is False


def test_istisna_offset_ilertmez_ve_dongu_durar(monkeypatch: pytest.MonkeyPatch) -> None:
    """process_update çökerse offset o update'ten ÖNCE kalır — mesaj kaybolmaz."""

    def patlayan(update: dict[str, Any]) -> bool:
        raise RuntimeError("handler patladı")

    monkeypatch.setattr(tb, "process_update", patlayan)
    yeni, islenen, reddedilen, kesinti = tb.updates_isle([_mesaj(100), _mesaj(101)], 100)
    assert yeni == 100
    assert islenen == 0
    assert reddedilen == 0
    assert kesinti is True


def test_karisik_yigin_kesintide_guvenli_kalir(monkeypatch: pytest.MonkeyPatch) -> None:
    """İlk update başarılı, ikinci patlar → offset ikinciden önce kalır ve
    üçüncü update DENENMEZ (sıra korunur, bir sonraki koşuda tekrar gelir)."""
    cagrilar: list[int] = []

    def sahte(update: dict[str, Any]) -> bool:
        cagrilar.append(update["update_id"])
        if update["update_id"] == 101:
            raise RuntimeError("pat")
        return True

    monkeypatch.setattr(tb, "process_update", sahte)
    yeni, islenen, reddedilen, kesinti = tb.updates_isle([_mesaj(100), _mesaj(101), _mesaj(102)], 100)
    assert yeni == 101
    assert islenen == 1
    assert reddedilen == 0
    assert kesinti is True
    assert cagrilar == [100, 101]


def test_reddedilen_update_tuketilir_offset_ilertir(monkeypatch: pytest.MonkeyPatch) -> None:
    """Yetkisiz mesaj (False) bilinçli red kararıdır ve tüketilir; aksi halde
    aynı yetkisiz mesaj her koşuda sonsuza dek yeniden gelirdi."""
    monkeypatch.setattr(tb, "process_update", lambda u: False)
    yeni, islenen, reddedilen, kesinti = tb.updates_isle([_mesaj(200)], 200)
    assert yeni == 201
    assert islenen == 0
    assert reddedilen == 1
    assert kesinti is False


def test_bosuk_uyarisi_govdesi_sure_ve_sayiyi_icerir(monkeypatch: pytest.MonkeyPatch) -> None:
    yakalanan: list[str] = []

    def sahte_send(metin: str, parse_mode: str = "HTML") -> bool:
        yakalanan.append(metin)
        return True

    monkeypatch.setattr(tb, "send_message", sahte_send)
    assert tb.bosuk_uyarisi_gonder(7, None) is True
    assert "7 güncelleme" in yakalanan[0]
    assert "bilinmeyen süre" in yakalanan[0]
    assert "Mesaj kaybı" in yakalanan[0]
