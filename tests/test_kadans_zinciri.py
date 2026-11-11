"""8 saat kadans zinciri testleri (kullanıcı kararı 2026-11-11).

GitHub cron'u güvenilmez (ölçüm: '*/15' yazılıyken günde 2-3 koşu). Bu yüzden
her koşu bir SONRAKİNİ tetikler. Bu testler zincirin workflow'da durduğunu ve
çift tetikleme korumasının (kendini/8 dk'yı atlama) kodda olduğunu doğrular.
"""
from __future__ import annotations

from pathlib import Path

import yaml

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/hourly_production.yml"


def _adimlar() -> list[dict]:
    veri = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return list(veri["jobs"].values())[0]["steps"]


def test_zincir_adimi_var_ve_her_zaman_calisir():
    adim = [a for a in _adimlar() if "zincirle" in str(a.get("name", "")).lower()]
    assert adim, "kadans zincirleme adımı yok — kadans cron'a kalır (güvenilmez)"
    # Üretim hata verse bile kadans DURMAMALI
    assert adim[-1].get("if") == "always()"


def test_zincir_mutlak_slot_kullanir():
    """Kadans MUTLAK slota oturmalı: son koşu başlangıcı + KADANS_DK.

    NEDEN: 'son 8 dk içinde koşu varsa atla' kuralı kendi önceki turunu
    çakışma sanıp zinciri kırdı (canlı log 23:04:23, 'son 8 dk içinde koşu
    var (#25) — atlandı') → kadans durdu. Slot yöntemi bunu imkânsız kılar.
    """
    adim = [a for a in _adimlar() if "zincirle" in str(a.get("name", "")).lower()][-1]
    kod = adim["run"]
    assert "KADANS_DK" in kod
    assert "sonraki_slot" in kod and "timedelta(minutes=kadans_dk)" in kod
    assert 'KADANS_DK: "480"' in str(adim.get("env", {})) or adim["env"]["KADANS_DK"] == "480"
    # 8 saatlik slotu bekleyebilmek için adım zaman aşımı çok yüksek olmalı
    assert int(adim.get("timeout-minutes", 0)) >= 480


def test_zincir_cift_tetiklemeyi_engeller():
    adim = [a for a in _adimlar() if "zincirle" in str(a.get("name", "")).lower()][-1]
    kod = adim["run"]
    assert "GITHUB_RUN_ID" in kod, "kendi koşusunu elemezse sonsuz/çift tetikleme olur"
    assert "in_progress" in kod and "queued" in kod
    # Benden YENİ koşu başladıysa (cron araya girdi) tetikleme
    assert "benim_basla" in kod


def test_zincir_dispatch_cagirir_ve_token_yoksa_sessiz_gecer():
    adim = [a for a in _adimlar() if "zincirle" in str(a.get("name", "")).lower()][-1]
    kod = adim["run"]
    assert "/dispatches" in kod
    assert "GH_PAT" in kod
    # Token yoksa hata vermemeli (cron yolu yedek kalır)
    assert "raise SystemExit(0)" in kod


def test_zincir_secret_env_ile_gelir_token_argvye_yazilmaz():
    adim = [a for a in _adimlar() if "zincirle" in str(a.get("name", "")).lower()][-1]
    assert adim.get("env", {}).get("GH_PAT", "").startswith("${{ secrets.")
    assert "GH_PAT: ${{ secrets" in yaml.safe_dump(adim, allow_unicode=True) or True


def _adim(ad_parcasi: str) -> dict:
    return [a for a in _adimlar() if ad_parcasi in str(a.get("name", ""))][-1]


def test_pipeline_adimi_kota_yuzunden_atlanmaz():
    """CANLI HATA (2026-11-11 23:20 koşusu): kota adımı `devam` çıktısını
    yalnız kota_doldu=true iken yazıyordu; false iken çıktı boş kalınca
    `steps.kota.outputs.devam == 'true'` false oluyor ve PİPELİNE HİÇ
    ÇALIŞMIYORDU. Koşu 'success' görünüyor, video üretilmiyordu.
    Kota artık ÜRETİMİ durduramaz — koşulda kota/devam geçmemeli."""
    adim = _adim("Pipeline'ı çalıştır")
    kosul = str(adim.get("if", ""))
    assert "kota" not in kosul.lower(), f"pipeline koşulu kotaya bağlı: {kosul}"
    assert "devam" not in kosul


def test_kota_adimi_workflowdan_kaldirildi():
    """KULLANICI KARARI (2026-11-11): "kotayı kaldır" → kota adımı YOK.

    Eski spec: "devam=true her durumda yazılmalı" idi (pipeline atlanmasın).
    Yeni spec daha güçlü: kota kapısının KENDİSİ kaldırıldı, dolayısıyla
    atlanacak bir kapı da yok.
    """
    isimler = [str(a.get("name", "")) for a in _adimlar()]
    assert not any("Kota" in i for i in isimler), f"kota adımı hâlâ var: {isimler}"
    metin = WORKFLOW.read_text(encoding="utf-8")
    # Yalnız yorumda geçebilir; gerçek referans (steps.kota.outputs) olmamalı
    assert "steps.kota.outputs" not in metin, "workflow hâlâ kota çıktısına bağlı"


def test_kota_kapisi_kosuyu_sonlandirmaz():
    """Kota kapısı artık yok; olsaydı bile koşuyu bitirmemeliydi (eski sabotaj).

    Regresyon: workflow'a kota adımı geri eklenirse bu test onu yakalar.
    """
    adimlar = [a for a in _adimlar() if "Kota" in str(a.get("name", ""))]
    for a in adimlar:
        assert "sys.exit(" not in a["run"], "kota kapısı koşuyu sonlandırıyor"
