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
    for yasak in ("YOUTUBE_TOKEN", "TELEGRAM_BOT_TOKEN", "ARENA_COOKIES_JSON",
                  "PEXELS_API_KEY", "GH_TOKEN", "github.token", "secrets."):
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
    for secret_adi in ("YOUTUBE_TOKEN", "YOUTUBE_CLIENT_SECRET", "TELEGRAM_BOT_TOKEN",
                       "ARENA_COOKIES_JSON", "PEXELS_API_KEY"):
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
    assert isimler.index("Ayarları state'ten yükle") < isimler.index(
        "Tetikleyici parametrelerini çöz"
    ), "payload köprüden SONRA yazılmalı (payload > state önceliği)"


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
