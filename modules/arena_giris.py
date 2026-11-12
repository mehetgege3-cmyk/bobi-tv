"""Arena'ya E-POSTA/ŞİFRE ile otomatik giriş + çerez kendini besleme.

NEDEN (2026-11-12, canlı kanıtlar): `ARENA_COOKIES_JSON` süresi dolunca hem
senaryo hem kapak görseli hattı çöküyordu. Kullanıcı `LMARENA_EMAIL` ve
`LMARENA_PASSWORD` secret'larını ekledi → oturum artık kendini yenileyebilir.

ÖLÇÜLEN AKIŞ (yerel Playwright, 2026-11-12):
  1) https://arena.ai/agent/ açılır (giriş YOKKEN de editör görünür)
  2) Mesaj yazılıp gönderilince iki engel çıkar:
       a) "Terms of Use & Privacy Policy" modalı → button:has-text("Agree")
       b) "Log In or Create Account" modalı → "Continue with email"
  3) E-posta alanı: input[type="email"] (placeholder "Your email")
  4) Arena e-posta DOMAIN'ini doğrular ("This email domain is not permitted")
     → kullanıcının gerçek e-postası gerekir.
  5) Google ile giriş de mümkün ("Continue with Google") ama hesap seçimi ister.

GÜVENLİK: şifre log'a YAZILMAZ, ekran görüntülerinde de görünmemesi için şifre
yazıldıktan sonra ekran görüntüsü alınmaz. Giriş başarısızsa sadece DURUM yazılır.
"""
from __future__ import annotations

import asyncio
import os
from typing import Any

CIKIS_DIZINI = os.environ.get("KANIT_DIZINI", "kanit")


def kimlik_var_mi() -> bool:
    """E-posta + şifre secret'ları tanımlı mı?"""
    return bool(
        os.environ.get("LMARENA_EMAIL", "").strip()
        and os.environ.get("LMARENA_PASSWORD", "").strip()
    )


async def _modal_kapat(page, ad: str = "") -> bool:
    """Terms of Use / riza modalını kapatır (ölçüldü: 'Agree' düğmesi)."""
    for secici in (
        'button:has-text("Agree")',
        'button:has-text("I agree")',
        'button:has-text("Accept")',
    ):
        try:
            loc = page.locator(secici).first
            if await loc.count() and await loc.is_visible():
                await loc.click(timeout=5000)
                print(f"[Giriş] ✅ Rıza modalı kapatıldı ({secici}) {ad}", flush=True)
                await page.wait_for_timeout(1500)
                return True
        except Exception:
            continue
    return False


async def _giris_modalini_ac(page) -> bool:
    """'Log In or Create Account' modalını açar (mesaj göndererek tetiklenir)."""
    # 1) Doğrudan 'Log in' düğmesi varsa (sidebar) onu dene
    for secici in ('button:has-text("Log in")', 'button:has-text("Log In")'):
        try:
            loc = page.locator(secici).first
            if await loc.count() and await loc.is_visible():
                await loc.click(timeout=6000)
                await page.wait_for_timeout(2500)
                if await page.get_by_text("Continue with email", exact=False).count():
                    return True
        except Exception:
            continue

    # 2) Ölçülen yol: editöre bir şey yaz + gönder → login modalı çıkar
    try:
        editor = page.locator('div.tiptap[contenteditable="true"]').first
        await editor.wait_for(state="visible", timeout=20000)
        await editor.focus()
        await page.keyboard.type("merhaba", delay=15)
        await page.wait_for_timeout(500)
        await _modal_kapat(page, "(gönderim öncesi)")
        dugme = page.locator('button[aria-label="Send message"]').first
        if await dugme.count():
            await dugme.click(timeout=6000)
        else:
            await page.keyboard.press("Enter")
        await page.wait_for_timeout(3000)
        await _modal_kapat(page, "(gönderim sonrası)")
    except Exception as e:
        print(f"[Giriş] Modal tetikleme hatası: {str(e)[:110]}", flush=True)

    return bool(await page.get_by_text("Continue with email", exact=False).count())


