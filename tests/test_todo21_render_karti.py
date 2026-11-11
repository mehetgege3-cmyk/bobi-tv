"""TODO 21 — Render testi CANLI kart: durum, süre, adım sayacı, yükleme yok.

Uydurma yüzde yasağı, "bilinmiyor" davranışı, bitmiş koşu, hata yolları ve
panel kuralları (≤3 buton/satır, ≤20 karakter etiket, Geri/Menü) test edilir.
"""
from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import modules.render_karti as rk  # noqa: E402
import modules.telegram_bot as tb  # noqa: E402

SIMDI = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)


def _kosu(**alanlar) -> dict:
    temel = {
        "id": 111,
        "run_number": 42,
        "status": "in_progress",
        "conclusion": None,
        "created_at": (SIMDI - timedelta(minutes=12)).isoformat(),
        "run_started_at": (SIMDI - timedelta(minutes=12)).isoformat(),
        "updated_at": (SIMDI - timedelta(minutes=1)).isoformat(),
        "html_url": "https://github.com/x/y/actions/runs/111",
    }
    temel.update(alanlar)
    return temel


@pytest.fixture(autouse=True)
def _ortam(monkeypatch, tmp_path):
    monkeypatch.setattr(tb, "CHAT_ID", "123456789")
    monkeypatch.setattr(tb, "BOT_TOKEN", "fake:token")
    monkeypatch.setattr(tb, "MENU_STATE_YOLU", tmp_path / "menu.json")
    monkeypatch.setattr(rk, "DURUM_YOLU", tmp_path / "render_test.json")
    tb._GITHUB_CACHE.clear()
    monkeypatch.setattr(tb, "_github_get_onbellekli", lambda yol: None)


# --- Süre / ilerleme -----------------------------------------------------


def test_suren_kosu_suresi_simdiye_gore():
    assert rk.gecen_sure_dk(_kosu(), SIMDI) == 12


def test_bitmis_kosu_suresi_start_updated_arasi():
    kosu = _kosu(
        status="completed",
        conclusion="success",
        run_started_at=(SIMDI - timedelta(minutes=20)).isoformat(),
        updated_at=(SIMDI - timedelta(minutes=8)).isoformat(),
    )
    assert rk.gecen_sure_dk(kosu, SIMDI) == 12


def test_tarih_yoksa_sure_bilinmiyor():
    assert rk.gecen_sure_dk({"status": "in_progress"}, SIMDI) is None
    assert "bilinmiyor" in rk.kart_metni({}, SIMDI)


def test_adim_bilgisi_yoksa_yuzde_uydurulmaz():
    il = rk.ilerleme({"steps": None})
    assert il["biliniyor"] is False and il["yuzde"] is None
    metin = rk.kart_metni(_kosu(), SIMDI)
    assert "yüzde uydurulmaz" in metin
    assert "%" not in metin.split("Adım:")[1].split("\n")[0]


def test_adim_bilgisi_varsa_yuzde_hesaplanir():
    adimlar = [
        {"status": "completed"},
        {"status": "completed"},
        {"status": "in_progress"},
        {"status": "queued"},
    ]
    il = rk.ilerleme({"steps": adimlar})
    assert il == {"biliniyor": True, "biten": 2, "toplam": 4, "yuzde": 50}
    metin = rk.kart_metni(_kosu(steps=adimlar), SIMDI)
    assert "2/4" in metin and "%50" in metin


# --- Durum metinleri -----------------------------------------------------


def test_durum_ve_sonuc_turkce():
    metin = rk.kart_metni(_kosu(), SIMDI)
    assert "🔄 Çalışıyor" in metin
    metin_ok = rk.kart_metni(_kosu(status="completed", conclusion="success"), SIMDI)
    assert "✅ Tamamlandı" in metin_ok and "✅ Başarılı" in metin_ok
    metin_hata = rk.kart_metni(_kosu(status="completed", conclusion="failure"), SIMDI)
    assert "❌ Başarısız" in metin_hata


def test_kart_her_durumda_yukleme_yapilmadigini_soyler():
    for kosu in (_kosu(), _kosu(status="completed", conclusion="success"), None):
        assert "yükleme yapılmadı" in rk.kart_metni(kosu, SIMDI).lower()


def test_kosu_yoksa_hata_sebebi_yazilir():
    metin = rk.kart_metni(None, SIMDI, hata="GitHub okunamadı")
    assert "GitHub okunamadı" in metin
    assert "bilinmiyor" not in metin.split("okunamadı")[0]


