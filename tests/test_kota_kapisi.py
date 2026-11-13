"""TODO 9 + P2 — workflow köprüsü ve push disiplini testleri.

Kapsam: hourly_production.yml'de 'Ayarları state'ten yükle' köprü adımının
varlığı ve konumu, pipeline adımından sabit ayar satırlarının kaldırıldığı
(grep assert), secret satırlarının KORUNDUĞU, render testi payload'ının
env'e çevrildiği (TODO 12 yolu), telegram_bot.yml'de push başarısızlığının
yutulmadığı ve bekleyen ayar yeniden denemesinin bağlı olduğu.
Kota kapısının koşu-yüzü testleri bu dosyada TODO 10 ile gelir.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_KOK = Path(__file__).resolve().parent.parent
HOURLY = REPO_KOK / ".github" / "workflows" / "hourly_production.yml"
BOT = REPO_KOK / ".github" / "workflows" / "telegram_bot.yml"


def _hourly_yukle() -> dict[str, Any]:
    veri: object = yaml.load(HOURLY.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    assert isinstance(veri, dict), "hourly_production.yml sözlük olmalı"
    return veri


def _hourly_adimlar() -> list[dict[str, Any]]:
    adimlar: Any = _hourly_yukle()["jobs"]["uret-ve-yayinla"]["steps"]
    assert isinstance(adimlar, list)
    return [dict(a) for a in adimlar]


# ---------- TODO 9: state → env köprüsü ----------


def test_bridge_adimi_var_ve_pipeline_dan_once() -> None:
    adimlar = _hourly_adimlar()
    isimler = [str(a.get("name", "")) for a in adimlar]
    assert "Ayarları state'ten yükle" in isimler, "köprü adımı eksik (TODO 9)"
    bridge_idx = isimler.index("Ayarları state'ten yükle")
    pipeline_idx = next(i for i, n in enumerate(isimler) if "Pipeline'ı çalıştır" in n)
    assert bridge_idx < pipeline_idx, "köprü, pipeline'dan ÖNCE çalışmalı"


def test_bridge_secretlari_env_e_yazmaz() -> None:
    """Köprü adımı modül fonksiyonlarını kullanır; secret'lar env_satirlari()
    tarafından zaten filtrelenir (bkz. test_ayar_deposu). Burada ek garanti:
    köprü adımı kodunda secret adı geçmez."""
    adimlar = _hourly_adimlar()
    bridge = next(a for a in adimlar if str(a.get("name", "")) == "Ayarları state'ten yükle")
    yazi = str(bridge.get("run", ""))
    assert "env_satirlari" in yazi, "köprü env_satirlari() kullanmalı (tek filtre noktası)"
    for yasak in (
        "YOUTUBE_TOKEN",
        "TELEGRAM_BOT_TOKEN",
        "GEMINI_COOKIES",
        "PEXELS_API_KEY",
        "GH_TOKEN",
        "github.token",
        "secrets.",
    ):
        assert yasak not in yazi, f"köprü adımı secret referansı içeriyor: {yasak}"


def test_pipeline_sabit_ayar_satirlari_kaldirildi() -> None:
    """Kabul kriteri 3: workflow'da GUNLUK_MAKS:/GUNLUK_HEDEF: sabit yazısı 0."""
    yazi = HOURLY.read_text(encoding="utf-8")
    assert yazi.count("GUNLUK_MAKS:") == 0, "GUNLUK_MAKS sabit satırı kaldırılmalı"
    assert yazi.count("GUNLUK_HEDEF:") == 0, "GUNLUK_HEDEF sabit satırı kaldırılmalı"
    assert yazi.count("OTOMATIK_SIL_AKTIF:") == 0, "temizlik sabiti kaldırılmalı"
    assert "MOD: 'isindirma_saatlik'" not in yazi, "MOD sabiti kaldırılmalı"


def test_secret_satirlari_korunur() -> None:
    """Köprü secret'lara DOKUNMAZ: pipeline adımının secret eşlemeleri yerinde kalır."""
    adimlar = _hourly_adimlar()
    pipeline = next(a for a in adimlar if "Pipeline'ı çalıştır" in str(a.get("name", "")))
    env: Any = pipeline.get("env") or {}
    for secret_adi in (
        "YOUTUBE_TOKEN",
        "YOUTUBE_CLIENT_SECRET",
        "TELEGRAM_BOT_TOKEN",
        "GEMINI_COOKIES",
        "PEXELS_API_KEY",
    ):
        assert secret_adi in env, f"secret eşlemesi kaybolmuş: {secret_adi}"


