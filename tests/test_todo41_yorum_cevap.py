"""İzleyici yorumuna Arena AI cevabı — güvenlik kapıları ve akış testleri.

KULLANICI FİKRİ (2026-11-11):
  "Hata taktiği uygulanan videolarda yorum geldiğinde, yorumu Arena AI'ye
   gönderip gelen cevabı izleyicinin yorumuna cevap olarak yazsak... ne
   düşünüyorsun?"

Modülün verdiği sözler:
  1. Sağlık/para/güvenlik kategorilerinde OTOMATİK cevap YASAK.
  2. Arena, videonun DOĞRU bilgisini görür → yanlış bilgiyi ASLA savunmaz.
  3. Arena erişilemezse %100 doğru şablon cevap gider (uydurma yok).
  4. Spam/hakaret/link içeren yorumlara cevap YOK.
  5. Kişi başına günlük 1, saatte 6, video başına 10 tavan (comment spam yok).
  6. Aynı yoruma iki kez cevap yazılmaz.
  7. Cevap ≤ 2 cümle, imzalı, saygılı.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from modules import yorum_cevap as yc


@pytest.fixture
def durum():
    return {"sur": 1, "cevaplar": [], "kisi": {}}


def _yorum(metin="Ahtapotların 3 kalbi var sanıyordum, meğer 3 değil 3 mü?", yazar="izleyici1", **ek):
    return {"id": "y1", "metin": metin, "yazar": yazar, "zaman": datetime.now(UTC).isoformat(),
            "video_id": "vid1", **ek}


# ---------------------------------------------------------------------------
# 1) Sağlık/para/güvenlik → otomatik cevap yok
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kategori", ["saglik_sorunu", "beslenme", "para", "guvenlik", "hukuk"])
def test_yasakli_kategoride_cevap_yok(kategori, durum):
    uygun, sebep = yc.cevap_verilebilir_mi(_yorum(), kategori, durum)
    assert uygun is False
    assert "otomatik cevap yasak" in sebep


def test_normal_kategoride_cevap_uygun(durum):
    uygun, sebep = yc.cevap_verilebilir_mi(_yorum(), "hayvanlar", durum)
    assert uygun is True and sebep == "uygun"


# ---------------------------------------------------------------------------
# 2) Spam / hakaret / link / kısa
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("metin", [
    "kanalıma gel abone ol bana",
    "https://spam.com bak",
    "t.me/kanal",
])
def test_spam_yorumlarina_cevap_yok(metin, durum):
    uygun, sebep = yc.cevap_verilebilir_mi(_yorum(metin), "hayvanlar", durum)
    assert uygun is False and "spam" in sebep


def test_hakaret_edilen_yoruma_cevap_yok(durum):
    uygun, sebep = yc.cevap_verilebilir_mi(_yorum("salak bir video olmuş"), "hayvanlar", durum)
    assert uygun is False and "hakaret" in sebep


def test_cok_kisa_yoruma_cevap_yok(durum):
    uygun, sebep = yc.cevap_verilebilir_mi(_yorum("👍"), "hayvanlar", durum)
    assert uygun is False and "kısa" in sebep


# ---------------------------------------------------------------------------
# 3) Tavanlar (comment spam politikası)
# ---------------------------------------------------------------------------


def test_ayni_yoruma_iki_kez_cevap_yok(durum):
    yorum = _yorum()
    durum["cevaplar"].append({"yorum_id": "y1", "zaman": datetime.now(UTC).isoformat(),
                              "video_id": "vid1"})
    uygun, sebep = yc.cevap_verilebilir_mi(yorum, "hayvanlar", durum)
    assert uygun is False and "zaten cevap" in sebep


def test_kisi_basina_gunluk_tavan(durum):
    simdi = datetime.now(UTC)
    durum["kisi"]["izleyici1"] = {"gun": simdi.strftime("%Y-%m-%d"), "sayi": 1}
    uygun, sebep = yc.cevap_verilebilir_mi(_yorum(), "hayvanlar", durum, simdi)
    assert uygun is False and "izleyiciye bugün" in sebep


def test_saatlik_tavan(durum):
    simdi = datetime.now(UTC)
    durum["cevaplar"] = [
        {"yorum_id": f"x{i}", "zaman": (simdi - timedelta(minutes=5)).isoformat(),
         "video_id": "vid1"} for i in range(yc.SAATLIK_TAVAN)
    ]
    uygun, sebep = yc.cevap_verilebilir_mi(_yorum(id="yeni"), "hayvanlar", durum, simdi)
    assert uygun is False and "saatlik" in sebep


def test_video_basina_tavan(durum):
    simdi = datetime.now(UTC)
    durum["cevaplar"] = [
        {"yorum_id": f"x{i}", "zaman": (simdi - timedelta(days=3)).isoformat(),
         "video_id": "vid1"} for i in range(yc.VIDEO_TAVAN)
    ]
    uygun, sebep = yc.cevap_verilebilir_mi(_yorum(id="yeni"), "hayvanlar", durum, simdi)
    assert uygun is False and "bu videoda" in sebep


def test_eski_yoruma_cevap_yok(durum):
    eski = (datetime.now(UTC) - timedelta(hours=yc.PENCERE_SAAT + 5)).isoformat()
    uygun, sebep = yc.cevap_verilebilir_mi(_yorum(zaman=eski), "hayvanlar", durum)
    assert uygun is False and "saatten eski" in sebep


# ---------------------------------------------------------------------------
# 4) Arena cevabı: temizlik + doğruluk kapısı
# ---------------------------------------------------------------------------


def test_cevap_temizlenir_ve_iki_cumleye_indirilir():
    ham = '"Cevap: Haklısın, ahtapotların 3 kalbi var. Bu arada harika bir soru. '
    ham += 'Devamını videoda anlattık. Bir de şunu ekleyeyim. — BOBİ 🤖"'
    temiz = yc.temizle_cevap(ham)
    assert temiz.startswith("Haklısın")
    assert "— BOBİ" not in temiz
    assert temiz.count(".") <= 2


def test_dogruluk_kapisi_defansif_cevabi_reddeder():
    gecti, gerekce = yc.dogruluk_kapisi(
        "Yanlış biliyorsun, öyle değil işte.", "Ahtapotların üç kalbi vardır."
    )
    assert gecti is False and gerekce == "defansif ton"


def test_dogruluk_kapisi_dogru_cevabi_gecirir():
    gecti, gerekce = yc.dogruluk_kapisi(
        "Haklısın, ahtapotların 3 kalbi var.", "Ahtapotların 3 kalbi vardır."
    )
    assert gecti is True


def test_guvenli_yedek_bos_bilgide_uydurmaz():
    cevap = yc.guvenli_yedek_cevap("")
    assert "Haklısın" in cevap
    assert "Doğrusu şu" not in cevap, "bilgi yoksa iddia üretilmemeli"


def test_guvenli_yedek_dogru_bilgiyi_kullanir():
    cevap = yc.guvenli_yedek_cevap("Ahtapotların 3 kalbi vardır.")
    assert "3 kalbi vardır" in cevap


# ---------------------------------------------------------------------------
# 5) Arena prompt'u yanlış bilgiyi savunmayı YASAKLAR
# ---------------------------------------------------------------------------


def test_arena_promptu_dogru_bilgiyi_ve_yasagi_icerir(monkeypatch, durum):
    yakalanan = {}

    def sahte(prompt):
        yakalanan["prompt"] = prompt
        return "Haklısın, doğrusu 3."

    # KULLANICI (2026-11-13): Arena çöpe atıldı → cevap üretimi Gemini web'den.
    import modules.gemini_web as gw

    monkeypatch.setattr(gw, "metin_uret", sahte)
    cevap = yc.arena_cevabi_uret(
        {"metin": "Bence yanlış biliyorsunuz"},
        dogru_bilgi="Ahtapotların 3 kalbi vardır.",
        soru="Ahtapotların kaç kalbi var?",
        video_baslik="Ahtapot sırrı",
    )
    p = yakalanan["prompt"]
    assert "VİDEONUN DOĞRU BİLGİSİ" in p
    assert "3 kalbi" in p
    assert "SAVUNMA" in p, "yanlış bilgiyi savunma yasağı prompt'ta olmalı"
    assert "haklısın" in p.lower()
    assert cevap == "Haklısın, doğrusu 3."


# ---------------------------------------------------------------------------
# 6) Uçtan uca tur (kuru çalışma — YouTube'a yazmaz)
# ---------------------------------------------------------------------------


def test_tur_kuru_calisma_kayit_uretir(tmp_path, monkeypatch):
    import modules.gemini_web as gw

    monkeypatch.setattr(gw, "metin_uret", lambda p: "Haklısın, doğrusu 3 kalp.")
    monkeypatch.setattr(
        yc, "yorumlari_oku",
        lambda vid, tok, azami=10: [
            {"id": "c1", "metin": "Bence 3 değil 2 kalbi var", "yazar": "ali",
             "zaman": datetime.now(UTC).isoformat(), "video_id": vid, "cevap_var": False},
            {"id": "c2", "metin": "https://spam.com", "yazar": "bot",
             "zaman": datetime.now(UTC).isoformat(), "video_id": vid, "cevap_var": False},
        ],
    )
    durum_yolu = tmp_path / "yorum.json"
    sonuc = yc.tur_calistir(
        [{"video_id": "v1", "kategori": "hayvanlar",
          "dogru_bilgi": "Ahtapotların 3 kalbi vardır.", "soru": "Kaç kalbi var?"}],
        "sahte-token", state_yolu=durum_yolu, kuru_calisma=True,
    )
    assert sonuc["cevaplanan"] == 1
    assert sonuc["atlanan"] == 1
    assert any("spam" in s for s in sonuc["sebepler"])
    kayit = sonuc["kayitlar"][0]
    assert kayit["yorum_id"] == "c1"
    assert "BOBİ" in kayit["cevap"]


def test_tur_yasakli_kategoride_hic_cevap_yazmaz(tmp_path, monkeypatch):
    monkeypatch.setattr(
        yc, "yorumlari_oku",
        lambda vid, tok, azami=10: [
            {"id": "c1", "metin": "Bu ilaç güvenli mi?", "yazar": "veli",
             "zaman": datetime.now(UTC).isoformat(), "video_id": vid, "cevap_var": False}
        ],
    )
    sonuc = yc.tur_calistir(
        [{"video_id": "v1", "kategori": "saglik_sorunu", "dogru_bilgi": "..."}],
        "tok", state_yolu=tmp_path / "y.json", kuru_calisma=True,
    )
    assert sonuc["cevaplanan"] == 0
    assert any("otomatik cevap yasak" in s for s in sonuc["sebepler"])


def test_tur_arena_coktugunde_guvenli_yedek_kullanir(tmp_path, monkeypatch):
    monkeypatch.setattr(
        yc, "yorumlari_oku",
        lambda vid, tok, azami=10: [
            {"id": "c9", "metin": "Doğrusu ne?", "yazar": "ayse",
             "zaman": datetime.now(UTC).isoformat(), "video_id": vid, "cevap_var": False}
        ],
    )
    sonuc = yc.tur_calistir(
        [{"video_id": "v1", "kategori": "hayvanlar",
          "dogru_bilgi": "Ahtapotların 3 kalbi vardır."}],
        "tok", arena_fn=lambda *a, **k: None,
        state_yolu=tmp_path / "y.json", kuru_calisma=True,
    )
    assert sonuc["cevaplanan"] == 1
    assert "3 kalbi vardır" in sonuc["kayitlar"][0]["cevap"]


def test_ozet_son24_sayar(tmp_path):
    durum_yolu = tmp_path / "y.json"
    simdi = datetime.now(UTC)
    import json

    durum_yolu.write_text(json.dumps({
        "sur": 1, "kisi": {},
        "cevaplar": [
            {"zaman": (simdi - timedelta(hours=2)).isoformat(), "yazildi": True},
            {"zaman": (simdi - timedelta(days=4)).isoformat(), "yazildi": True},
        ],
    }, ensure_ascii=False), encoding="utf-8")
    oz = yc.ozet(durum_yolu)
    assert oz["toplam"] == 2
    assert oz["son24"] == 1
    assert oz["yazilan"] == 2


# ---------------------------------------------------------------------------
# 7) Workflow + CLI (otomatik koşu)
# ---------------------------------------------------------------------------


def test_yorum_cevap_workflow_var_ve_guvenli():
    from pathlib import Path

    import yaml

    kok = Path(__file__).resolve().parents[1]
    d = yaml.safe_load((kok / ".github/workflows/yorum_cevap.yml").read_text(encoding="utf-8"))
    job = d["jobs"]["yorum-cevapla"]
    env = {}
    for a in job["steps"]:
        env.update(a.get("env") or {})
    assert env.get("ARENA_COOKIES_JSON", "").startswith("${{ secrets.")
    assert env.get("YOUTUBE_TOKEN", "").startswith("${{ secrets.")
    # Üretim hattıyla aynı concurrency grubunda OLMAMALI (kuyruğu kilitlemesin)
    assert d.get("concurrency", {}).get("group") == "yorum-cevap"
    # Cron saatlik
    assert d[True]["schedule"][0]["cron"] == "17 * * * *"


def test_son_videolardan_adaylar_dogru_bilgi_olmadan_vermez(tmp_path, monkeypatch):
    """Doğru bilgi yoksa cevap YAZILMAZ (uydurma cevap, cevapsızlıktan kötü)."""
    import json

    arsiv = tmp_path / "videos.json"
    arsiv.write_text(json.dumps([
        {"video_id": "a", "durum": "yayinda", "kategori": "hayvanlar",
         "dogru_bilgi": "Ahtapotların 3 kalbi vardır."},
        {"video_id": "b", "durum": "yayinda", "kategori": "hayvanlar"},  # bilgi yok
    ], ensure_ascii=False), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    (tmp_path / "bobi_tv/archive").mkdir(parents=True)
    (tmp_path / "bobi_tv/archive/videos.json").write_text(
        arsiv.read_text(encoding="utf-8"), encoding="utf-8"
    )
    adaylar = yc.son_videolardan_adaylar(5)
    assert [a["video_id"] for a in adaylar] == ["a"]
