"""TODO 33 — Menüde gezinme bütünlüğü (2026-11-11 kullanıcı geri bildirimi).

Kullanıcı haklı olarak kızdı: "dalga geçiyorsun galiba". Ölçülen gerçek
sorunlar:
1. Rapor ekranı üç ayrı metin bloğunu üst üste yığıyordu (kaydırmadan hiçbir
   şey okunmuyordu).
2. Raporun altındaki ekranların (7 gün / performans / sistem / bildirim /
   denetim / mini app) panelde GEZİNME YOLU yoktu — metinlerden "başka ekran"
   diye bahsediliyordu, düğme yoktu.
3. "← Geri" ile "🏠 Menü" aynı yere dönüyordu (ikisi de ana kart).

Bu dosya o hataların geri gelmemesini ölçer: ana karttan her ekrana yol VAR,
"Geri" gerçekten bir üst ekrana döner, hiyerarşi döngüsüzdür.
"""

from __future__ import annotations

import sys
from collections import deque
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import modules.telegram_bot as tb  # noqa: E402
from modules.ayar_katalogu import tumu  # noqa: E402


@pytest.fixture(autouse=True)
def _ortam(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(tb, "CHAT_ID", "123456789")
    monkeypatch.setattr(tb, "BOT_TOKEN", "fake:token")
    monkeypatch.setattr(tb, "MENU_STATE_YOLU", tmp_path / "menu.json")
    monkeypatch.setattr(tb, "AYARLAR_STATE_YOLU", tmp_path / "ayarlar.json")
    monkeypatch.setattr(tb, "GECMIS_YOLU", tmp_path / "gecmis.jsonl")
    monkeypatch.setattr(tb, "KOTA_YOLU", tmp_path / "kota.json")
    monkeypatch.setattr(tb, "BEKLEYEN_YOLU", tmp_path / "bekleyen.json")


def _ekranlar() -> dict[str, Any]:
    """Menüde gezinilebilen ekranlar: callback → ekran üreticisi.

    `sistem_goster` bilinçli olarak YOK: "Sistem" şemsiye ekranı (sistem_kok)
    onun yerini aldı; eski callback yalnız geriye dönük uyum için duruyor.
    """
    return {
        "menu_main": tb.ekran_ana,
        "rapor_goster": tb.ekran_rapor,
        "uret_menu": tb.ekran_uret,
        "status_now": tb.ekran_durum,
        "sistem_kok": tb.ekran_sistem_kok,
        "rapor_7gun": tb.ekran_7gun,
        "performans": tb.ekran_performans,
        "kuyruk_liste": tb.ekran_kuyruk,
        "render_kart": tb.ekran_render_kart,
        "denetim_goster": tb.ekran_denetim,
        "bildirim_goster": tb.ekran_bildirim,
        "mini_app_goster": tb.ekran_mini_app,
        "yardim_goster": tb.ekran_yardim,
        "ay:kok": tb.ekran_ayar_kok,
        "ay:hizli": tb.ekran_hizli_ayarlar,
        "ay:gecmis": tb.ekran_gecmis,
    }


def _butonlar(ekran_uretici) -> list[str]:
    _, butonlar = ekran_uretici()
    return [b["callback_data"] for satir in butonlar for b in satir if "callback_data" in b]


def test_ana_karttan_her_ekrana_yol_var() -> None:
    """BFS: ana karttan başlayıp düğmeleri izleyerek her ekrana ulaşılabilmeli.

    "Her şey elimin altında" iddiasının ölçüsü budur: ulaşılamayan ekran,
    kullanıcı için YOK demektir.
    """
    ekranlar = _ekranlar()
    gorulen: set[str] = set()
    kuyruk: deque[str] = deque(["menu_main"])
    while kuyruk:
        cb = kuyruk.popleft()
        if cb in gorulen:
            continue
        uretici = ekranlar.get(cb)
        if uretici is None:
            continue  # aksiyon düğmesi (üretimi başlat vb.) — ekran değil
        gorulen.add(cb)
        for hedef in _butonlar(uretici):
            if hedef in ekranlar and hedef not in gorulen:
                kuyruk.append(hedef)

    ulasilamayan = set(ekranlar) - gorulen
    assert not ulasilamayan, f"panelde gezinti yolu olmayan ekranlar: {sorted(ulasilamayan)}"


def test_ayar_gruplari_ve_ayarlar_gezilebilir() -> None:
    """Ayarlar kökünden her gruba, her gruptan her ayarın detayına yol var."""
    _, kok = tb.ekran_ayar_kok()
    kok_cb = [b["callback_data"] for satir in kok for b in satir if "callback_data" in b]
    for grup in tb.GRUPLAR:
        assert f"ay:g:{grup}" in kok_cb, f"ayarlar kökünde '{grup}' grubuna düğme yok"

    for grup in tb.GRUPLAR:
        _, butonlar = tb.ekran_ayar_grup(grup)
        grup_cb = [b["callback_data"] for satir in butonlar for b in satir if "callback_data" in b]
        for a in tumu():
            if a["grup"] == grup:
                assert f"ay:s:{a['anahtar']}" in grup_cb, (
                    f"'{grup}' grubunda '{a['anahtar']}' ayarına düğme yok"
                )


def test_geri_bir_ust_ekrana_doner() -> None:
    """"← Geri" hedefi: her ekranın BİR ÜSTÜ (ana kart olmayanlar ana karta değil)."""
    assert tb.ekran_ust("rapor_7gun") == "rapor_goster"
    assert tb.ekran_ust("kuyruk_liste") == "rapor_goster"
    assert tb.ekran_ust("rapor_goster") == "menu_main"
    assert tb.ekran_ust("render_kart") == "uret_menu"
    assert tb.ekran_ust("bildirim_goster") == "sistem_kok"
    assert tb.ekran_ust("ay:hizli") == "ay:kok"
    assert tb.ekran_ust("menu_main") == "menu_main"
    # Dinamik ayar callback'i → ayarın grubu
    ilk = tumu()[0]
    assert tb.ekran_ust(f"ay:s:{ilk['anahtar']}") == f"ay:g:{ilk['grup']}"


def test_hiyerarsi_dongusuz_ve_kok_ana_kart() -> None:
    """EKRAN_UST zinciri en fazla 3 adımda ana karta ulaşır (döngü yok)."""
    for baslangic in tb.EKRAN_UST:
        cb = baslangic
        for _ in range(6):
            ust = tb.ekran_ust(cb)
            if ust == "menu_main":
                break
            assert ust != cb, f"kendine geri dönen ekran: {cb}"
            cb = ust
        else:
            raise AssertionError(f"{baslangic} → ana karta ulaşamadı (zincir kopuk)")
        assert tb.ekran_ust("menu_main") == "menu_main"


def test_hicbir_ekran_dugmesiz_degil() -> None:
    """Her ekranda en az 2 düğme ve DAİMA ana karta dönüş düğmesi olmalı."""
    for ad, uretici in _ekranlar().items():
        if ad == "menu_main":
            continue  # ana kartın kendisi; dönüş düğmesi beklemez
        _, butonlar = uretici()
        cb = [b["callback_data"] for satir in butonlar for b in satir if "callback_data" in b]
        assert cb, f"{ad} ekranında hiç düğme yok (çıkmaz sokak)"
        # Ana karta dönüş: ya menu_main ya da "geri" (üst ekran) var.
        assert "menu_main" in cb or "geri" in cb, f"{ad} ekranından geri dönüş yok"


def test_panel_kurallari_butun_ekranlarda() -> None:
    """Telegram sınırları: satırda ≤3 düğme, etiket ≤20 karakter, callback ≤64 bayt."""
    for ad, uretici in _ekranlar().items():
        metin, butonlar = uretici()
        assert len(metin) <= 4096, f"{ad}: metin 4096 karakteri aşıyor"
        for satir in butonlar:
            assert len(satir) <= 3, f"{ad}: satırda 3'ten fazla düğme"
            for b in satir:
                assert len(b["text"]) <= 20, f"{ad}: etiket çok uzun: {b['text']}"
                if "callback_data" in b:
                    assert len(b["callback_data"].encode()) <= 64, f"{ad}: callback > 64 bayt"


def test_rapor_karti_kaydirma_gerektirmez() -> None:
    """Rapor kartı kısa: telefon ekranında kaydırmadan okunur (SATIR sayısı)."""
    metin, _ = tb.ekran_rapor()
    assert len(metin.splitlines()) <= 16, "rapor kartı çok uzun — eski yığılmış hâle döndü"
    # Üç bölüm de korunur (veri kaybı yok).
    for parca in ("Üretim", "Kalite", "Trend"):
        assert parca in metin
