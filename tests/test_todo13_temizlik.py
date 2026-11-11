"""TODO 13 — Kod incelemesinde bulunan hatalar (Faz 0 / temizlik).

Her test bir maddeyi kilitler; ileride sessiz gerileme olmasın.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import modules.telegram_bot as tb  # noqa: E402


@pytest.fixture(autouse=True)
def _ortam(monkeypatch, tmp_path):
    monkeypatch.setattr(tb, "CHAT_ID", "123456789")
    monkeypatch.setattr(tb, "BOT_TOKEN", "fake:token")
    monkeypatch.setattr(tb, "MENU_STATE_YOLU", tmp_path / "menu.json")
    monkeypatch.setattr(tb, "COOLDOWN", tmp_path / "cooldown.json", raising=False)


# ---------- 1. _html_guvenli: izinli etiketler ----------

def test_html_guvenli_code_etiketini_korur():
    """`ekran_giris` içindeki `<code>60</code>` ekranda DÜZ METİN olarak
    görünüyordu (kaçırılıyordu). Artık korunmalı."""
    assert tb._html_guvenli("Sınır: <code>60</code>") == "Sınır: <code>60</code>"


def test_html_guvenli_izinli_etiketler_ve_guvenlik():
    cikti = tb._html_guvenli("<b>a</b> <i>b</i> <pre>c</pre> <script>x</script>")
    for etiket in ("<b>a</b>", "<i>b</i>", "<pre>c</pre>"):
        assert etiket in cikti
    assert "<script>" not in cikti, "izinli olmayan etiket kaçırılmalı"


def test_html_guvenli_ampersandi_tek_kez_kacirir():
    """Çift escape olmamalı: '&' → '&amp;', '&amp;' → '&amp;amp;' DEĞİL."""
    assert tb._html_guvenli("a & b") == "a &amp; b"


# ---------- 2. Tek escape noktası ----------

def test_send_message_da_escape_ediyor(monkeypatch):
    """send_message eskiden escape YAPMIYORDU (panel yapıyordu) → tutarsızdı."""
    yakalanan = {}

    def sahte_api(yontem, veri):
        yakalanan[yontem] = veri
        return {"ok": True, "result": {"message_id": 1}}

    monkeypatch.setattr(tb, "api_call", sahte_api)
    tb.send_message("<b>x</b> & <script>")
    assert yakalanan["sendMessage"]["text"] == "<b>x</b> &amp; &lt;script&gt;"


def test_help_metninde_elle_yazilmis_amp_yok():
    """get_help_text içinde elle `&amp;` vardı → panel_goster ile çift escape."""
    assert "&amp;" not in tb.get_help_text()


# ---------- 3. CALLBACK_DERINLIK sözleşmesi ----------

def test_callback_derinlik_eksik_anahtarlar_tamamlandi():
    d = tb.CALLBACK_DERINLIK
    for anahtar in ("ay:gir", "ay:onayd", "panelleri_temizle", "uret_onay"):
        assert anahtar in d, f"{anahtar} derinlik sözlüğünde yok"
    assert max(d.values()) <= 3


def test_tum_callbackler_derinlik_sozlugunde():
    """Buton üreten her callback_data bir derinlik değeri taşımalı."""
    _, butonlar = tb.ekran_ana()
    eksik = []
    for satir in butonlar:
        for b in satir:
            cd = b.get("callback_data")
            if cd and ":" not in cd and cd not in tb.CALLBACK_DERINLIK:
                eksik.append(cd)
    assert not eksik, f"derinlik tanımsız callback: {eksik}"


# ---------- 4. Tek sabit: repo / pipeline adı ----------

def test_repo_ve_pipeline_adi_tek_sabitten_gelir():
    assert tb.GITHUB_REPO.count("/") == 1
    assert tb.PIPELINE_SURUM in tb.get_status_text()
    # Kodu gezip sabit repo adı aramayalım: modül içinde tek yerden gelmeli
    kaynak = Path(tb.__file__).read_text(encoding="utf-8")
    assert kaynak.count("mehetgege3-cmyk/bobi-tv") <= 1, "repo adı birden çok yerde sabit"
    assert "v6.4 PRO" not in kaynak.split("PIPELINE_SURUM =")[1].split("\n", 2)[2]


# ---------- 5. Metin komutları panele yönlenir ----------

@pytest.mark.parametrize("komut", ["/status", "/stats", "/help"])
def test_metin_komutlari_panele_gider(monkeypatch, komut):
    yakalanan = []
    monkeypatch.setattr(tb, "panel_goster", lambda *a, **k: yakalanan.append(a) or True)
    monkeypatch.setattr(tb, "send_message", lambda *a, **k: yakalanan.append("SEND_MESSAGE"))
    tb.handle_message(komut)
    assert yakalanan, f"{komut} hiçbir cevap üretmedi"
    assert "SEND_MESSAGE" not in yakalanan, f"{komut} panel dışı mesaj attı"


# ---------- 6. Onay + cooldown ----------

def test_trigger_onaysiz_calismaz(monkeypatch, tmp_path):
    monkeypatch.setattr(tb, "_cooldown_dosyasi", lambda: tmp_path / "cd.json")
    tetiklendi = []
    monkeypatch.setattr(tb, "trigger_production", lambda: tetiklendi.append(1) or "✅ oldu")
    monkeypatch.setattr(tb, "panel_goster", lambda *a, **k: True)
    tb.handle_message("/trigger")
    assert tetiklendi == [], "onaysız üretim tetiklendi!"


def test_trigger_onay_ekrani_ve_evet_butonu_var(monkeypatch, tmp_path):
    monkeypatch.setattr(tb, "_cooldown_dosyasi", lambda: tmp_path / "cd.json")
    metin, butonlar = tb.ekran_uret_onay()
    assert "başlatmak üzeresin" in metin.lower() or "risk" in metin.lower()
    duz = [b["callback_data"] for satir in butonlar for b in satir]
    assert "uret_onay" in duz and "uret_menu" in duz


def test_cooldown_cift_tetiklemeyi_engeller(monkeypatch, tmp_path):
    cd = tmp_path / "cd.json"
    monkeypatch.setattr(tb, "_cooldown_dosyasi", lambda: cd)
    sayac = []
    monkeypatch.setattr(tb, "trigger_production", lambda: sayac.append(1) or "✅ tetiklendi")
    tb.trigger_production_kontrollu()
    tb.trigger_production_kontrollu()      # hemen ikinci kez
    assert len(sayac) == 1, "cooldown çift tetiklemeye izin verdi"


def test_cooldown_hatali_tetiklemede_baslamaz(monkeypatch, tmp_path):
    cd = tmp_path / "cd.json"
    monkeypatch.setattr(tb, "_cooldown_dosyasi", lambda: cd)
    monkeypatch.setattr(tb, "trigger_production", lambda: "❌ Hata: GH_TOKEN yok")
    tb.trigger_production_kontrollu()
    assert tb.uretim_cooldown_kalan() == 0, "hatalı tetikleme cooldown başlattı"