def test_render_testi_payload_env_e_cevriliyor() -> None:
    """TODO 12 yolu: repository_dispatch client_payload.yukleme_atla →
    GITHUB_ENV YUKLEME_ATLA=1 (köprüden sonra yazılır → payload kazanır)."""
    adimlar = _hourly_adimlar()
    tetik = next(a for a in adimlar if str(a.get("id", "")) == "tetik")
    yazi = str(tetik.get("run", ""))
    assert "YUKLEME_ATLA=1" in yazi, "payload YUKLEME_ATLA=1'e çevrilmeli"
    env: Any = tetik.get("env") or {}
    assert "TETIK_YUKLEME_ATLA" in env, "payload env'e bağlanmalı"
    assert "client_payload.yukleme_atla" in str(env["TETIK_YUKLEME_ATLA"])
    adimlar = _hourly_adimlar()
    isimler = [str(a.get("name", "")) for a in adimlar]
    assert isimler.index("Ayarları state'ten yükle") < isimler.index("Tetikleyici parametrelerini çöz"), (
        "payload köprüden SONRA yazılmalı (payload > state önceliği)"
    )


# ---------- P2: push başarısızlığı yutulmaz ----------


def test_telegram_bot_push_yutulmaz() -> None:
    """Kabul kriteri 4: `|| echo "Push atlandı"` 0 eşleşme; push hatası exit 1."""
    yazi = BOT.read_text(encoding="utf-8")
    assert yazi.count('|| echo "Push atlandı"') == 0, "sessiz push yutma kaldırılmalı"
    assert "if ! git push origin main; then" in yazi, "push hatası açıkça yakalanmalı"
    assert "exit 1" in yazi, "push hatası koşuyu KIRMIZI yapmalı"


def test_telegram_bot_bekleyen_ayar_yeniden_denemesi_bagli() -> None:
    """TODO 8: bot koşusu başında bekleyen ayar değişikliği yeniden denenir."""
    yazi = BOT.read_text(encoding="utf-8")
    assert "bekleyen_ayarlari_yeniden_dene" in yazi, "bekleyen yeniden deneme bağlı değil"


