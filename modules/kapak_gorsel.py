"""Kapak görselini Arena AI ÜRETİR (2026-11-12 kullanıcı kararı).

KULLANICI TALİMATI (aynen): "Mevcut tüm kuralları çöpe at. Arena AI'ye şöyle
prompt ver: videonun içeriği hakkındaki tam metni ver, bu metni okusun ve buna
uygun Short video için kapak fotoğrafı oluştursun; kullanıcıları tıklamaya ve
izlemeye teşvik, etkileşim için gerekli tüm profesyonel şekilde üzerine
düşünülmüş olsun. Oluşturduğu resmi indir ve oluşturulan videonun ilk karesine
yerleştirilip seçilsin. Diğer tüm saçmalıkları çöpe at."

ÇÖPE ATILANLAR (bilinçli olarak SİLİNDİ, geri getirilmemeli):
  • A/B/C/D kapak adayları ve skor yarıştırması (okunabilirlik skoru, sınır testi)
  • "sok_baslik" (4 kelime) + "vurgu_kelime" + HEX renk JSON şeması
  • 1. kareden kapak türetme, yerel VS/Clash kapak üreticisi (kapak_uret)
  • Ayrı görsel API'leri (GEMINI/OPENAI anahtarı zorunluluğu)

YENİ AKIŞ (tek yol):
  1. Videonun TAM metni Arena'ya verilir (senaryo.tam_metin / diyaloglar).
  2. Arena metni okur, düşünür ve TEK bir görsel üretir; sayfadaki görsel
     yakalanır + indirilir.
  3. Görsel 1080x1920'ye kırpılır → kapak.
  4. Kapak, final videonun İLK KARESİNE yerleştirilir (kapak = 1. kare).
  5. Arena görsel üretemezse: video metninden yapılan tek kapak (video karesi +
     videonun kendi başlığı). Üretim DURMAZ, uydurma yok.
"""

from __future__ import annotations

import asyncio
import base64
import os
from pathlib import Path
from typing import Any

from modules import calisma_dizinleri

KAPAK_BOYUT = (1080, 1920)


# ---------------------------------------------------------------------------
# 1) Metin: videonun tam içeriği
# ---------------------------------------------------------------------------


def video_metni(paket: dict[str, Any]) -> str:
    """Videonun TAM metnini çıkarır (senaryo tam_metin → diyaloglar → başlık)."""
    senaryo = paket.get("senaryo") or {}
    tam = str(senaryo.get("tam_metin") or "").strip()
    if tam:
        return tam
    parcalar = [
        str(d.get("metin") or "").strip()
        for d in (senaryo.get("diyaloglar") or [])
        if str(d.get("metin") or "").strip()
    ]
    if parcalar:
        return "\n".join(parcalar)
    return str(paket.get("baslik") or senaryo.get("baslik") or "").strip()


# ---------------------------------------------------------------------------
# 2) Prompt: metni oku, düşün, tek görsel üret
# ---------------------------------------------------------------------------


