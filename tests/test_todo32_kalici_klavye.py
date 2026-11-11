"""TODO 32 — Kalıcı alt klavye + modern ana kart (2026-11-11 kullanıcı isteği).

Kullanıcı: "Mini app istemiyorum. Biz menü sistemi ile devam edelim. Menüyü
güzelleştir. Bot başlayınca menüleri açık görünebilir, modern tasarım ve daha
kullanıcı dostu tasarla; bota girdiğimde her şey elimin altında olsun."

Sözleşme:
1. Kalıcı klavye payload'ı doğru (`is_persistent`, `resize_keyboard`, 6 düğme).
2. Klavye BİR KEZ kurulur (her /start'ta ekran mesajı birikmez).
3. Alt klavye düğme metni → doğru panel ekranı (emoji duyarsız eşleme).
4. Panel state yazımı mevcut alanları (özellikle `klavye_kuruldu`,
   `bekleyen_giris`) SİLMEZ.
5. Ana kart modern blok yapısında (Bugün / Sistem) ve veri kaybı yok.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import modules.telegram_bot as tb  # noqa: E402


@pytest.fixture(autouse=True)
def _ortam(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(tb, "CHAT_ID", "123456789")
    monkeypatch.setattr(tb, "BOT_TOKEN", "fake:token")
    monkeypatch.setattr(tb, "MENU_STATE_YOLU", tmp_path / "menu.json")
    monkeypatch.setattr(tb, "AYARLAR_STATE_YOLU", tmp_path / "ayarlar.json")
    monkeypatch.setattr(tb, "GECMIS_YOLU", tmp_path / "gecmis.jsonl")
    monkeypatch.setattr(tb, "KOTA_YOLU", tmp_path / "kota.json")
    monkeypatch.setattr(tb, "BEKLEYEN_YOLU", tmp_path / "bekleyen.json")


def _yakala(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Telegram çağrılarını (yöntem + payload) yakalar."""
    cagrilar: list[dict[str, Any]] = []

    def sahte_post(url: str, json: dict[str, Any] | None = None, timeout: float | None = None) -> Any:
        cagrilar.append({"yontem": str(url).rsplit("/", 1)[-1], "veri": json or {}})

        class R:
            status_code = 200

            def json(self) -> dict[str, Any]:
                return {"ok": True, "result": {"message_id": 777}}

        return R()

    monkeypatch.setattr("modules.telegram_bot.requests.post", sahte_post)
    return cagrilar


def _klavye_cagrilari(cagrilar: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        c for c in cagrilar
        if c["yontem"] == "sendMessage" and "keyboard" in (c["veri"].get("reply_markup") or {})
    ]


def _panel_cagrilari(cagrilar: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        c for c in cagrilar
        if c["yontem"] == "sendMessage"
        and "inline_keyboard" in (c["veri"].get("reply_markup") or {})
    ]


def test_kalici_klavye_payload_sozlesmesi(monkeypatch: pytest.MonkeyPatch) -> None:
    """Klavye kalıcı + yeniden boyutlanan + 6 düğme + ipucu metni."""
    cagrilar = _yakala(monkeypatch)
    tb.klavye_gonder()
    klavyeler = _klavye_cagrilari(cagrilar)
    assert len(klavyeler) == 1
    rm = klavyeler[0]["veri"]["reply_markup"]
    assert rm["is_persistent"] is True, "klavye kalıcı olmalı (sohbet açılınca görünür)"
    assert rm["resize_keyboard"] is True, "klavye küçültülmeli (ekranı kaplamasın)"
    assert rm.get("input_field_placeholder"), "yazı alanında yönlendirme metni olmalı"
    satirlar = rm["keyboard"]
    assert len(satirlar) == 3 and all(len(s) == 2 for s in satirlar)
    etiketler = [b["text"] for s in satirlar for b in s]
    assert len(etiketler) == 6
    # Her düğmede emoji var (kullanıcı dostu, göz ile hızlı seçim).
    assert all(any(not ch.isalnum() and not ch.isspace() for ch in e) for e in etiketler)


