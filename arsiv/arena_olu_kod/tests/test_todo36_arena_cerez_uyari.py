"""TODO dosyası madde 3 (Seçenek C) — çerez düşünce Telegram uyarısı testleri.

Kurallar:
- Yalnız oturum/çerez hatalarında uyarı çıkar;
- 30 dakikada bir defadan sık tekrar etmez (spam yok);
- Susturma açıksa gönderilmez;
- Metinde çerez/token YOK, yalnız verdict + zaman + adımlar.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import modules.arena_cerez_uyari as u  # noqa: E402

SIMDI = datetime(2026, 11, 11, 10, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _izole(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(u, "STATE", tmp_path / "uyari.json")


def test_yalniz_oturum_hatalarinda_uyarir() -> None:
    assert u.uyari_gerekli_mi("oturum-gecersiz", SIMDI)[0] is True
    assert u.uyari_gerekli_mi("cookie-yapilandirma-hatasi", SIMDI)[0] is True
    for verdict in ("basarili", "selector-bulunamadi", "cevap-algilamadi", ""):
        assert u.uyari_gerekli_mi(verdict, SIMDI)[0] is False


def test_30_dakikada_bir_tekrar() -> None:
    gonderilen: list[str] = []
    r1 = u.uyari_gonder("oturum-gecersiz", SIMDI, gonderici=lambda m: gonderilen.append(m) or True)
    assert r1["gonderildi"] is True
    # 10 dk sonra: spam yok
    r2 = u.uyari_gonder(
        "oturum-gecersiz", SIMDI + timedelta(minutes=10), gonderici=lambda m: gonderilen.append(m) or True
    )
    assert r2["gonderildi"] is False and "tekrar aralığı" in r2["sebep"]
    # 31 dk sonra: tekrar hatırlatma
    r3 = u.uyari_gonder(
        "oturum-gecersiz", SIMDI + timedelta(minutes=31), gonderici=lambda m: gonderilen.append(m) or True
    )
    assert r3["gonderildi"] is True
    assert len(gonderilen) == 2


def test_verdict_degisirse_hemen_uyarir() -> None:
    u.uyari_gonder("oturum-gecersiz", SIMDI, gonderici=lambda m: True)
    r = u.uyari_gonder(
        "cookie-yapilandirma-hatasi", SIMDI + timedelta(minutes=2), gonderici=lambda m: True
    )
    assert r["gonderildi"] is True


def test_gonderim_hatasi_damga_yazmaz() -> None:
    r = u.uyari_gonder("oturum-gecersiz", SIMDI, gonderici=lambda m: False)
    assert r["gonderildi"] is False
    assert json.loads(u.STATE.read_text(encoding="utf-8")) if u.STATE.exists() else {} == {}
    assert u.uyari_gerekli_mi("oturum-gecersiz", SIMDI + timedelta(minutes=1))[0] is True


def test_metinde_sir_yok() -> None:
    metin = u.uyari_metni("oturum-gecersiz", SIMDI)
    assert "oturum-gecersiz" in metin
    assert "ARENA_COOKIES_JSON" in metin  # secret'ın ADI geçer, değeri değil
    for yasak in ("arena-auth-prod-v1", "Cookie:", "Bearer ", "ghp_"):
        assert yasak not in metin
    assert "2026-11-11 10:00" in metin


def test_susturma_saygi_gorur(monkeypatch: pytest.MonkeyPatch) -> None:
    import modules.bildirim as b

    monkeypatch.setattr(b, "susturulmus_mu", lambda simdi=None: True)
    r = u.uyari_gonder("oturum-gecersiz", SIMDI, gonderici=lambda m: True)
    assert r["gonderildi"] is False
    assert "susturulmuş" in r["sebep"]
