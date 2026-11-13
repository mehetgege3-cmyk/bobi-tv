"""Arena canlı süreç testleri (2026-11-11 kullanıcı isteği).

Kullanıcı:
  "Timeout kullanma, bazen Arena AI uzun düşünüyor; bunu anlık olarak pipeline
   içinde gösterirsek yanıtın oluşturma sürecini varsayımsal değil, gerçek
   olarak göstermiş oluruz."

Bu dosya o sözü kilitler:
  1. `_arena_sorgusu_yap` SABİT süre sınırı kullanmaz (idle/maks frenleri ayrı),
     varsayılanları çok geniş ve env ile ayarlanır.
  2. Her ~10 sn'de canlı ilerleme satırı basar (flush=True → Actions'ta anında).
  3. Gerçek yanıt süresi `bobi_tv/state/arena_sure.json`'a yazılır.
  4. Canlı test workflow'u tek video üretir, kuyruğu kilitlemez (concurrency yok).
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import yaml

KOK = Path(__file__).resolve().parents[1]
ARENA = KOK / "modules/arena_api.py"
CANLI = KOK / ".github/workflows/canli_test.yml"


def _kaynak() -> str:
    return inspect.getsource(__import__("modules.arena_api", fromlist=["x"]))


# ---------------------------------------------------------------------------
# 1) Sabit timeout yok, frenler env'den
# ---------------------------------------------------------------------------


def test_arena_sorgusunda_sabit_timeout_yok():
    """Eski imza `timeout=130` idi: Arena 3 dk düşünürse cevap çöpe gidiyordu."""
    kaynak = _kaynak()
    assert "timeout: int = 130" not in kaynak
    assert "timeout=130" not in kaynak
    assert "timeout=120" not in kaynak
    # Yeni güvenlik frenleri env ile ayarlanır
    assert "ARENA_IDLE_DK" in kaynak and "ARENA_MAKS_DK" in kaynak


def test_arena_frenleri_cevabi_kaybetmez():
    """Fren devreye girse bile yeterli metin varsa CEVAP DÖNDÜRÜLÜR."""
    kaynak = _kaynak()
    assert "return cevap if len(cevap) >= min_cevap_uzunlugu else None" in kaynak


def test_arena_canli_ilerleme_satiri_basar():
    """Her 10 sn'de tek satır: saat · durum · karakter · son değişim."""
    kaynak = _kaynak()
    assert "son_kalp" in kaynak, "canlı ilerleme sayacı yok"
    assert "düşünüyor" in kaynak and "karakter" in kaynak
    assert "flush=True" in kaynak, "Actions'ta anında görünmesi için flush şart"


def test_arena_kendi_dusunme_suresini_de_yazar():
    """Arena arayüzü 'Thought for 12 seconds' gösteriyor; loglanmalı."""
    assert "Thought for" in _kaynak()


# ---------------------------------------------------------------------------
# 2) Süre kaydı (panel/rapor varsayım değil ÖLÇÜM gösterir)
# ---------------------------------------------------------------------------


def test_arena_sure_kaydi_yazilir(tmp_path, monkeypatch):
    import modules.arena_api as aa

    hedef = tmp_path / "arena_sure.json"
    monkeypatch.setattr(aa, "ARENA_SURE_YOLU", hedef)
    aa._arena_sure_kaydet(41.0, 820, "12 seconds")
    aa._arena_sure_kaydet(63.0, 900, "20 seconds")
    veri = json.loads(hedef.read_text(encoding="utf-8"))
    assert veri["son"]["saniye"] == 63.0
    assert veri["ortalama"] == 52.0
    assert veri["en_uzun"] == 63.0
    assert veri["ornek"] == 2
    assert len(veri["olcumler"]) == 2


def test_arena_sure_kaydi_20_olcumle_sinirli(tmp_path, monkeypatch):
    import modules.arena_api as aa

    hedef = tmp_path / "arena_sure.json"
    monkeypatch.setattr(aa, "ARENA_SURE_YOLU", hedef)
    for i in range(30):
        aa._arena_sure_kaydet(float(i), 100)
    veri = json.loads(hedef.read_text(encoding="utf-8"))
    assert veri["ornek"] == 20, "dosya şişmesin"


