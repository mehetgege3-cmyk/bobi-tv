"""Gemini WEB istemcisi — ağ olmadan mantık testleri.
Canlı kanıt: kanit/gemini/web_elma.png (286×512, 27.690 bayt, 2026-11-13)."""

from modules import gemini_web


def test_cerez_yoksa_none(monkeypatch):
    monkeypatch.delenv("GEMINI_COOKIES", raising=False)
    assert gemini_web.cerez() == ""
    assert gemini_web.hazir_mi() is False
    assert gemini_web.gorsel_uret("elma", "/tmp/x.png") is None


def test_cerez_json_dizisi_de_okunur(monkeypatch):
    monkeypatch.setenv(
        "GEMINI_COOKIES",
        '[{"name":"__Secure-1PSID","value":"A"},{"name":"NID","value":"2"}]',
    )
    c = gemini_web.cerez()
    assert "__Secure-1PSID=A" in c and "NID=2" in c
    assert gemini_web.hazir_mi() is True


def test_cerez_baslik_metni_aynen_gecer(monkeypatch):
    monkeypatch.setenv("GEMINI_COOKIES", "__Secure-1PSID=X; __Secure-1PSIDTS=Y")
    assert gemini_web.cerez() == "__Secure-1PSID=X; __Secure-1PSIDTS=Y"
    assert gemini_web.hazir_mi() is True


def test_1psid_yoksa_hazir_degil(monkeypatch):
    monkeypatch.setenv("GEMINI_COOKIES", "NID=2; SID=3")
    assert gemini_web.hazir_mi() is False


def test_bos_prompt_none(monkeypatch):
    monkeypatch.setenv("GEMINI_COOKIES", "__Secure-1PSID=X")
    assert gemini_web.gorsel_uret("   ", "/tmp/y.png") is None


def test_govde_yapisi_dogru():
    """f.req = [None, "<81 öğeli json>"] olmalı (gemini_webapi 2.1.1 ile aynı)."""
    import json as _j

    govde, uid = gemini_web._govde("deneme", "AT123")
    metin = govde.decode()
    assert "at=AT123" in metin and "f.req=" in metin
    from urllib.parse import parse_qs

    f_req = parse_qs(metin)["f.req"][0]
    dis = _j.loads(f_req)
    assert isinstance(dis, list) and len(dis) == 2 and dis[0] is None
    ic = _j.loads(dis[1])
    assert len(ic) == 81
    assert ic[0][0] == "deneme"
    assert ic[1] == ["tr"]
    assert ic[7] == 1 and ic[79] == 1
    assert ic[59] == uid
