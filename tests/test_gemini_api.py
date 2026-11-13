"""Gemini istemcisi — ağ olmadan mantık testleri (ölçüm: docs/GEMINI_ENTEGRASYON.md)."""

from modules import gemini_api


def test_anahtar_yoksa_gorsel_none(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert gemini_api.gorsel_uret("x", "/tmp/a.png") is None


def test_anahtar_yoksa_metin_none(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert gemini_api.metin_uret("x") is None


def test_bos_prompt_none():
    assert gemini_api.metin_uret("   ") is None
    assert gemini_api.gorsel_uret("", "/tmp/b.png") is None


def test_durum_anahtar_bildirir(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "AQ.test")
    d = gemini_api.durum()
    assert d["anahtar_var"] is True


def test_gorsel_adaylari_dolu():
    assert len(gemini_api.GORSEL_ADAYLARI) >= 2
    assert all(a.strip() for a in gemini_api.GORSEL_ADAYLARI)
