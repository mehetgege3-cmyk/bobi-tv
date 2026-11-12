"""YENİ kapak hattı testleri (2026-11-12 kullanıcı kararı).

Kullanıcı: "Mevcut tüm kuralları çöpe at. Arena'ya videonun tam metnini ver,
metni okusun, Short için profesyonel kapak fotoğrafı oluştursun; oluşturduğu
resmi indir ve videonun ilk karesine yerleştirilip seçilsin."

Eski hat (A/B/C/D adayları, okunabilirlik skoru, sok_baslik/vurgu/renk JSON'u,
1. kareden kapak türetme) SİLİNDİ. Bu testler yeni tek yolu kilitler.
"""
from __future__ import annotations

import sys

import pytest


def _paket() -> dict:
    return {
        "dosya_adi": "test_kapak",
        "baslik": "Ahtapotların Üç Kalbi Var #shorts",
        "senaryo": {
            "baslik": "Ahtapotların Üç Kalbi Var #shorts",
            "kapak_baslik": "ÜÇ KALP, BİRİ DURUYOR",
            "tam_metin": (
                "🧠 Günün Merak Uyandıran Sorusu\nAhtapotların kaç kalbi var?\n\n"
                "🔍 Cevabı Biliyor Muydun?\nAhtapotların üç kalbi vardır ve biri yüzerken durur."
            ),
        },
    }


def test_prompt_videonun_tam_metnini_icerir():
    """Arena'ya giden prompt videonun TAM metnini taşımalı (kullanıcı şartı)."""
    from modules import kapak_gorsel

    paket = _paket()
    prompt = kapak_gorsel.gorsel_promptu(paket)
    assert "Ahtapotların üç kalbi vardır" in prompt
    assert "VİDEO METNİ (TAM)" in prompt
    # Kısa "sok başlık" şeması ARTIK YOK
    assert "sok_baslik" not in prompt
    assert "vurgu_kelime" not in prompt
    assert "JSON" not in prompt


def test_prompt_gorsel_uretimi_ister_ve_yazi_yasaklar():
    from modules import kapak_gorsel

    prompt = kapak_gorsel.gorsel_promptu(_paket())
    assert "görsel ÜRET" in prompt or "görsel üret" in prompt.lower()
    assert "9:16" in prompt
    assert "YAZI KOYMA" in prompt
    assert "tıklasın" in prompt  # tıklama/izleme teşviki


def test_eski_kapak_karar_hatti_silindi():
    """Eski KARAR hattı yok: A/B/C/D adayı, JSON önerisi, skor, seçim fonksiyonu."""
    from modules import kapak_arena

    for ad in (
        "arena_kapak_onerisi",
        "kapak_sec_ve_hazirla",
        "kapak_raporu",
        "_okunabilirlik_skoru",
        "_sinirlara_uygun",
        "ai_gorsel_zemin",
    ):
        assert not hasattr(kapak_arena, ad), f"eski hat geri gelmiş: {ad}"

    # mekanik yardımcılar KALDI (1. kareye yerleştirme kullanıcı şartı)
    for ad in ("ilk_kare_cikar", "baslik_kaplama", "ilk_kareye_yerlestir", "baslik_kaplama_jpg"):
        assert hasattr(kapak_arena, ad), f"gerekli yardımcı kayıp: {ad}"


def test_arena_gorseli_gelmezse_yedek_yol_import_hatasi_vermez(monkeypatch, tmp_path):
    """Yedek yol silinmiş modüle bağlı OLMAMALI (ImportError = kapak kaybı)."""
    from modules import kapak_gorsel, kapak_hatti

    monkeypatch.setattr(
        kapak_gorsel, "arena_kapak_gorseli_uret", lambda p: (_ for _ in ()).throw(RuntimeError("arena yok"))
    )
    monkeypatch.setattr(kapak_hatti.calisma_dizinleri, "OUTPUT_YOLU", tmp_path)
    from modules import kapak_arena

    monkeypatch.setattr(kapak_arena, "ilk_kare_cikar", lambda v, c: None)

    sonuc = kapak_hatti.kapak_uret_ve_yerlestir({"dosya_adi": "x", "baslik": "x"})
    assert sonuc["kaynak"] == "yok"
    assert sonuc["ilk_kare"] is False