def test_klavye_bir_kez_kurulur(monkeypatch: pytest.MonkeyPatch) -> None:
    """3 × /start → kalıcı klavye TAM 1 kez; panel 1 kez doğar, sonra düzenlenir."""
    cagrilar = _yakala(monkeypatch)
    for _ in range(3):
        tb.handle_message("/start")
    assert len(_klavye_cagrilari(cagrilar)) == 1, "klavye yalnız bir kez gönderilmeli"
    assert len(_panel_cagrilari(cagrilar)) == 1, "3 /start → tek panel"


def test_klavye_gizle_kaldirir(monkeypatch: pytest.MonkeyPatch) -> None:
    cagrilar = _yakala(monkeypatch)
    tb.klavye_gizle()
    # remove_keyboard taşıyan mesaj da reply_markup içinde "keyboard" anahtarı
    # olmadan gider → hepsini görmek için sendMessage'lara bak.
    gizleme = [
        c for c in cagrilar
        if c["yontem"] == "sendMessage"
        and c["veri"].get("reply_markup", {}).get("remove_keyboard") is True
    ]
    assert len(gizleme) == 1


@pytest.mark.parametrize(
    ("duz_metin", "beklenen_ekran"),
    [
        ("durum", "status_now"),
        ("üret", "uret_menu"),
        ("rapor", "rapor_goster"),
        ("ayarlar", "ay:kok"),
        ("stok", "kuyruk_liste"),
        ("yardım", "yardim_goster"),
    ],
)
def test_alt_klavye_metni_dogru_ekrani_acar(
    monkeypatch: pytest.MonkeyPatch, duz_metin: str, beklenen_ekran: str
) -> None:
    """Alt klavyeden gelen düz metin, ilgili panel ekranına yönlenir."""
    cagrilar = _yakala(monkeypatch)
    tb.handle_message("/start")
    cagrilar.clear()
    assert tb.REPLY_ESLEME[duz_metin] == beklenen_ekran
    tb.handle_message(duz_metin)
    assert cagrilar, "klavye metni en az bir panel çağrısı üretmeli"
    # Ekran panel içinde açılır: yeni mesaj yığmak yerine düzenleme tercih edilir.
    assert any(c["yontem"] in {"editMessageText", "sendMessage"} for c in cagrilar)
    assert not _klavye_cagrilari(cagrilar), "ikinci kez klavye gönderilmemeli"


def test_emoji_duyarli_klavye_metni_de_eslesir(monkeypatch: pytest.MonkeyPatch) -> None:
    """Düğme metni emojisiyle gönderilse de `_duz_metin` eşlemeyi bulur."""
    assert tb._duz_metin("📊 Durum") == "durum"
    assert tb._duz_metin("⚙️ Ayarlar") == "ayarlar"
    assert tb._duz_metin("  RAPOR  ") == "rapor"


def test_panel_yaz_mevcut_alanlari_korur(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """`_panel_yaz` sözlüğü sıfırdan yazmaz: bayrak ve bekleyen giriş korunur."""
    yol = tmp_path / "menu.json"
    monkeypatch.setattr(tb, "MENU_STATE_YOLU", yol)
    yol.write_text(
        json.dumps({"klavye_kuruldu": True, "bekleyen_giris": "GUNLUK_HEDEF", "ozel": 5}),
        encoding="utf-8",
    )
    tb._panel_yaz(4242)
    veri = json.loads(yol.read_text(encoding="utf-8"))
    assert veri["message_id"] == 4242
    assert veri["klavye_kuruldu"] is True, "klavye bayrağı silinmemeli"
    assert veri["bekleyen_giris"] == "GUNLUK_HEDEF", "giriş bekleyen alan korunmalı"
    assert veri["ozel"] == 5


def test_ana_kart_modern_blok_yapisi() -> None:
    """Ana kart: başlık + ayırıcı + Bugün/Sistem blokları + sparkline; veri kaybı yok."""
    metin, butonlar = tb.ekran_ana()
    assert "BOBİ TV" in metin
    assert "─" in metin, "blok ayırıcı çizgi olmalı"
    for parca in ("Bugün", "üretim", "yayında", "Stok", "Kanal", "Sistem", "Son koşu", "Bot"):
        assert parca in metin, f"ana kartta '{parca}' eksik"
    # Veri kaybı yok: 7 günlük trend satırı hâlâ var.
    assert "7 gün" in metin
    # Kart, panel kuralına uy: 4096 karakter sınırı.
    assert len(metin) < 2000
