"""TODO 26 + 27 — 10 dk cool-off + iptal ve DENETİM KAYDI.

Kurallar: yanlış tetikleme 10 dk içinde iptal edilebilir (yalan vaat yok:
render alınmışsa video stoğa gider), geri alınamaz her işlem denetim kaydına
yazılır ve kayıtta secret/token BULUNMAZ.
"""
from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import modules.denetim as dn  # noqa: E402
import modules.telegram_bot as tb  # noqa: E402

SIMDI = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _ortam(monkeypatch, tmp_path):
    monkeypatch.setattr(tb, "CHAT_ID", "123456789")
    monkeypatch.setattr(tb, "BOT_TOKEN", "fake:token")
    monkeypatch.setattr(tb, "MENU_STATE_YOLU", tmp_path / "menu.json")
    monkeypatch.setenv("BOBI_IPTAL_YOLU", str(tmp_path / "iptal.json"))
    monkeypatch.setenv("BOBI_COOLDOWN_YOLU", str(tmp_path / "cooldown.json"))
    monkeypatch.setattr(dn, "DENETIM_YOLU", tmp_path / "denetim.jsonl")
    return tmp_path


# --- Denetim modülü ------------------------------------------------------


def test_kayit_yazilir_ve_okunur():
    assert dn.kaydet("video_sil", "ok", kullanici_id=42, ayrinti={"video_id": "abc"}, simdi=SIMDI)
    k = dn.son_kayitlar(5)
    assert len(k) == 1
    assert k[0]["olay"] == "video_sil"
    assert k[0]["kullanici_id"] == 42
    assert k[0]["ayrinti"]["video_id"] == "abc"
    assert k[0]["zaman"].startswith("2026-11-11T12:00")


def test_ayrintidaki_secret_maskelenir():
    dn.kaydet(
        "ayar_degistir",
        "ok",
        ayrinti={
            "anahtar": "MIN_IZLENME_ESIGI",
            "TELEGRAM_BOT_TOKEN": "123:GIZLI",
            "nested": {"client_secret": "shh", "cookie_jar": "x", "normal": "görünür"},
        },
        simdi=SIMDI,
    )
    satir = (dn.DENETIM_YOLU).read_text(encoding="utf-8")
    assert "GIZLI" not in satir and "shh" not in satir
    kayit = dn.son_kayitlar(1)[0]
    assert kayit["ayrinti"]["TELEGRAM_BOT_TOKEN"] == dn.MASKE
    assert kayit["ayrinti"]["nested"]["normal"] == "görünür"


def test_en_yeni_once_okunur():
    for i in range(3):
        dn.kaydet("olay", "ok", ayrinti={"i": i}, simdi=SIMDI)
    kayitlar = dn.son_kayitlar(3)
    assert [k["ayrinti"]["i"] for k in kayitlar] == [2, 1, 0]


def test_bozuk_satir_atlanir_sayilir():
    dn.kaydet("olay", "ok", simdi=SIMDI)
    with dn.DENETIM_YOLU.open("a", encoding="utf-8") as f:
        f.write("{bozuk json\n")
    veri = dn.oku(10)
    assert len(veri["kayitlar"]) == 1
    assert veri["bozuk"] == 1
    assert "bozuk satır" in dn.panel_metni(10)


def test_dosya_yoksa_cokmez():
    veri = dn.oku(5)
    assert veri == {"kayitlar": [], "bozuk": 0, "var": False}
    assert "Kayıt yok" in dn.panel_metni(5)


def test_yazilamayan_yol_false_doner(tmp_path):
    engel = tmp_path / "engel"
    engel.write_text("x", encoding="utf-8")
    assert dn.kaydet("olay", yol=engel / "alt" / "x.jsonl") is False


def test_dosya_dondurulur(monkeypatch, tmp_path):
    monkeypatch.setattr(dn, "AZAMI_SATIR", 3)
    yol = tmp_path / "d.jsonl"
    for i in range(5):
        dn.kaydet("olay", "ok", ayrinti={"i": i}, yol=yol)
    assert yol.exists()
    assert (tmp_path / "d.jsonl.1").exists(), "eşik aşılınca tek yedek alınmalı"


def test_ozet_olay_sayimi():
    dn.kaydet("video_sil", simdi=SIMDI)
    dn.kaydet("video_sil", simdi=SIMDI)
    dn.kaydet("uretim_tetikle", simdi=SIMDI)
    o = dn.ozet()
    assert o["olay_sayimi"]["video_sil"] == 2
    assert o["toplam"] == 3


def test_geri_alinamaz_olaylar_kumesi_dolu():
    for olay in ("video_sil", "stok_at", "uretim_tetikle"):
        assert olay in dn.GERI_ALINAMAZ_OLAYLAR


def test_panel_metni_15_satiri_gecmez():
    for i in range(30):
        dn.kaydet("olay", "ok", ayrinti={"i": i}, simdi=SIMDI)
    metin = dn.panel_metni(8)
    assert len([s for s in metin.split("\n") if s.strip()]) <= 15


