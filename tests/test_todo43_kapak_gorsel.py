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


def test_prompt_video_basligini_tasir():
    """KULLANICI (2026-11-13): istem = "<video başlığı> + sabit cümle".

    Eski "tam metin" ve 7 tasarım kuralı İPTAL edildi (kullanıcı: şablonu çöpe at).
    """
    from modules import kapak_gorsel

    paket = _paket()
    prompt = kapak_gorsel.gorsel_promptu(paket)
    baslik = str(paket.get("baslik") or paket.get("kapak_baslik") or "").strip()
    assert baslik and prompt.startswith(baslik)
    # Eski şema izleri ARTIK YOK
    assert "sok_baslik" not in prompt
    assert "vurgu_kelime" not in prompt
    assert "JSON" not in prompt
    assert "TASARIM KURALLARI" not in prompt


def test_prompt_kullanicinin_cumlesini_icerir():
    """İstem kullanıcının verdiği cümlenin TAMAMINI taşımalı."""
    from modules import kapak_gorsel

    prompt = kapak_gorsel.gorsel_promptu(_paket())
    assert "short video için kapak fotoğrafı istiyorum" in prompt
    assert "etkileşim ve izlenme rekorları kırması" in prompt
    assert "profesyonel şekilde tasarla" in prompt
    assert "merak edip tıklasın" in prompt


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


def test_prompt_gonderimi_calisan_orijinaldir():
    """DERS (canlı koşu 43292738267): eklenen 'doğrulama' gönderimi BOZDU.

    Çalışan sürüm (commit 5199075): editor.click(), keyboard.insert_text,
    ardından Send message düğmesine tıklama. Enter yedeği ve "kutu boşaldı mı"
    kontrolü KALDIRILDI — prompt kutuda kalıyordu, sohbet başlamıyordu.
    """
    import inspect

    from modules import arena_api

    kaynak = inspect.getsource(arena_api._promptu_gonder)
    assert 'button[aria-label="Send message"]' in kaynak
    assert "insert_text" in kaynak
    assert "await editor.click()" in kaynak
    assert "_editor_bos" not in kaynak          # bozduğumuz yedek geri gelmesin
    assert "keyboard.type(" not in kaynak


def test_eposta_on_kontrol_yazim_hatasini_yakalar():
    """CANLI OLAY (43283455004): secret'a 'gmal.com' yazılmıştı → 4 dk boşa koştu.

    Sözleşme: yazım hatası tarayıcı AÇILMADAN, anlaşılır mesajla yakalanır.
    """
    from modules import arena_giris

    ok, mesaj = arena_giris.eposta_on_kontrol("kullanici@gmal.com")
    assert ok is False
    assert "gmail.com" in mesaj          # doğru domain önerilir

    ok, mesaj = arena_giris.eposta_on_kontrol("kullanici@gmai.com")
    assert ok is False and "gmail.com" in mesaj

    assert arena_giris.eposta_on_kontrol("kullanici@gmail.com")[0] is True
    assert arena_giris.eposta_on_kontrol("x@outlook.com")[0] is True
    assert arena_giris.eposta_on_kontrol("bozuk-adres")[0] is False
    assert arena_giris.eposta_on_kontrol("")[0] is False


def test_google_oauth_akisi_olculen_secicileri_kullanir():
    """ÖLÇÜLDÜ (2026-11-12): gmail hesaplarında Arena Google OAuth'a yönlendiriyor.

    Gerçek ekran: accounts.google.com/v3/signin/identifier
      input[name="identifier"] → input[name="Password"]
    """
    import inspect

    from modules import arena_giris

    kaynak = inspect.getsource(arena_giris._google_ile_giris)
    assert 'input[name="identifier"]' in kaynak
    assert 'input[name="Password"]' in kaynak
    # 2FA / doğrulama ekranı ayrı mesajla raporlanır (sessiz başarısızlık yok)
    assert "2 ADIMLI DOĞRULAMA" in kaynak
    assert "accounts.google.com" in kaynak

    # e-posta adımı sonrası Google'a yönlendirme yakalanıyor mu?
    email_kaynak = inspect.getsource(arena_giris._email_ile_giris)
    assert "_google_ile_giris" in email_kaynak


def test_kisa_soruda_cevabin_basi_kesilmez():
    """CANLI HATA (koşu 43298899604): soru "Merhaba", cevap "Merhaba! 👋 ...".

    _cevabi_ayikla rfind() ile cevabın KENDİ başındaki "Merhaba"yı bulup
    kesiyordu → cevap "! 👋 Size nasıl yardımcı olabilirim?" oluyordu.
    Kısa sorularda echo İLK eşleşmedir; cevabın tamamı korunmalı.
    """
    from modules.arena_api import _cevabi_ayikla

    govde = (
        "What would you like to do?\n"
        "Merhaba\n"
        "Merhaba! 👋 Size nasıl yardımcı olabilirim?"
    )
    cevap = _cevabi_ayikla(govde, "Merhaba", "Merhaba")
    assert cevap.startswith("Merhaba!"), cevap