def test_panel_arena_suresini_gosterir(tmp_path, monkeypatch):
    import modules.arena_api as aa
    import modules.telegram_bot as tb

    hedef = tmp_path / "arena_sure.json"
    monkeypatch.setattr(aa, "ARENA_SURE_YOLU", hedef)
    aa._arena_sure_kaydet(55.0, 640, "17 seconds")
    metin = tb._arena_sure_ozeti()
    assert "55 sn" in metin and "17 seconds" in metin


def test_panel_olcum_yoksa_satir_uydurmaz(tmp_path, monkeypatch):
    import modules.arena_api as aa
    import modules.telegram_bot as tb

    monkeypatch.setattr(aa, "ARENA_SURE_YOLU", tmp_path / "yok.json")
    assert tb._arena_sure_ozeti() == ""


# ---------------------------------------------------------------------------
# 3) Canlı test workflow'u
# ---------------------------------------------------------------------------


def _canli() -> dict:
    return yaml.safe_load(CANLI.read_text(encoding="utf-8"))


def test_canli_test_workflow_var_ve_tek_video():
    veri = _canli()
    job = veri["jobs"]["canli-test"]
    env = {a["name"]: a for a in job["steps"] if a.get("env")}
    ortam = {}
    for ad in env.values():
        ortam.update(ad["env"])
    assert ortam.get("TUR_BASINA_URETIM") == "1"
    assert ortam.get("URETIM_TAVANI") == "1", "canlı test 1 video üretmeli"
    assert ortam.get("CANLI_TEST") == "1"


def test_canli_test_kuyrugu_kilitlemez():
    """8 saatlik üretim job'u açıkken bile test HEMEN başlamalı → concurrency YOK."""
    veri = _canli()
    assert "concurrency" not in veri["jobs"]["canli-test"]
    assert "concurrency" not in veri


def test_canli_test_arena_frenlerini_env_ile_verir():
    veri = _canli()
    ortam = {}
    for ad in veri["jobs"]["canli-test"]["steps"]:
        ortam.update(ad.get("env") or {})
    assert ortam.get("ARENA_IDLE_DK") == "15"
    assert ortam.get("ARENA_MAKS_DK") == "45"
    assert ortam.get("PYTHONUNBUFFERED") == "1", "log anlık aksın"


def test_canli_test_yukleme_ve_kapak_icin_gerekli_secretlari_gecirir():
    veri = _canli()
    ortam = {}
    for ad in veri["jobs"]["canli-test"]["steps"]:
        ortam.update(ad.get("env") or {})
    for gerekli in ("YOUTUBE_TOKEN", "YOUTUBE_CLIENT_SECRET", "ARENA_COOKIES_JSON",
                    "TELEGRAM_BOT_TOKEN"):
        assert gerekli in ortam, f"{gerekli} geçirilmiyor"
        assert ortam[gerekli].startswith("${{ secrets."), "secret olarak geçmeli"


def test_canli_test_ozet_ve_artifact_uretir():
    veri = _canli()
    adlar = [a.get("name", "") for a in veri["jobs"]["canli-test"]["steps"]]
    assert any("özet" in a.lower() for a in adlar)
    assert any("artifact" in a.lower() for a in adlar)


# ---------------------------------------------------------------------------
# 4) main_pipeline CANLI_TEST modu — canlı koşuda bulunan hata
# ---------------------------------------------------------------------------


def test_canli_test_sabiti_ve_tavan_atlama():
    """CANLI HATA (2026-11-11, run 42998937740): test 'Üretim tavanına
    ulaşıldı (24/1). Atlanıyor.' diyerek HİÇBİR ŞEY yapmadan bitti.

    CANLI_TEST=1 iken üretim tavanı ve bugünkü sayım yok sayılmalı."""
    kaynak = (KOK / "main_pipeline.py").read_text(encoding="utf-8")
    assert 'CANLI_TEST = str(os.environ.get("CANLI_TEST", "0"))' in kaynak
    assert "if CANLI_TEST:" in kaynak
    assert "elif bugunki >= uretim_tavani:" in kaynak, "tavan kontrolü CANLI_TEST'ten SONRA gelmeli"
    assert "bu_tur = 1 if CANLI_TEST else bu_tur_hesapla" in kaynak