def test_workflow_yaml_gecerli_kalir() -> None:
    for yol in (HOURLY, BOT):
        veri: object = yaml.load(yol.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
        assert isinstance(veri, dict), yol.name
        assert "jobs" in veri, yol.name


# ===========================================================================
# TODO 10 — kota kapısı koşu mantığı (modules/kota_kapisi + main_pipeline)
# ===========================================================================

import importlib  # noqa: E402
import json  # noqa: E402
from datetime import UTC, datetime, timedelta  # noqa: E402
from typing import Any as _Any  # noqa: E402

import pytest  # noqa: E402

import modules.kota_kapisi as kk  # noqa: E402
from modules.ayar_katalogu import KOTA_TAVANI  # noqa: E402


def test_gunluk_maks_tavani_6_kodlanmis() -> None:
    """P4: 10000 // 1600 = 6 — tavan katalogdan gelir, kapı bunu kullanır."""
    assert KOTA_TAVANI == 6
    assert kk.kota_dolu_cikis_kodu("sessiz_dur") == 0
    assert kk.kota_dolu_cikis_kodu("hata") == 1
    assert kk.kota_dolu_cikis_kodu(None) == 0
    assert kk.kota_dolu_cikis_kodu("sahse-deger") == 0, "bilinmeyen → güvenli varsayılan"


def test_kota_kontrol_doluluk_24_saat_penceresi(tmp_path: Path) -> None:
    arsiv = tmp_path / "videos.json"
    arsiv.write_text(json.dumps([{"tarih": "2026-01-01T10:00:00Z"}]), encoding="utf-8")
    kota = tmp_path / "youtube_quota.json"
    simdi = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    kota.write_text(
        json.dumps({"doldu": True, "guncelleme": (simdi - timedelta(hours=2)).isoformat()}),
        encoding="utf-8",
    )
    sonuc = kk.kota_kontrol_yap(hedef=1, arsiv_yolu=arsiv, kota_yolu=kota, simdi=simdi)
    assert sonuc["kota_doldu"] == "true" and sonuc["devam"] == "false"
    # 24 saat geçtiyse kota sıfırlanmış sayılır:
    kota.write_text(
        json.dumps({"doldu": True, "guncelleme": (simdi - timedelta(hours=25)).isoformat()}),
        encoding="utf-8",
    )
    sonuc2 = kk.kota_kontrol_yap(hedef=1, arsiv_yolu=arsiv, kota_yolu=kota, simdi=simdi)
    assert sonuc2["kota_doldu"] == "false" and sonuc2["devam"] == "false"  # hedef bugün tutuldu


def test_kota_kontrol_hedefe_gore_devam(tmp_path: Path) -> None:
    arsiv = tmp_path / "videos.json"
    arsiv.write_text(json.dumps([{"tarih": "2026-01-01T10:00:00Z"}]), encoding="utf-8")
    kota = tmp_path / "youtube_quota.json"
    simdi = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    sonuc = kk.kota_kontrol_yap(hedef=4, arsiv_yolu=arsiv, kota_yolu=kota, simdi=simdi)
    assert sonuc == {"bugunki": "1", "kalan": "3", "kota_doldu": "false", "devam": "true"}


def test_kota_durumu_ozeti_bilinmiyor_uydurmasiz(tmp_path: Path) -> None:
    """Kota dosyası yokken panel 'bilinmiyor' der — sayı UYDURULMAZ."""
    ozet = kk.kota_durumu_ozeti(tmp_path / "yok.json")
    assert "bilinmiyor" in ozet
    import re as _re

    assert not _re.search(r"\d{3,}", ozet)


def test_kota_durumu_ozeti_birimle_hesap(tmp_path: Path) -> None:
    kota = tmp_path / "youtube_quota.json"
    kota.write_text(json.dumps({"kalan_birim": 5200, "toplam_birim": 10000}), encoding="utf-8")
    ozet = kk.kota_durumu_ozeti(kota)
    assert "4800/10000 birim" in ozet
    assert "~3 yükleme kaldı" in ozet, "5200 // 1600 = 3"


# ---------- main_pipeline: tavan + davranış kapısı ----------


def _paket_sablonu(tmp_path: Path) -> dict[str, _Any]:
    final = tmp_path / "video.mp4"
    final.write_bytes(b"x")
    return {
        "video_no": 1,
        "dosya_adi": "20260101_test",
        "baslik": "Test video",
        "aciklama": "açıklama",
        "final_video": str(final),
        "kapak_dosyasi": "",
        "senaryo": {"sahneler": []},
        "kaynak": "test",
        "olusturuldu": "2026-01-01T00:00:00+00:00",
        "video_suresi": 15,
    }


def _piline_bagla(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> _Any:
    mp: _Any = importlib.import_module("main_pipeline")
    importlib.reload(mp)
    (tmp_path / "queue").mkdir(exist_ok=True)
    monkeypatch.setattr(mp, "ARSIV", tmp_path / "videos.json")
    monkeypatch.setattr(mp, "KUYRUK_YOLU", tmp_path / "queue")
    monkeypatch.setattr(mp, "LOG_YOLU", tmp_path / "logs")
    monkeypatch.setattr(mp, "uretim_hatti_calistir", lambda no: _paket_sablonu(tmp_path))
    monkeypatch.setattr(mp, "dusuk_izlenmeli_videolari_temizle", lambda **k: [])
    monkeypatch.setattr(mp, "notify_error", lambda *a, **k: None)
    monkeypatch.setattr(mp, "kota_state_yaz", lambda **k: None)
    return mp


def test_pipeline_gunluk_maks_kirpilmaz(monkeypatch: pytest.MonkeyPatch) -> None:
    """KULLANICI KARARI (2026-11-11): "Kota 6 istemiyorum, kotayı kaldır."

    Eski spec: env 24 olsa bile etkin değer 6'ya kırpılır + uyarı loglanır.
    Yeni spec: kırpma YOK — 6'ya sabitleme tam olarak kaldırılan davranıştı.
    """
    monkeypatch.setenv("GUNLUK_MAKS", "24")
    mp: _Any = importlib.import_module("main_pipeline")
    importlib.reload(mp)
    assert mp.GUNLUK_MAKS == 24, "kota tavanı kaldırıldı; değer kırpılmamalı"


def test_pipeline_kota_dolu_sessiz_dur_exit0(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """C2'nin çözümü: kota dolunca SESSİZ DUR — exit 0, self-repair fırtınası yok."""
    monkeypatch.setenv("KOTA_DOLU_DAVRANIS", "sessiz_dur")
    mp = _piline_bagla(monkeypatch, tmp_path)
    monkeypatch.setattr(mp, "toplu_yukle", lambda paketler: ([], [], [_paket_sablonu(tmp_path)]))
    monkeypatch.setattr(mp, "send_message", lambda *a, **k: True)
    with pytest.raises(SystemExit) as yakalanan:
        mp.pipeline_calistir()
    assert yakalanan.value.code == 0, "sessiz_dur → exit(0) — kırmızı tik YOK"


def test_pipeline_kota_dolu_hata_exit1(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """'hata' seçimi eski davranışı korur: kırmızı tik (exit 1)."""
    monkeypatch.setenv("KOTA_DOLU_DAVRANIS", "hata")
    mp = _piline_bagla(monkeypatch, tmp_path)
    monkeypatch.setattr(mp, "toplu_yukle", lambda paketler: ([], [], [_paket_sablonu(tmp_path)]))
    monkeypatch.setattr(mp, "send_message", lambda *a, **k: True)
    with pytest.raises(SystemExit) as yakalanan:
        mp.pipeline_calistir()
    assert yakalanan.value.code == 1


def test_yukleme_atla_1_iken_yukleme_cagirilmaz(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """TODO 12 mock kanıtı: YUKLEME_ATLA=1 → YouTube yükleme adımı HİÇ çağrılmaz."""
    monkeypatch.setenv("YUKLEME_ATLA", "1")
    mp = _piline_bagla(monkeypatch, tmp_path)
    cagrilar: list[_Any] = []

    def sahte_toplu_yukle(
        paketler: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[str], list[dict[str, Any]]]:
        cagrilar.append(paketler)
        return ([], [], [])

    monkeypatch.setattr(mp, "toplu_yukle", sahte_toplu_yukle)
    monkeypatch.setattr(mp, "send_message", lambda *a, **k: True)
    monkeypatch.setattr(mp, "uretim_hatti_calistir", lambda no: None)  # üretim yok (kuyruk boş)
    with pytest.raises(SystemExit):
        mp.pipeline_calistir()
    assert cagrilar == [], "YUKLEME_ATLA=1 iken yükleme çağrılmamalı"


# ---------- workflow yüzü (TODO 10/11/12) ----------


def test_workflow_kota_adimi_yok() -> None:
    """KULLANICI KARARI (2026-11-11): "kotayı kaldır" → workflow'da kota kapısı YOK.

    Eski spec: kota adımı modules/kota_kapisi'ni çağırmalıydı.
    Yeni spec: adımın kendisi kaldırıldı. kota_kapisi modülü yalnız YARDIMCI
    fonksiyonlar (gerçek API hatası sınıflandırma) için duruyor.
    """
    import yaml

    kok = Path(__file__).resolve().parents[1]
    veri = yaml.safe_load((kok / ".github/workflows/hourly_production.yml").read_text(encoding="utf-8"))
    adimlar = list(veri["jobs"].values())[0]["steps"]
    assert not any("Kota" in str(a.get("name", "")) for a in adimlar)

def test_workflow_force_tuketimi_adimi_var() -> None:
    yazi = HOURLY.read_text(encoding="utf-8")
    assert "force_sifirla" in yazi, "tek kullanımlık force tüketim adımı eksik"


def test_workflow_render_test_sonuc_bildirimi() -> None:
    yazi = HOURLY.read_text(encoding="utf-8")
    assert "Render testi sonucu bildir" in yazi, "render testi sonuç adımı eksik"
    assert "yükleme yapılmadı" in yazi, "sonuç mesajı 'yükleme yapılmadı' içermeli"
    adimlar: Any = yaml.load(HOURLY.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)["jobs"][
        "uret-ve-yayinla"
    ]["steps"]
    adim = next(a for a in adimlar if "Render testi sonucu bildir" in str(a.get("name", "")))
    assert "YUKLEME_ATLA" in str(adim.get("if", "")), "bildirim yalnız render testi koşusunda"