async def _email_ile_giris(page) -> bool:
    """'Continue with email' → e-posta → şifre/sihirli bağlantı akışını yürütür."""
    email = os.environ.get("LMARENA_EMAIL", "").strip()
    sifre = os.environ.get("LMARENA_PASSWORD", "").strip()
    if not (email and sifre):
        print("[Giriş] LMARENA_EMAIL/LMARENA_PASSWORD yok — giriş atlandı", flush=True)
        return False

    # 'Continue with email' bağlantısı
    try:
        await page.get_by_text("Continue with email", exact=False).first.click(timeout=8000)
        print("[Giriş] 'Continue with email' açıldı", flush=True)
        await page.wait_for_timeout(2500)
    except Exception as e:
        print(f"[Giriş] 'Continue with email' açılamadı: {str(e)[:100]}", flush=True)
        return False

    # Teşhis: HANGİ DOMAIN reddedildi (e-posta adresi loglanmaz, yalnız domain)
    domain = email.split("@")[-1].lower() if "@" in email else "?"
    print(f"[Giriş] e-posta domaini: {domain}", flush=True)

    # E-posta alanı
    alan = page.locator('input[type="email"]').first
    try:
        await alan.wait_for(state="visible", timeout=15000)
        await alan.fill(email)
        await page.wait_for_timeout(600)
        await page.locator('button:has-text("Continue with email")').first.click(timeout=8000)
        print("[Giriş] E-posta gönderildi", flush=True)
    except Exception as e:
        print(f"[Giriş] E-posta adımı hatası: {str(e)[:110]}", flush=True)
        return False

    await page.wait_for_timeout(5000)

    # Arena domain doğrulaması yapıyor: "This email domain is not permitted"
    try:
        govde = await page.locator("body").inner_text()
    except Exception:
        govde = ""
    if "domain is not permitted" in govde.lower():
        print(
            f"[Giriş] ❌ Arena '{domain}' domainini KABUL ETMİYOR "
            "(geçici/tek kullanımlık e-posta servisleri engelli). "
            "Gmail/Outlook gibi kalıcı bir adres gerekir.",
            flush=True,
        )
        return False
    if "verification code" in govde.lower() or "check your email" in govde.lower():
        print(
            "[Giriş] ℹ️ Arena e-postaya DOĞRULAMA KODU / sihirli bağlantı gönderdi — "
            "bu akış otomatikleştirilemez (kullanıcı onayı gerekir).",
            flush=True,
        )

    # Şifre alanı çıktıysa doldur (şifre log'a yazılmaz)
    try:
        sifre_alani = page.locator('input[type="password"]').first
        if await sifre_alani.count():
            await sifre_alani.wait_for(state="visible", timeout=20000)
            await sifre_alani.fill(sifre)
            await page.wait_for_timeout(400)
            for secici in (
                'button:has-text("Log in")',
                'button:has-text("Sign in")',
                'button:has-text("Continue")',
                'button[type="submit"]',
            ):
                loc = page.locator(secici).first
                if await loc.count() and await loc.is_visible():
                    await loc.click(timeout=8000)
                    print("[Giriş] Şifre gönderildi", flush=True)
                    break
            await page.wait_for_timeout(8000)
        else:
            # Sihirli bağlantı / doğrulama kodu akışı olabilir
            print("[Giriş] ℹ️ Şifre alanı yok — sihirli bağlantı/kod akışı olabilir", flush=True)
            await page.wait_for_timeout(8000)
    except Exception as e:
        print(f"[Giriş] Şifre adımı hatası: {str(e)[:110]}", flush=True)

    return await giris_basarili_mi(page)


async def giris_basarili_mi(page) -> bool:
    """Giriş gerçekten oldu mu? (login düğmesi kayboldu + editör var)"""
    try:
        durum = await page.evaluate(
            """() => ({
                editor: document.querySelectorAll('div.tiptap[contenteditable="true"]').length,
                giris_dugmesi: [...document.querySelectorAll('button, a')]
                    .some(b => /^(log in|log in or create account|sign up for free)$/i
                               .test((b.innerText || '').trim())),
                metin: (document.body.innerText || '').slice(0, 300)
            })"""
        )
    except Exception:
        return False
    if "invalid" in durum.get("metin", "").lower() or "incorrect" in durum.get("metin", "").lower():
        print("[Giriş] ❌ Arena kimlik bilgilerini reddetti (invalid/incorrect)", flush=True)
        return False
    basarili = bool(durum.get("editor")) and not durum.get("giris_dugmesi")
    print(f"[Giriş] {'✅ GİRİŞ BAŞARILI' if basarili else '❌ GİRİŞ DOĞRULANAMADI'}", flush=True)
    return basarili


async def _cerezleri_al(context) -> list[dict]:
    try:
        return await context.cookies()
    except Exception:
        return []