def test_canli_test_silme_kontrolunu_atlar():
    """Tek seferlik test kanalda video SİLME kararı vermemeli."""
    kaynak = (KOK / "main_pipeline.py").read_text(encoding="utf-8")
    assert "otomatik silme kontrolü atlandı" in kaynak


def test_canli_test_kapak_kaniti_loglar():
    """Yükleme sonrası 'kapak yüklendi mi + ilk kareye gömüldü mü' loglanmalı."""
    kaynak = (KOK / "main_pipeline.py").read_text(encoding="utf-8")
    assert "ilk kareye gömüldü" in kaynak


# ---------------------------------------------------------------------------
# 5) Canlı testten çıkan İÇERİK düzeltmeleri (döngü + kapak kanıtı)
# ---------------------------------------------------------------------------


def test_dongu_uygula_son_cumleye_uc_nokta_ekler():
    """CANLI TEST BULGUSU: kalite raporu 68/100 ile KALDI, döngü puanı 0'dı.

    Son cümle '...' ile bitmiyordu, ilk cümle bağlaçla başlamıyordu ve
    öneri UYGULANMIYORDU (kanca motorundaki hatanın kardeşi)."""
    from modules.senaryo_v7.loop_validator import dongu_uygula, loop_dogrula
    from modules.senaryo_v7.models import Diyalog, Senaryo

    senaryo = Senaryo(
        diyaloglar=[Diyalog(metin="MAKARNAMI YİYEN BENMİŞİM"),
                    Diyalog(metin="Nihayet! Kimmiş o"),
                    Diyalog(metin="Umarım o hırsız cezayı alır")],
        tts_metinleri=["MAKARNAMI YİYEN BENMİŞİM"],
    )
    assert loop_dogrula(senaryo).puan == 0
    sonuc = dongu_uygula(senaryo)
    assert sonuc.uygulandi is True
    assert sonuc.puan >= 70, "uygulama sonrası döngü kabul eşiğini geçmeli"
    assert senaryo.diyaloglar[-1].metin.endswith("...")
    assert senaryo.diyaloglar[0].metin.split()[0].lower() in {
        "ve", "ama", "fakat", "çünkü", "bu", "işte", "o", "dolayısıyla"
    }
    assert senaryo.tts_metinleri[0] == senaryo.diyaloglar[0].metin


def test_dongu_uygula_zaten_kusursuzsa_dokunmaz():
    from modules.senaryo_v7.loop_validator import dongu_uygula
    from modules.senaryo_v7.models import Diyalog, Senaryo

    senaryo = Senaryo(
        diyaloglar=[Diyalog(metin="Ve herkes bunu sordu"),
                    Diyalog(metin="Sonra kapı açıldı...")],
    )
    dongu_uygula(senaryo)
    assert senaryo.diyaloglar[0].metin == "Ve herkes bunu sordu"
    assert senaryo.diyaloglar[-1].metin == "Sonra kapı açıldı..."


def test_dongu_kopru_onerisi_deterministik():
    """Eskiden random.choice idi → aynı senaryo her koşuda farklı öneri."""
    from modules.senaryo_v7.loop_validator import _kopru_cumlesi_uret

    a = _kopru_cumlesi_uret("Bir şey oldu", "Kapı açıldı", False)
    b = _kopru_cumlesi_uret("Bir şey oldu", "Kapı açıldı", False)
    assert a == b


def test_kapak_yukleme_basarisizligi_sessizce_yutulmaz(tmp_path, monkeypatch, capsys):
    """Canlı testte log 'kapak yüklendi' diyordu; başarısızlık SESSİZDİ."""
    from modules import youtube_upload as yu

    ok = yu._kapak_yukle("vid", str(tmp_path / "yok.jpg"), "tok")
    assert ok is False
    cikti = capsys.readouterr().out
    assert "Kapak dosyası yok" in cikti