# --- Tetikleme → denetim + iptal penceresi ------------------------------


def test_basarili_tetikleme_denetime_yazilir(monkeypatch):
    monkeypatch.setattr(tb, "uretim_cooldown_kalan", lambda: 0)
    monkeypatch.setattr(tb, "trigger_production", lambda: "✅ Üretim tetiklendi")
    monkeypatch.setattr(tb, "uretim_cooldown_baslat", lambda: None)
    mesaj = tb.trigger_production_kontrollu()
    assert "tetiklendi" in mesaj.lower()
    kayitlar = dn.son_kayitlar(5)
    assert any(k["olay"] == "uretim_tetikle" and k["sonuc"] == "ok" for k in kayitlar)
    assert tb.iptal_kalan_sn() > 0, "iptal penceresi açılmalı"


def test_basarisiz_tetikleme_de_denetime_yazilir(monkeypatch):
    monkeypatch.setattr(tb, "uretim_cooldown_kalan", lambda: 0)
    monkeypatch.setattr(tb, "trigger_production", lambda: "❌ Hata: token yok")
    tb.trigger_production_kontrollu()
    kayitlar = dn.son_kayitlar(5)
    assert any(k["sonuc"] == "basarisiz" for k in kayitlar)
    assert tb.iptal_kalan_sn() == 0, "başarısız tetiklemede iptal penceresi açılmaz"


def test_cooldown_engellediginde_denetim_yok(monkeypatch):
    monkeypatch.setattr(tb, "uretim_cooldown_kalan", lambda: 30)
    tb.trigger_production_kontrollu()
    assert dn.son_kayitlar(5) == []


# --- İptal --------------------------------------------------------------


def test_iptal_penceresi_icinde_iptal_edilir():
    tb._iptal_penceresi_baslat()
    ok, mesaj = tb.uretim_iptal_et()
    assert ok is True
    assert "İptal kaydedildi" in mesaj
    assert "KAYBOLMAZ" in mesaj, "render alınmışsa stoğa gider — dürüst uyarı"
    assert any(k["olay"] == "uretim_iptal" for k in dn.son_kayitlar(5))


def test_pencere_kapandiysa_iptal_reddedilir():
    ok, mesaj = tb.uretim_iptal_et()
    assert ok is False
    assert "pencere kapandı" in mesaj.lower() or "İptal penceresi kapandı" in mesaj


def test_pencere_dolunca_kalan_sifir():
    tb._iptal_penceresi_baslat(simdi=1000.0)
    assert tb.iptal_kalan_sn(simdi=1000.0) == tb.IPTAL_PENCERESI_SN
    assert tb.iptal_kalan_sn(simdi=1000.0 + tb.IPTAL_PENCERESI_SN + 1) == 0


def test_bozuk_iptal_dosyasi_cokmez(tmp_path, monkeypatch):
    (tmp_path / "iptal.json").write_text("{değil", encoding="utf-8")
    assert tb.iptal_kalan_sn() == 0


def test_uretim_ekraninda_iptal_dugmesi_pencere_acikken():
    tb._iptal_penceresi_baslat()
    _, butonlar = tb.ekran_uret()
    duz = [b["callback_data"] for satir in butonlar for b in satir]
    assert "uret_iptal" in duz
    for satir in butonlar:
        assert len(satir) <= 3
        for b in satir:
            assert len(b["text"]) <= 20


def test_uretim_ekraninda_iptal_dugmesi_pencere_kapaliyken_yok():
    _, butonlar = tb.ekran_uret()
    duz = [b["callback_data"] for satir in butonlar for b in satir]
    assert "uret_iptal" not in duz


def test_iptal_callback_cevap_verir(monkeypatch):
    cagrilar = []
    monkeypatch.setattr(tb, "answer_callback", lambda cb, metin="": cagrilar.append(metin))
    monkeypatch.setattr(tb, "_ekran_goster", lambda demet: None)
    tb.handle_callback("uret_iptal", "cb-1")
    assert cagrilar


# --- Denetim ekranı -----------------------------------------------------


def test_denetim_ekrani_ve_kurallari():
    dn.kaydet("uretim_tetikle", "ok", simdi=SIMDI)
    metin, butonlar = tb.ekran_denetim()
    assert "Denetim Kaydı" in metin
    assert "uretim_tetikle" in metin
    for satir in butonlar:
        assert len(satir) <= 3
        for b in satir:
            assert len(b["text"]) <= 20
    duz = [b["callback_data"] for satir in butonlar for b in satir]
    assert {"menu_main", "denetim_goster"} <= set(duz)


def test_denetim_ekrani_secret_gostermez(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "999:COKGIZLI")
    dn.kaydet("ayar_degistir", ayrinti={"TELEGRAM_BOT_TOKEN": "999:COKGIZLI"}, simdi=SIMDI)
    metin, _ = tb.ekran_denetim()
    assert "COKGIZLI" not in metin