async def giris_yap_ve_cerez_al(paket: dict[str, Any] | None = None) -> list[dict] | None:
    """Arena'ya e-posta/şifre ile girer; BAŞARILIYSA çerezleri döndürür.

    Başarısızsa None döner (üretim durmaz, mevcut çerez korunur).
    """
    if not kimlik_var_mi():
        print("[Giriş] Kimlik secret'ları yok — otomatik giriş yapılmıyor", flush=True)
        return None

    # TARAYICI AÇMADAN ön kontrol: yazım hatası varsa 4 dakika boşa gitmesin
    gecerli, mesaj = eposta_on_kontrol()
    if not gecerli:
        print(f"[Giriş] ⛔ ÖN KONTROL: {mesaj}", flush=True)
        return None
    print(f"[Giriş] ✅ Ön kontrol: {mesaj}", flush=True)

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("[Giriş] Playwright yok", flush=True)
        return None

    from modules import arena_api

    try:
        async with async_playwright() as p:
            browser = await arena_api._tarayici_ac(p.chromium.launch, headless=True)
            context = await browser.new_context(viewport={"width": 1366, "height": 900})
            page = await context.new_page()
            await page.goto("https://arena.ai/agent/", wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(5000)
            await _modal_kapat(page, "(açılış)")

            if not await _giris_modalini_ac(page):
                print("[Giriş] Login modalı açılamadı", flush=True)
                await arena_api._tarayiciyi_kapat(browser)
                return None

            basarili = await _email_ile_giris(page)
            cerezler = await _cerezleri_al(context) if basarili else None
            await arena_api._tarayiciyi_kapat(browser)

            if basarili and cerezler:
                print(f"[Giriş] ✅ {len(cerezler)} çerez alındı — secret'a yazılacak", flush=True)
                return cerezler
            return None
    except Exception as e:
        print(f"[Giriş] Giriş hattı hatası: {str(e)[:140]}", flush=True)
        return None


def giris_yap_ve_secret_guncelle() -> bool:
    """SYNC: e-posta/şifre ile gir → çerezleri ARENA_COOKIES_JSON'a yaz.

    Başarılıysa True. Bu fonksiyon çerez ölü olduğunda çağrılır.
    """
    try:
        cerezler = asyncio.run(giris_yap_ve_cerez_al())
    except RuntimeError:
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as havuz:
            cerezler = havuz.submit(lambda: asyncio.run(giris_yap_ve_cerez_al())).result()
    if not cerezler:
        return False

    try:
        from modules import arena_cerez

        sonuc = arena_cerez.oturumdan_guncelle(cerezler, oturum_saglikli=True)
        return bool(sonuc.get("guncellendi"))
    except Exception as e:
        print(f"[Giriş] Çerez yazılamadı: {str(e)[:120]}", flush=True)
        return False

# Sık yazım hataları (2026-11-12 canlı olay: secret'a "gmal.com" girilmişti)
_YAYGIN_DOMAINLER = (
    "gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "live.com",
    "yahoo.com", "icloud.com", "yandex.com", "yandex.ru", "proton.me",
    "protonmail.com", "mail.ru", "gmx.com", "aol.com", "msn.com",
)


def _levenshtein(a: str, b: str) -> int:
    """İki metin arasındaki düzenleme mesafesi (klasik DP; yaklaşım YOK)."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    onceki = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        simdiki = [i]
        for j, cb in enumerate(b, 1):
            simdiki.append(
                min(
                    onceki[j] + 1,          # silme
                    simdiki[j - 1] + 1,     # ekleme
                    onceki[j - 1] + (ca != cb),  # değiştirme
                )
            )
        onceki = simdiki
    return onceki[-1]


def eposta_on_kontrol(eposta: str | None = None) -> tuple[bool, str]:
    """Tarayıcıyı AÇMADAN e-postayı doğrular (hızlı geri bildirim).

    Neden: Arena domaini reddettiğinde giriş 4 dakika sürüyordu. Yazım hatası
    (gmal.com) artık saniyeler içinde, anlaşılır mesajla yakalanır.
    """
    adres = (eposta if eposta is not None else os.environ.get("LMARENA_EMAIL", "")).strip()
    if not adres:
        return False, "LMARENA_EMAIL boş"
    if adres.count("@") != 1:
        return False, f"LMARENA_EMAIL geçersiz ('@' sayısı {adres.count('@')})"
    yerel, domain = adres.split("@")
    domain = domain.lower().strip(".")
    if not yerel or not domain:
        return False, "LMARENA_EMAIL geçersiz (yerel kısım/domain boş)"
    if "." not in domain:
        return False, f"LMARENA_EMAIL domaini geçersiz: '{domain}'"

    # Yazım hatası şüphesi: bilinen bir domaine 1 harf uzaklıkta mı?
    if domain not in _YAYGIN_DOMAINLER:
        for bilinen in _YAYGIN_DOMAINLER:
            if _levenshtein(domain, bilinen) <= 1:
                return False, (
                    f"YAZIM HATASI ŞÜPHESİ: '{domain}' → muhtemelen '{bilinen}'. "
                    "LMARENA_EMAIL secret'ını düzeltin."
                )
    return True, f"e-posta tamam (domain: {domain})"