def test_arena_kapak_gorseli_uret_senkron_cagrilabilir(monkeypatch):
    """Pipeline senkron; asenkron sarmalayıcı asyncio.run ile güvenli çalışmalı."""
    import asyncio
    import inspect

    from modules import kapak_gorsel

    assert not inspect.iscoroutinefunction(kapak_gorsel.arena_kapak_gorseli_uret)
    assert inspect.iscoroutinefunction(kapak_gorsel.arena_kapak_gorseli_uret_async)

    async def sahte(paket):
        return "gordu"

    monkeypatch.setattr(kapak_gorsel, "arena_kapak_gorseli_uret_async", sahte)
    assert kapak_gorsel.arena_kapak_gorseli_uret({"baslik": "x"}) == "gordu"

    # Çalışan bir loop içinden de patlamamalı (thread'e düşer)
    async def ic():
        return kapak_gorsel.arena_kapak_gorseli_uret({"baslik": "x"})

    assert asyncio.run(ic()) == "gordu"


def test_kucuk_gorsel_kapak_olarak_kabul_edilmez(tmp_path):
    """Logo/ikon/avatar kapak sanılmasın: minimum 400x400."""
    from PIL import Image

    from modules import kapak_gorsel

    kucuk = tmp_path / "logo.png"
    Image.new("RGB", (64, 64), (255, 0, 0)).save(kucuk)
    assert kapak_gorsel._gorsel_yeterli(kucuk) is False

    buyuk = tmp_path / "kapak.png"
    Image.new("RGB", (900, 1600), (0, 0, 255)).save(buyuk)
    assert kapak_gorsel._gorsel_yeterli(buyuk) is True


def test_kapak_gorseli_1080x1920_kirpilir(tmp_path):
    from PIL import Image

    from modules import kapak_gorsel

    ham = tmp_path / "ham.png"
    Image.new("RGB", (1024, 1024), (10, 20, 30)).save(ham)
    hedef = tmp_path / "kapak.jpg"
    assert kapak_gorsel.gorseli_karesine_oturt(ham, hedef) == hedef
    with Image.open(hedef) as img:
        assert img.size == (1080, 1920)


def test_render_kapaksiz_cokmez():
    """CANLI HATA (run 43265657831): kapak render'dan SONRA üretildiği için
    animasyon.py 'NoneType' object has no attribute 'read' ile çöküyordu.

    Sözleşme: kapak yokken render çalışır, 1. kare sahneden çizilir.
    """
    import inspect

    from modules import animasyon

    kaynak = inspect.getsource(animasyon)
    assert "ilk_kare_kapak_rgb = None" in kaynak
    assert "if kare_no == 0 and ilk_kare_kapak_rgb is not None:" in kaynak
    # kapak yoksa/okunamazsa sessizce çökmemeli, loglamalı
    assert "Kapak henüz yok" in kaynak
    assert "Kapak okunamadı" in kaynak


def test_kapak_uretilmeden_render_edilebilir_akis():
    """Sıra kilidi: render ÖNCE, kapak SONRA (kapak_hatti render sonrası çağrılır)."""
    import inspect

    from modules import arena_uretici

    kaynak = inspect.getsource(arena_uretici)
    assert "kapak_uret_ve_yerlestir" in kaynak
    # kapak çağrısı render fonksiyonundan sonra olmalı
    assert kaynak.index("kapak_uret_ve_yerlestir") > kaynak.index("def ")  # en az bir tanım var


def test_kapak_paket_alanlarini_doldurur(monkeypatch, tmp_path):
    """CANLI HATA (43266695264): kapak üretildi ama YouTube'a 'Kapak dosyası
    yok: (boş)' dedi — çünkü paket['kapak_dosyasi'] doldurulmuyordu.

    Sözleşme: kapak üretildiyse paket kapak_dosyasi/kapak_yolu/kapak_ilk_kare/
    kapak_kaynagi alanlarıyla işaretlenir.
    """
    from PIL import Image

    from modules import kapak_gorsel, kapak_hatti

    ham = tmp_path / "ham.png"
    Image.new("RGB", (900, 1600), (5, 5, 5)).save(ham)
    monkeypatch.setattr(kapak_gorsel, "arena_kapak_gorseli_uret", lambda p: ham)
    monkeypatch.setattr(kapak_hatti.calisma_dizinleri, "OUTPUT_YOLU", tmp_path)
    from modules import kapak_arena

    monkeypatch.setattr(kapak_arena, "ilk_kareye_yerlestir", lambda v, k: None)

    paket = {"dosya_adi": "p", "final_video": "", "senaryo": {}}
    sonuc = kapak_hatti.kapak_uret_ve_yerlestir(paket)
    assert sonuc["kaynak"] == "arena_gorsel"
    assert paket["kapak_dosyasi"] == sonuc["kapak"]
    assert paket["kapak_yolu"] == sonuc["kapak"]
    assert paket["kapak_kaynagi"] == "arena_gorsel"
    assert paket["kapak_ilk_kare"] is False  # video yoktu → gömülmedi (dürüst)