def test_canli_mi_bitmis_kosuda_false():
    assert rk.canli_mi(_kosu()) is True
    assert rk.canli_mi(_kosu(status="completed", conclusion="success")) is False
    assert rk.canli_mi(None) is False


def test_kosu_numarasi_gosterilir():
    assert "#42" in rk.kart_metni(_kosu(), SIMDI)


# --- Yerel durum dosyası -------------------------------------------------


def test_tetikleme_kaydi_yazilir_ve_okunur():
    veri = rk.tetikleme_kaydet(SIMDI)
    assert veri["yukleme_atla"] is True
    okunan = rk.durum_oku()
    assert okunan["tetiklendi"] == SIMDI.isoformat()
    assert okunan["durum"] == "tetiklendi"


def test_bozuk_durum_dosyasi_cokmez(tmp_path, monkeypatch):
    yol = tmp_path / "bozuk.json"
    yol.write_text("{değil", encoding="utf-8")
    assert rk.durum_oku(yol) == {}


def test_durum_yazilamazsa_false(monkeypatch, tmp_path):
    # Yazılamayan yol (dizin yerine dosya) → False, istisna fırlatmaz.
    engel = tmp_path / "engel"
    engel.write_text("x", encoding="utf-8")
    assert rk.durum_yaz({"a": 1}, engel / "alt" / "x.json") is False


# --- Panel entegrasyonu --------------------------------------------------


def test_ekran_kurallari():
    metin, butonlar = tb.ekran_render_kart()
    assert "Render testi" in metin
    for satir in butonlar:
        assert len(satir) <= 3
        for b in satir:
            assert len(b["text"]) <= 20
            assert len(b["callback_data"].encode()) <= 64
    duz = [b["callback_data"] for satir in butonlar for b in satir]
    assert "menu_main" in duz
    assert "render_kart" in duz, "yenile düğmesi yok"


def test_ekran_kosu_bulunamazsa_durust(monkeypatch):
    metin, _ = tb.ekran_render_kart()
    assert "okunamadı" in metin
    assert "yükleme yapılmadı" in metin.lower()


def test_ekran_kosuyu_bulunca_gosterir(monkeypatch):
    monkeypatch.setattr(
        tb,
        "_github_get_onbellekli",
        lambda yol: {"workflow_runs": [_kosu(display_title="render testi")]},
    )
    metin, _ = tb.ekran_render_kart()
    assert "🔄 Çalışıyor" in metin
    assert "#42" in metin


def test_yerel_kosu_id_one_cikar(monkeypatch):
    rk.tetikleme_kaydet(SIMDI, kosu_id=222)
    kosular = [_kosu(id=111), _kosu(id=222, run_number=77)]
    monkeypatch.setattr(tb, "_github_get_onbellekli", lambda yol: {"workflow_runs": kosular})
    metin, _ = tb.ekran_render_kart()
    assert "#77" in metin, "yerel kayıttaki koşu seçilmeli"


def test_callback_cevap_verir_ve_panel_gonderir(monkeypatch):
    cagrilar = []
    monkeypatch.setattr(tb, "answer_callback", lambda cb, metin="": cagrilar.append(("answer", cb)))
    monkeypatch.setattr(tb, "_ekran_goster", lambda demet: cagrilar.append(("ekran", demet[0])))
    tb.handle_callback("render_kart", "cb-9")
    assert ("answer", "cb-9") in cagrilar
    assert any(c[0] == "ekran" for c in cagrilar)


def test_uret_ekraninda_test_karti_dugmesi_var():
    _, butonlar = tb.ekran_uret()
    duz = [b["callback_data"] for satir in butonlar for b in satir]
    assert "render_kart" in duz


def test_render_testi_tetikleme_yerel_kayit_yazar(monkeypatch, tmp_path):
    class Yanit:
        status_code = 204
        text = ""

    monkeypatch.setenv("GH_TOKEN", "fake")
    monkeypatch.setattr("modules.telegram_bot.requests.post", lambda *a, **k: Yanit())
    monkeypatch.setattr(tb, "_ekran_goster", lambda demet: None)
    mesaj = tb.render_testi_tetikle()
    assert "yükleme yapılmadı" in mesaj
    assert "Canlı durum kartı" in mesaj
    kayit = json.loads((tmp_path / "render_test.json").read_text(encoding="utf-8"))
    assert kayit["yukleme_atla"] is True