def gorsel_promptu(paket: dict[str, Any]) -> str:
    """Arena'ya giden TEK prompt: tam metni oku → profesyonel kapak görseli üret."""
    metin = video_metni(paket)
    return (
        "Sen YouTube Shorts için kapak (thumbnail) tasarlayan bir görsel "
        "tasarımcısısın. Aşağıda bir videonun TAM METNİ var. Önce metni baştan "
        "sona dikkatlice oku, konuyu ve en şaşırtıcı noktayı belirle; sonra bu "
        "videoya kapak olacak TEK bir dikey (9:16) görsel ÜRET.\n\n"
        "GÖRSELİN AMACI: izleyici akışta kaydırırken durup tıklasın, sonuna kadar "
        "izlesin, beğenip yorum yazsın.\n\n"
        "TASARIM KURALLARI (profesyonel, üzerine düşünülmüş):\n"
        "1) Metnin en çarpıcı/sürpriz fikrini tek bir sahneyle anlat; soyut değil "
        "somut bir görüntü olsun.\n"
        "2) Güçlü görsel hiyerarşi: baskın tek bir özne, sade arka plan, yüksek "
        "kontrast, net siluet, merkezde/üst 2/3'te özne (altta kalan alan yazı ve "
        "arayüz için boş kalsın).\n"
        "3) Duygu ve merak: şaşkınlık, ölçek farkı, beklenmedik detay, 'bu nasıl "
        "olur' hissi. Abartılı sahte şok ifadeleri, korku, kan, şiddet, çıplaklık YOK.\n"
        "4) Renk: sıcak-soğuk kontrastı, tek baskın renk + tek vurgu rengi, "
        "doygun ama göz yormayan sinematik ışık.\n"
        "5) Stil: modern, sinematik, 3D/fotoğrafik gerçekçilik; stok görsel gibi "
        "jenerik değil, tek bir fikre odaklı.\n"
        "6) GÖRSELİN İÇİNE YAZI KOYMA. Hiçbir kelime, sayı, harf, logo, filigran "
        "olmasın (başlık sonradan eklenecek).\n"
        "7) 9:16 dikey, telefon ekranında küçük boyutta bile anlaşılır olsun.\n\n"
        "Şimdi görseli üret. Sadece görsel döndür; açıklama, metin veya kod yazma.\n"
        # KULLANICI BULGUSU (2026-11-13): Arena görsel ürettikten sonra
        # "Which image do you prefer?" diye soruyor; cevap alamayınca akış
        # bitmiyor ve görsel teslim edilmiyordu. Bu cümle istekte varsa
        # Arena sormadan doğrudan yapıyor.
        "Soru sorma, yap.\n\n"
        "=== VİDEO METNİ (TAM) ===\n"
        f"{metin}\n"
        "=== VİDEO METNİ SONU ==="
    )


# ---------------------------------------------------------------------------
# 3) Görseli yakala + indir
# ---------------------------------------------------------------------------


async def _sayfadaki_gorseli_indir(page, hedef: Path) -> Path | None:
    """Sayfada beliren üretilmiş görseli yakalar ve indirir.

    Strateji (sırayla): <img> kaynakları → canvas data URL → arka plan görselleri.
    """
    adaylar: list[str] = []
    try:
        adaylar = await page.evaluate(
            """() => {
                const out = [];
                for (const img of document.querySelectorAll('img')) {
                    const s = img.currentSrc || img.src || '';
                    if (s && (s.startsWith('data:image') || s.includes('blob:') ||
                              /\\.(png|jpe?g|webp)/i.test(s))) out.push(s);
                }
                for (const c of document.querySelectorAll('canvas')) {
                    try { out.push(c.toDataURL('image/png')); } catch (e) {}
                }
                for (const el of document.querySelectorAll('*')) {
                    const bg = getComputedStyle(el).backgroundImage || '';
                    const m = bg.match(/url\\("?([^")]+)"?\\)/);
                    if (m && m[1]) out.push(m[1]);
                }
                return out;
            }"""
        )
    except Exception as e:
        print(f"[Kapak] Sayfa tarama hatası: {str(e)[:100]}")
        return None

    # En büyük/en yeni görseller önce denenir (üretilen görsel genelde sonradır)
    # HTMLImageElement'lerin gerçek bitmap'ini canvas üzerinden data URL'e çevir
    # (Arena görseli blob: URL ile gösterirse requests ile indirilemez; kurtarma yolu)
    try:
        data_url_listesi = await page.evaluate(
            """() => {
                const out = [];
                for (const img of document.querySelectorAll('img')) {
                    const s = img.currentSrc || img.src || '';
                    if (!s.startsWith('blob:') || !img.complete || !img.naturalWidth) continue;
                    try {
                        const c = document.createElement('canvas');
                        c.width = img.naturalWidth; c.height = img.naturalHeight;
                        c.getContext('2d').drawImage(img, 0, 0);
                        out.push(c.toDataURL('image/png'));
                    } catch (e) {}
                }
                return out;
            }"""
        )
        adaylar = (adaylar or []) + list(data_url_listesi or [])
    except Exception:
        pass

    for kaynak in reversed(adaylar or []):
        try:
            if kaynak.startswith("data:image"):
                ham = kaynak.split(",", 1)[1]
                hedef.write_bytes(base64.b64decode(ham))
            elif kaynak.startswith("http") or kaynak.startswith("blob:"):
                if kaynak.startswith("blob:"):
                    continue
                import requests

                r = requests.get(kaynak, timeout=60)
                if r.status_code != 200 or len(r.content) < 20000:
                    continue
                hedef.write_bytes(r.content)
            else:
                continue
            if hedef.exists() and hedef.stat().st_size > 20000 and _gorsel_yeterli(hedef):
                return hedef
        except Exception:
            continue
    return None