def test_prompt_gonderimi_dogrulanir():
    """CANLI BULGU (43271340457): prompt editörde KALDI (gönderilmedi) ama eski
    kod True dönüyordu → 8 dk boş sayfa beklendi, log 'gönderildi' dedi.

    Sözleşme: _promptu_gonder gönderimi DOĞRULAR; doğrulayamazsa False döner.
    """
    import inspect

    from modules import arena_api

    kaynak = inspect.getsource(arena_api._promptu_gonder)
    assert "_editor_bos" in kaynak          # editör boşaldı mı kontrolü
    assert "GÖNDERİLEMEDİ" in kaynak         # başarısızlık sessiz kalmıyor
    assert 'keyboard.press(tus)' in kaynak  # düğme çalışmazsa Enter/Ctrl+Enter yedeği
    assert "keyboard.type(" in kaynak  # GERÇEK tuş vuruşu (insert_text React'i güncellemiyor)
    assert "disabled" in kaynak              # pasif düğmeye tıklamayı fark eder


def test_olu_oturum_yonlendirmesi_aninda_yakalanir():
    """CANLI KANIT (run 43275868230): çerez ölüyken sayfa
    accounts.google.com'a yönlendi; hat 8 dakika boş bekledi.

    Sözleşme: yönlendirme URL'i görülürse oturum kapalı sayılır (ucuz kontrol).
    """
    import inspect

    from modules import arena_api, kapak_gorsel

    kaynak = inspect.getsource(arena_api.oturum_gercekten_acik_mi)
    for isaret in ("accounts.google.com", "/login", "/signin"):
        assert isaret in kaynak

    # Kapak hattı bu freni kullanmalı (yoksa yine boşa bekler)
    kapak_kaynak = inspect.getsource(kapak_gorsel.arena_kapak_gorseli_uret_async)
    assert "oturum_gercekten_acik_mi" in kapak_kaynak
    assert "_oturum_doldu_isaretle" in kapak_kaynak
    assert "_promptu_gonder" in kapak_kaynak


# ---------------------------------------------------------------------------
# Arena e-posta/şifre girişi (LMARENA_EMAIL + LMARENA_PASSWORD, 2026-11-12)
# ---------------------------------------------------------------------------


def test_giris_kimlik_yoksa_sessizce_atlar(monkeypatch):
    """Secret'lar yoksa giriş hattı üretimi düşürmez, None döner."""
    import asyncio

    from modules import arena_giris

    monkeypatch.delenv("LMARENA_EMAIL", raising=False)
    monkeypatch.delenv("LMARENA_PASSWORD", raising=False)
    assert arena_giris.kimlik_var_mi() is False
    assert asyncio.run(arena_giris.giris_yap_ve_cerez_al()) is None


def test_giris_modulu_olculen_secicileri_kullanir():
    """Yerel ölçümle bulunan gerçek DOM seçicileri kodda olmalı."""
    import inspect

    from modules import arena_giris

    kaynak = inspect.getsource(arena_giris)
    assert 'button:has-text("Agree")' in kaynak            # Terms of Use modalı
    assert "Continue with email" in kaynak                  # e-posta giriş yolu
    assert 'input[type="email"]' in kaynak                  # e-posta alanı (ölçüldü)
    assert 'input[type="password"]' in kaynak               # şifre adımı
    assert "domain is not permitted" in kaynak              # Arena domain doğrulaması


def test_giris_sifreyi_loglamaz():
    """Şifre log'a/ekran görüntüsüne sızmamalı."""
    import inspect

    from modules import arena_giris

    kaynak = inspect.getsource(arena_giris)
    # print satırlarında sifre değişkeni geçmemeli
    for satir in kaynak.splitlines():
        if "print(" in satir and "{" in satir:
            assert "sifre" not in satir.lower() or "yok" in satir.lower(), satir
    assert 'os.environ.get("LMARENA_PASSWORD"' in kaynak


def test_giris_workflow_secretlari_baglar():
    """Workflow iki secret'ı env'e bağlamalı ve çerez secret'ını güncellemeli."""
    from pathlib import Path

    yol = Path(".github/workflows/arena_giris_login.yml")
    metin = yol.read_text(encoding="utf-8")
    assert "secrets.LMARENA_EMAIL" in metin
    assert "secrets.LMARENA_PASSWORD" in metin
    assert "secrets.GH_PAT" in metin   # secret yazmak için gerekli
    assert "giris_yap_ve_secret_guncelle" in metin


def test_giris_domain_teshisi_ekler():
    """Arena domain reddettiğinde HANGİ domain olduğu log'a yazılmalı (adres değil)."""
    import inspect

    from modules import arena_giris

    kaynak = inspect.getsource(arena_giris._email_ile_giris)
    assert "domaini:" in kaynak
    assert 'split("@")[-1]' in kaynak
    assert "KABUL ETMİYOR" in kaynak
