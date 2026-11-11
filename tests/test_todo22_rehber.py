"""TODO 22 — "Ne işe yarıyor?" rehberi: ayar etkisi, zamanlaması, ETKİSİZLİĞİ.

Kurallar test edilir: uydurma açıklama yok, secret değeri sızmaz, tavan iddiası
yok (kota kaldırıldı), ekran ≈15 satır, panel buton kuralları.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import modules.rehber as rh  # noqa: E402
import modules.telegram_bot as tb  # noqa: E402


@pytest.fixture(autouse=True)
def _ortam(monkeypatch, tmp_path):
    monkeypatch.setattr(tb, "CHAT_ID", "123456789")
    monkeypatch.setattr(tb, "BOT_TOKEN", "fake:token")
    monkeypatch.setattr(tb, "MENU_STATE_YOLU", tmp_path / "menu.json")


# --- Kapsam -------------------------------------------------------------


def test_katalogdaki_her_ayarin_rehberi_var():
    """Eksik açıklama = kullanıcının cevapsız sorusu; test eksikleri listeler."""
    eksik = rh.rehbersiz_ayarlar()
    assert eksik == [], f"rehberi olmayan ayarlar: {eksik}"


def test_rehbersiz_ayar_uydurmaz():
    g = rh.rehber_girdisi("OLMAYAN_AYAR")
    assert rh.BILINMIYOR in g["ne"]
    assert g["zaman"] == rh.BILINMIYOR


def test_her_girdi_uc_alan_dolu():
    for anahtar in rh.butun_anahtarlar():
        g = rh.REHBER[anahtar]
        assert g["ne"].strip() and g["zaman"].strip() and g["degil"].strip(), anahtar


# --- İçerik dürüstlüğü --------------------------------------------------


def test_kota_tavani_iddiasi_yok():
    """2026-11-11: tavan kaldırıldı — rehber 'günde 6' gibi iddia yazamaz."""
    for anahtar in rh.butun_anahtarlar():
        metin = rh.detay_metni(anahtar).lower()
        assert "günde 6" not in metin
        assert "tavan 6" not in metin


def test_kadans_girdisi_tavan_olmadigini_soyler():
    metin = rh.detay_metni("KADANS_DK")
    assert "tavan" in metin.lower()
    assert "cron" in metin.lower(), "cron uyarısı kaybolmamalı"


def test_silme_ayarlari_geri_alinamaz_uyarisi_tasir():
    for anahtar in ("OTOMATIK_SIL_AKTIF", "MIN_IZLENME_ESIGI"):
        assert "GERİ ALINAMAZ" in rh.detay_metni(anahtar)


def test_sistem_metni_uctan_uca_akis_ve_sinirlar():
    metin = rh.sistem_metni()
    for parca in ("Konu seçer", "Senaryo", "TTS", "Render", "YÜKLER"):
        assert parca in metin
    assert "YOK" in metin, "tavan yok bilgisi yazılmalı"
    assert "403" in metin, "tek gerçek engel (YouTube kotası) yazılmalı"


def test_sistem_metni_15_satiri_gecmez():
    assert len([s for s in rh.sistem_metni().split("\n") if s.strip()]) <= 15


# --- Secret güvenliği ---------------------------------------------------


def test_secret_ayarlarda_deger_gosterilmez(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:GIZLI-deger")
    metin = rh.detay_metni("TELEGRAM_BOT_TOKEN")
    assert "GIZLI" not in metin
    assert rh.secret_durumu("TELEGRAM_BOT_TOKEN") == "✅ tanımlı"


def test_secret_yoksa_eksik_der(monkeypatch):
    monkeypatch.delenv("GH_TOKEN", raising=False)
    assert rh.secret_durumu("GH_TOKEN") == "⛔ eksik"


# --- Grup / panel metinleri --------------------------------------------


@pytest.mark.parametrize("grup", ["tetikleme", "uretim_kota", "temizlik", "bildirim"])
def test_grup_metni_her_ayari_tek_satirda_anlatir(grup):
    metin = rh.grup_metni(grup)
    assert "ne işe yarıyor" in metin.lower()
    assert len([s for s in metin.split("\n") if s.strip()]) <= 15


def test_detay_metni_uc_soruyu_yanitlar():
    metin = rh.detay_metni("MIN_IZLENME_ESIGI", "Min izlenme eşiği")
    assert "Ne yapar" in metin
    assert "Ne zaman etkili" in metin
    assert "Neyi değiştirmez" in metin


# --- Panel entegrasyonu -------------------------------------------------


def test_ayar_detayinda_nedir_dugmesi_var():
    metin, butonlar = tb.ekran_ayar_detay("KADANS_DK")
    duz = [b["callback_data"] for satir in butonlar for b in satir if "callback_data" in b]
    assert "ay:nedir:KADANS_DK" in duz


def test_nedir_ekrani_kurallari():
    metin, butonlar = tb.ekran_ayar_nedir("KADANS_DK")
    assert "KADANS" not in metin  # teknik anahtar değil, etiket gösterilir
    assert "Üretim kadansı" in metin
    for satir in butonlar:
        assert len(satir) <= 3
        for b in satir:
            assert len(b["text"]) <= 20
            assert len(b["callback_data"].encode()) <= 64
    duz = [b["callback_data"] for satir in butonlar for b in satir if "callback_data" in b]
    assert "menu_main" in duz
    assert len([s for s in metin.split("\n") if s.strip()]) <= 15


def test_nedir_bilinmeyen_ayarda_ana_ekrana_doner():
    metin, butonlar = tb.ekran_ayar_nedir("YOK_BOYLE_AYAR")
    assert "BOBİ TV" in metin  # ekran_ana


def test_sistem_nedir_ekrani():
    metin, butonlar = tb.ekran_sistem_nedir()
    assert "Bu sistem ne işe yarıyor" in metin
    duz = [b["callback_data"] for satir in butonlar for b in satir if "callback_data" in b]
    assert {"menu_main", "kuyruk_liste"} <= set(duz)


def test_callback_ay_nedir_yonlendirir(monkeypatch):
    cagrilar = []
    monkeypatch.setattr(tb, "answer_callback", lambda cb, metin="": cagrilar.append(("answer", cb)))
    monkeypatch.setattr(tb, "_ekran_goster", lambda demet: cagrilar.append(("ekran", demet[0])))
    tb.handle_callback("ay:nedir:MIN_IZLENME_ESIGI", "cb-1")
    assert ("answer", "cb-1") in cagrilar
    ekran = [c[1] for c in cagrilar if c[0] == "ekran"][-1]
    assert "Ne yapar" in ekran


def test_callback_bilinmeyen_ayarda_sessiz_kalmaz(monkeypatch):
    cagrilar = []
    monkeypatch.setattr(tb, "answer_callback", lambda cb, metin="": cagrilar.append(("answer", cb)))
    monkeypatch.setattr(tb, "_ekran_goster", lambda demet: cagrilar.append(("ekran", demet[0])))
    tb.handle_callback("ay:nedir:YOK", "cb-2")
    assert cagrilar, "bilinmeyen ayarda da kullanıcıya cevap verilmeli"


def test_yardim_ekraninda_sistem_nedir_dugmesi():
    _, butonlar = tb.ekran_yardim()
    # web_app düğmelerinde callback_data YOK (Telegram kuralı) — filtrele.
    duz = [b["callback_data"] for satir in butonlar for b in satir if "callback_data" in b]
    assert "sistem_nedir" in duz
    # 2026-11-11: kullanıcı "Mini App istemiyorum" dedi → yardım ekranında
    # Mini App açılış düğmesi YOK. (Mini App ekranı panelden hâlâ erişilebilir.)
    web = [b for satir in butonlar for b in satir if "web_app" in b]
    assert web == [], "yardım ekranında Mini App düğmesi olmamalı"