def test_denetim_callback_yonlendirmesi(monkeypatch):
    cagrilar = []
    monkeypatch.setattr(tb, "answer_callback", lambda cb, metin="": cagrilar.append(("answer", cb)))
    monkeypatch.setattr(tb, "_ekran_goster", lambda demet: cagrilar.append(("ekran", demet[0])))
    tb.handle_callback("denetim_goster", "cb-2")
    assert ("answer", "cb-2") in cagrilar
    assert any(c[0] == "ekran" for c in cagrilar)


def test_iptal_dosyasi_state_dizininde():
    """İptal penceresi state'te tutulur (workflow commit eder, kaybolmaz)."""
    assert "state" in str(tb._iptal_dosyasi())


def test_ayar_degisikligi_denetime_yazilir(monkeypatch, tmp_path):
    monkeypatch.setattr(tb, "AYARLAR_STATE_YOLU", tmp_path / "ayarlar.json")
    monkeypatch.setattr(tb, "GECMIS_YOLU", tmp_path / "gecmis.jsonl")
    monkeypatch.setattr(tb, "BEKLEYEN_YOLU", tmp_path / "bekleyen.json")
    monkeypatch.setattr(
        tb.ayar_deposu, "commit_ve_yukle", lambda dosyalar, mesaj: (True, "")
    )
    ok, _ = tb.ayar_uygula("MIN_IZLENME_ESIGI", "150", 42)
    assert ok is True
    kayit = next(k for k in dn.son_kayitlar(10) if k["olay"] == "ayar_degistir")
    assert kayit["ayrinti"]["anahtar"] == "MIN_IZLENME_ESIGI"
    assert kayit["ayrinti"]["yeni"] == "150"
    assert kayit["kullanici_id"] == 42


def test_kuyruk_atma_denetime_yazilir(monkeypatch, tmp_path):
    import modules.kuyruk_yonetimi as ky

    monkeypatch.setattr(ky, "KUYRUK_DIZINI", tmp_path / "queue")
    monkeypatch.setattr(ky, "ATILAN_DIZINI", tmp_path / "atilan")
    (tmp_path / "queue").mkdir()
    (tmp_path / "queue" / "x.json").write_text(
        '{"dosya_adi": "x", "baslik": "b", "stok_sebep": "kota"}', encoding="utf-8"
    )
    tb.ekran_kuyruk_at_uygula()
    kayit = next(k for k in dn.son_kayitlar(10) if k["olay"] == "stok_at")
    assert kayit["ayrinti"]["atilan"] == 1


def test_video_silme_denetime_yazilir(monkeypatch, tmp_path):
    """GERİ ALINAMAZ işlem: youtube_upload silmeden sonra denetim satırı yazar."""
    import modules.youtube_upload as yu

    monkeypatch.setenv("YOUTUBE_TOKEN", "fake")
    monkeypatch.setattr(yu, "token_yukle", lambda: {})
    monkeypatch.setattr(yu, "token_yenile", lambda t: "access")
    monkeypatch.setattr(yu, "ARSIV_YOLU", tmp_path / "yok.json")

    class Yanit:
        def __init__(self, kod, veri=None):
            self.status_code = kod
            self._veri = veri or {}

        def json(self):
            return self._veri

    from datetime import timedelta

    eski = (datetime.now(UTC) - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")

    def sahte_get(url, headers=None, timeout=None, **k):
        if "channels" in url:
            return Yanit(200, {"items": [{"contentDetails": {"relatedPlaylists": {"uploads": "PL1"}}}]})
        if "playlistItems" in url:
            return Yanit(200, {"items": [{"contentDetails": {"videoId": "vid1"}}]})
        return Yanit(
            200,
            {"items": [{"id": "vid1", "snippet": {"title": "Düşük video", "publishedAt": eski},
                        "statistics": {"viewCount": "5"}}]},
        )

    monkeypatch.setattr(yu.requests, "get", sahte_get)
    monkeypatch.setattr(yu.requests, "delete", lambda *a, **k: Yanit(204))
    monkeypatch.setattr(yu, "_arsivde_silindi_isaretle", lambda *a, **k: None)

    silinen = yu.dusuk_izlenmeli_videolari_temizle(min_izlenme=100, kontrol_suresi_dk=60)
    assert silinen, "test kurulumu silme üretmeli"
    kayit = next(k for k in dn.son_kayitlar(10) if k["olay"] == "video_sil")
    assert kayit["ayrinti"]["video_id"] == "vid1"
    assert kayit["ayrinti"]["esik"] == 100


def test_json_dosyasi_utf8_ve_tek_satir():
    dn.kaydet("olay", ayrinti={"türkçe": "ğüşiöç"}, simdi=SIMDI)
    metin = dn.DENETIM_YOLU.read_text(encoding="utf-8")
    assert "ğüşiöç" in metin
    assert json.loads(metin.strip())["olay"] == "olay"