def arena_kapak_gorseli_uret(paket: dict[str, Any]) -> Path | None:
    """SYNC sarmalayıcı — pipeline'dan böyle çağrılır (asyncio.run güvenli).

    Oturum bayrağı düşmüşse Playwright HİÇ açılmaz (boşa 45 sn bekleme yok).
    """
    from modules import arena_api

    if arena_api.oturum_doldu_mu():
        print("[Kapak] Arena oturumu yok — kapak video karesinden üretilecek")
        return None
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # Normal yol: loop yok → doğrudan çalıştır
        try:
            return asyncio.run(arena_kapak_gorseli_uret_async(paket))
        except Exception as e:
            print(f"[Kapak] Arena görsel hattı hatası: {str(e)[:140]}")
            return None
    # Zaten çalışan bir event loop var → ayrı thread'de çalıştır
    # (coroutine burada OLUŞTURULMAZ; "never awaited" uyarısı doğmaz)
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as havuz:
        return havuz.submit(
            lambda: asyncio.run(arena_kapak_gorseli_uret_async(paket))
        ).result()


async def arena_kapak_gorseli_uret_async(paket: dict[str, Any]) -> Path | None:
    """Arena'ya tam metni verir, ürettiği kapak görselini indirir."""
    from modules import arena_api

    if arena_api.oturum_doldu_mu():
        print("[Kapak] Arena oturumu yok — kapak video karesinden üretilecek")
        return None
    cookies_raw = os.environ.get("ARENA_COOKIES_JSON", "").strip()
    if not cookies_raw:
        print("[Kapak] ARENA_COOKIES_JSON yok — kapak video karesinden üretilecek")
        return None
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("[Kapak] Playwright yok — kapak video karesinden üretilecek")
        return None
    try:
        clean_cookie = arena_api._arena_sayfasi_hazirla(cookies_raw)
    except Exception as e:
        print(f"[Kapak] Çerez hazırlama hatası: {str(e)[:100]}")
        return None

    dosya_adi = str(paket.get("dosya_adi") or "video")
    cikis = calisma_dizinleri.OUTPUT_YOLU / f"{dosya_adi}_arena_kapak_ham.png"
    cikis.parent.mkdir(parents=True, exist_ok=True)
    prompt = gorsel_promptu(paket)
    print(f"[Kapak] Arena'ya tam video metni gönderildi ({len(video_metni(paket))} karakter)")

    try:
        async with async_playwright() as p:
            browser = await arena_api._tarayici_ac(p.chromium.launch, headless=True)
            context = await browser.new_context(viewport={"width": 1366, "height": 900})
            await context.add_cookies(
                [
                    {"name": "arena-auth-prod-v1.0", "value": clean_cookie,
                     "domain": "arena.ai", "path": "/"},
                    {"name": "arena_build_bucket", "value": "stable",
                     "domain": "arena.ai", "path": "/"},
                    {"name": "user_country_code", "value": "TR",
                     "domain": "arena.ai", "path": "/"},
                ]
            )
            page = await context.new_page()
            await page.goto("https://arena.ai/agent/", wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(3000)
            await arena_api._arena_riza_modalini_kapat(page)
            # ÖLÜ OTURUM FRENİ: Arena login'e yönlendirdiyse 8 dk boşa bekleme
            if not await arena_api.oturum_gercekten_acik_mi(page):
                arena_api._oturum_doldu_isaretle()
                print("[Kapak] ⛔ Arena oturumu YOK — kapak video karesinden üretilecek")
                await arena_api._tarayiciyi_kapat(browser)
                return None
            if not await arena_api._promptu_gonder(page, prompt):
                print("[Kapak] ⚠️ Prompt gönderilemedi — kapak video karesinden üretilecek")
                await arena_api._tarayiciyi_kapat(browser)
                return None
            gorsel = await _gorsel_bekle_ve_indir(page, cikis)
            if gorsel:
                # Çerez kendini beslesin (aynı oturumdan tazelenmiş çerez)
                try:
                    await arena_api._cerezi_tazele(context)
                except Exception:
                    pass
            await arena_api._tarayiciyi_kapat(browser)
            return gorsel
    except Exception as e:
        print(f"[Kapak] Arena görsel hattı hatası: {str(e)[:140]}")
        return None


async def _gorsel_bekle_ve_indir(page, hedef: Path) -> Path | None:
    """Görsel oluşana kadar (donmuş sayfa freniyle) bekler ve indirir."""
    from datetime import datetime

    idle_dk = float(os.environ.get("ARENA_IDLE_DK", "6") or 6)
    maks_dk = float(os.environ.get("ARENA_MAKS_DK", "15") or 15)
    baslangic = datetime.now()
    son_degisim = datetime.now()
    son_uzunluk = -1
    kalp = -99.0

    while True:
        await page.wait_for_timeout(3000)
        gecen = (datetime.now() - baslangic).total_seconds()
        try:
            body = await page.locator("body").inner_text()
        except Exception:
            body = ""
        if "Sign in to continue" in body or "Continue with Google" in body:
            print("[Kapak] ⛔ Oturum düşmüş — kapak video karesinden üretilecek")
            return None
        if "to agree" in body.lower() or "How it Works" in body:
            await page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(500)

        if len(body) != son_uzunluk:
            son_uzunluk = len(body)
            son_degisim = datetime.now()

        # Görsel var mı? (üretim genelde "<img ...>" ile belirir)
        try:
            sayi = await page.evaluate(
                "() => document.querySelectorAll('img').length"
                " + document.querySelectorAll('canvas').length"
            )
        except Exception:
            sayi = 0
        if sayi:
            indirilen = await _sayfadaki_gorseli_indir(page, hedef)
            if indirilen:
                print(f"[Kapak] ✅ Arena kapak görseli indirildi ({gecen:.0f} sn)")
                return indirilen

        if gecen - kalp >= 15:
            kalp = gecen
            print(f"[Kapak] ⏳ Arena görsel üretiyor… {int(gecen)} sn · {sayi} görsel öğesi",
                  flush=True)

        sessiz_dk = (datetime.now() - son_degisim).total_seconds() / 60
        if sessiz_dk > idle_dk or gecen / 60 > maks_dk:
            print(f"[Kapak] ⚠️ Görsel gelmedi ({gecen:.0f} sn) — video karesine düşülecek")
            return None


# ---------------------------------------------------------------------------
# 4) Kapak = 1. kare
# ---------------------------------------------------------------------------


def gorseli_karesine_oturt(ham: Path, hedef: Path) -> Path | None:
    """Görseli 1080x1920'ye kırpar (Shorts kapağı)."""
    try:
        from PIL import Image

        img = Image.open(ham).convert("RGB")
        oran = max(KAPAK_BOYUT[0] / img.width, KAPAK_BOYUT[1] / img.height)
        img = img.resize((int(img.width * oran) + 1, int(img.height * oran) + 1))
        sol = (img.width - KAPAK_BOYUT[0]) // 2
        ust = (img.height - KAPAK_BOYUT[1]) // 2
        img = img.crop((sol, ust, sol + KAPAK_BOYUT[0], ust + KAPAK_BOYUT[1]))
        hedef.parent.mkdir(parents=True, exist_ok=True)
        img.save(hedef, "JPEG", quality=94, optimize=True)
        return hedef if hedef.exists() else None
    except Exception as e:
        print(f"[Kapak] Kırpma hatası: {str(e)[:120]}")
        return None


def _gorsel_yeterli(yol: Path) -> bool:
    """Yakalanan görsel gerçekten kapak mı? (min 400x400 — logo/ikon/avatar değil)"""
    try:
        from PIL import Image

        with Image.open(yol) as img:
            return img.width >= 400 and img.height >= 400
    except Exception:
        return False
