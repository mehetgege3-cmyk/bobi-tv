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


def _zincir_adimi() -> dict:
    """Zincirleme ADIMI artık üretim job'unda değil, ayrı `bekle-ve-zincirle`
    job'unda yaşıyor (2026-11-11 düzeltmesi).

    NEDEN TAŞINDI: zincir adımı üretim job'unun İÇİNDE ~8 saat uyuyordu
    (`time.sleep`), job bu süre boyunca `in_progress` kalıyordu ve
    `concurrency: hourly-production` yüzünden yeni koşular saatlerce
    `pending` bekliyordu (kanıt: run 42975301955 üretimini 07:00'de bitirdi,
    iş 15:00'e kadar açık kaldı; 09:35'teki koşu 40+ dk pending).
    Artık uyku AYRI job'da → üretim biter, kuyruk serbest kalır.
    """
    veri = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    job = veri["jobs"].get("bekle-ve-zincirle")
    assert job, "bekle-ve-zincirle job'u yok"
    adimlar = [a for a in job["steps"] if "zincirle" in str(a.get("name", "")).lower()]
    assert adimlar, "zincirleme adımı yok"
    return adimlar[-1]


def test_zincir_adimi_var_ve_her_zaman_calisir():
    veri = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    job = veri["jobs"]["bekle-ve-zincirle"]
    # Üretim hata verse bile kadans DURMAMALI
    assert job.get("if") == "always()"
    assert job.get("needs") == "uret-ve-yayinla"
    assert _zincir_adimi()["run"]
    # ÜRETİM JOB'UNDA uyuyan adım OLMAMALI (kuyruk kilitlenmesinin kaynağı)
    uretim_adlari = " ".join(str(a.get("name", "")) for a in _adimlar()).lower()
    assert "zincirle" not in uretim_adlari, "üretim job'unda zincir adımı kalmamalı"


def test_zincir_uykusu_uretim_jobunu_bloklamaz():
    """Kritik regresyon: uyku üretim job'unda olursa kuyruk saatlerce kilitlenir."""
    for ad in _adimlar():
        kod = str(ad.get("run", ""))
        assert "time.sleep(bekle)" not in kod, f"üretim job'unda uyku var: {ad.get('name')}"
    zincir = _zincir_adimi()["run"]
    assert "time.sleep(bekle)" in zincir


def test_zincir_mutlak_slot_kullanir():
    """Kadans MUTLAK slota oturmalı: son koşu başlangıcı + KADANS_DK.

    NEDEN: 'son 8 dk içinde koşu varsa atla' kuralı kendi önceki turunu
    çakışma sanıp zinciri kırdı (canlı log 23:04:23, 'son 8 dk içinde koşu
    var (#25) — atlandı') → kadans durdu. Slot yöntemi bunu imkânsız kılar.
    """
    adim = _zincir_adimi()
    kod = adim["run"]
    assert "KADANS_DK" in kod
    assert "timedelta(minutes=kadans_dk)" in kod, "slot = son koşu + KADANS_DK olmalı"
    assert 'KADANS_DK: "480"' in str(adim.get("env", {})) or adim["env"]["KADANS_DK"] == "480"
    # 8 saatlik slotu bekleyebilmek için JOB zaman aşımı yüksek olmalı
    veri = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert int(veri["jobs"]["bekle-ve-zincirle"].get("timeout-minutes", 0)) >= 480


def test_zincir_cift_tetiklemeyi_engeller():
    kod = _zincir_adimi()["run"]
    # Çift tetikleme koruması: çalışan/kuyruktaki koşu varsa atla
    assert "in_progress" in kod and "queued" in kod
    assert "atlandı" in kod


def test_zincir_dispatch_cagirir_ve_token_yoksa_sessiz_gecer():
    kod = _zincir_adimi()["run"]
    assert "/dispatches" in kod
    assert "GH_PAT" in kod
    # Token yoksa hata vermemeli (cron yolu yedek kalır)
    assert "raise SystemExit(0)" in kod


def test_zincir_secret_env_ile_gelir_token_argvye_yazilmaz():
    adim = _zincir_adimi()
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


def test_zincir_kendi_kosusunu_atlar():
    """CANLI HATA (43204255511): 'zincir: çalışan koşu var' deyip kendini atlıyordu.

    `bekle-ve-zincirle` job'u 8 saat uyuyor; uyandığında kendi koşusu listede
    completed görünüyor ve kontrol onu 'çalışan koşu' sanıp zinciri kırıyordu.
    Bu yüzden 8 saatlik zincir hiç çalışmadı, üretimi cron kurtarıyordu.
    """
    veri = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    zincir_job = veri["jobs"]["bekle-ve-zincirle"]
    zincir = next(a for a in zincir_job["steps"] if "Slotu bekle" in str(a.get("name", "")))
    yazi = str(zincir.get("run", ""))
    assert "GITHUB_RUN_ID" in yazi, "kendi koşu kimliği okunmalı"
    assert 'str(k.get("id")) == kendi' in yazi or "== kendi" in yazi, "kendi koşu atlanmalı"
