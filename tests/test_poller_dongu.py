"""Poller uzun ömürlü döngü sözleşmesi (2026-11-11).

Neden: GitHub cron '*/5' fiilen çalışmıyor. Ölçüm: poller 2026-11-10'da günde
2 koşu yaptı, aralarında 168 dk vardı; kullanıcı /start'a bastığında 3 saat
cevap alamadı ve biriken 5 "/start" tek koşuda toplu işlendi.
Çözüm: tek koşuyu ~5.5 saat ayakta tutan yoklama döngüsü.
"""
from __future__ import annotations

from pathlib import Path

import yaml

WORKFLOW = Path(".github/workflows/telegram_bot.yml")


def _adim() -> dict:
    d = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    for job in d["jobs"].values():
        for step in job["steps"]:
            if "PYEOF" in step.get("run", ""):
                return step
    raise AssertionError("poller adımı bulunamadı")


def test_poller_dongu_ile_calisir() -> None:
    """Poller mesaj yokken ÇIKMAZ; döngü değişkenleri tanımlı olmalı."""
    adim = _adim()
    govde = adim["run"]
    env = adim["env"]
    assert env["TELEGRAM_DONGU_DK"] == "330"
    assert env["TELEGRAM_YOKLAMA_SN"] == "20"
    assert "while True:" in govde, "yoklama döngüsü yok"
    # mesaj yokken sys.exit(0) YAPILMAMALI (eski hata)
    yok_blok = govde.split("if not updates:", 1)[1][:400]
    assert "sys.exit(0)" not in yok_blok, "mesaj yokken çıkılıyor — poller yine susar"
    assert "time.sleep(YOKLAMA_SN)" in yok_blok


def test_poller_sure_dolunca_temiz_cikar() -> None:
    """Döngü süresi dolunca exit 0 (kırmızı tik değil) — yeni koşu devralır."""
    govde = _adim()["run"]
    assert "dongu_bitti()" in govde
    assert "sys.exit(0)" in govde


def test_poller_zaman_asimlari_github_limiti_altinda() -> None:
    """Adım 330 dk, job 350 dk — GitHub'ın 360 dk ücretsiz sınırının altında."""
    d = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    job = next(iter(d["jobs"].values()))
    assert job["timeout-minutes"] == 350
    assert _adim()["timeout-minutes"] == 330


def test_ag_hatasi_donguyu_oldurmez() -> None:
    """Tek ağ hatası koşuyu düşürmez; 3 ardışık hatada çıkar."""
    govde = _adim()["run"]
    assert "ardisik_hata" in govde
    assert "len(ardisik_hata) >= 3" in govde


def test_start_panelleri_cogaltmaz() -> None:
    """Kuyrukta biriken N adet /start ekrana N panel düşürmemeli."""
    kaynak = Path("modules/telegram_bot.py").read_text(encoding="utf-8")
    #handle_message içinde /start'a özel "yeni_mesaj=True" yolu KALMAMALI
    govde = kaynak.split("def handle_message", 1)[1].split("def ", 1)[0]
    assert "yeni_mesaj=True" not in govde, "/start hâlâ taze panel açıyor"
    assert "MENU_KOMUTLARI" in govde
