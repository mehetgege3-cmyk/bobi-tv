"""
BOBİ TV — Arena AI API Entegrasyonu v1.0
Playwright ile Arena.ai'dan senaryo + animasyon kodu iste.
Tam otonom, Python subprocess'te çalışabilir.
"""
import os
import json
import asyncio
import tempfile
import re
from pathlib import Path
from datetime import datetime


async def arena_video_uret(video_no: int, output_dir: str = "bobi_tv/output") -> dict | None:
    """
    Arena AI'dan tamamen otonom video üretim:
    1. Senaryo iste (kısa absürt Türkçe)
    2. Animasyon Python kodu iste
    3. Kodu çalıştır, video oluştur
    
    Döner: {baslik, aciklama, final_video, ...} veya None
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("[Arena] Playwright yok. pip install playwright")
        return None

    cookies_json = os.environ.get("ARENA_COOKIES_JSON", "")
    if not cookies_json:
        print("[Arena] ARENA_COOKIES_JSON yok.")
        return None

    # Cookie'yi parse et
    try:
        cookies = json.loads(cookies_json)
    except Exception as e:
        print(f"[Arena] Cookie parse hatası: {e}")
        return None

    # Arena auth cookie'sini çıkar
    arena_cookie = None
    for c in cookies:
        if c.get("name", "").startswith("arena-auth-prod-v1."):
            arena_cookie = c.get("value", "")
            if arena_cookie:
                break

    if not arena_cookie:
        print("[Arena] Auth cookie bulunamadı")
        return None

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    tarih = datetime.now().strftime("%Y%m%d")
    video_cikti = f"{output_dir}/{tarih}_{video_no:04d}_arena.mp4"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})

        # Cookie'yi ekle
        await context.add_cookies([
            {
                "name": "arena-auth-prod-v1.0",
                "value": arena_cookie,
                "domain": "arena.ai",
                "path": "/"
            }
        ])

        page = await context.new_page()

        # === ADIM 1: Senaryo iste ===
        print(f"[Arena] Video #{video_no}: Senaryo oluşturuluyor...")
        senaryo = await _arena_senaryo_uret(page, video_no)
        if not senaryo:
            await browser.close()
            return None

        # === ADIM 2: Animasyon Python kodu iste ===
        print(f"[Arena] Video #{video_no}: Python kodu yazılıyor...")
        kod = await _arena_kod_uret(page, senaryo, video_cikti)
        if not kod:
            await browser.close()
            return None

        await browser.close()

    # === ADIM 3: Kodu çalıştır ===
    print(f"[Arena] Video #{video_no}: Animasyon render ediliyor...")
    basari, metadata = _kodu_calistir(kod, video_cikti)

    if basari and Path(video_cikti).exists():
        boyut = Path(video_cikti).stat().st_size // (1024 * 1024)
        print(f"[Arena] ✅ Video hazır: {video_cikti} ({boyut}MB)")

        return {
            "video_no": video_no,
            "final_video": video_cikti,
            "baslik": metadata.get("baslik", f"BOBİ TV #{video_no} 🎬"),
            "aciklama": metadata.get("aciklama", "BOBİ TV — Absürt Türkçe Shorts"),
            "hashtag": metadata.get("hashtag", "#shorts #komedi #türkçe"),
            "olusturuldu": datetime.now().isoformat(),
        }

    print(f"[Arena] ❌ Video oluşturulamadı")
    return None


async def _arena_senaryo_uret(page, video_no: int) -> str | None:
    """Arena'dan kısa absürt Türkçe senaryo iste."""
    prompt = f"""Türkçe absürt komedi senaryo yaz. 
4-5 satır diyalog, son cümlesi twist/şok bitirme olsun.
Kısa ve viral potansiyeli yüksek.
Örnek: "Buzdolabım bana küstü / Açısı gittim / Kapısı bana ters ters baktı / Ben de ona öfkelendim / Evden çıktım — adam boş!"

Senaryo #{video_no}:"""

    return await _arena_sorgusu_yap(page, prompt, beklenen_uzunluk=100)


async def _arena_kod_uret(page, senaryo: str, video_cikti: str) -> str | None:
    """Arena'dan PIL + FFmpeg Python animasyon kodu iste."""
    prompt = f"""Türkçe YouTube Shorts animasyon videosu için çalıştırılabilir Python kodu yaz.

Gerekli:
- 1080x1920 px (9:16 format), 30 FPS, ~8 saniye
- Koyu gradient arka plan (lacivert → mor)
- Senaryo diyalogları: beyaz metin, ortada, sırayla
- Watermark: "BOBI TV" küçük, alt köşe
- Çıktı: {video_cikti}

Senaryo:
{senaryo}

Kodun sonunda JSON print et:
{{"baslik": "...", "aciklama": "...", "hashtag": "..."}}

Sadece Python kodu döndür (import dahil, markdown yok)."""

    kod = await _arena_sorgusu_yap(page, prompt, beklenen_uzunluk=500)

    if kod:
        # Kod bloğu varsa çıkar
        if "```python" in kod:
            kod = kod.split("```python")[1].split("```")[0].strip()
        elif "```" in kod:
            parts = kod.split("```")
            if len(parts) >= 3:
                kod = parts[1].strip()

    return kod


async def _arena_sorgusu_yap(page, prompt: str, beklenen_uzunluk: int = 100, timeout: int = 60) -> str | None:
    """
    Arena'ya sorgu yap, cevabı döndür.
    - Yeni chat aç
    - Prompt gönder
    - Cevap bekle (stable olana kadar)
    - Cevabı parse et ve döndür
    """
    try:
        # Ana sayfa
        await page.goto("https://arena.ai/agent/", wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(1000)

        # Input alanını bul
        input_selector = 'div.tiptap[contenteditable="true"], textarea[placeholder*="Ask"], input[placeholder*="Ask"]'
        try:
            await page.wait_for_selector(input_selector, timeout=5000)
        except:
            print("[Arena] Input alanı bulunamadı, deneme 2...")
            # Fallback
            input_selector = '[contenteditable="true"]'
            await page.wait_for_selector(input_selector, timeout=5000)

        # Prompt yaz
        input_elem = page.locator(input_selector).first
        await input_elem.click()
        await input_elem.fill(prompt)
        await page.wait_for_timeout(500)

        # Gönder (Enter veya Send butonu)
        send_btn = page.locator('button[aria-label="Send"], button:has-text("Send")')
        if await send_btn.is_visible():
            await send_btn.click()
        else:
            await input_elem.press("Enter")

        await page.wait_for_timeout(1000)

        # Cevabı polling ile bekle
        cevap = await _cevap_bekle(page, beklenen_uzunluk, timeout)
        return cevap

    except Exception as e:
        print(f"[Arena] Sorgu hatası: {e}")
        return None


async def _cevap_bekle(page, min_uzunluk: int = 100, timeout: int = 60) -> str | None:
    """
    Cevabı polling ile bekle.
    - Stable olana kadar (4 ardışık poll'da değişim yok)
    - Minimum uzunluk
    """
    son_uzunluk = 0
    stable_ticks = 0
    baslangic_zaman = datetime.now()

    for _ in range(timeout * 2):  # 2sn interval = timeout * 2 poll
        await page.wait_for_timeout(500)

        body = await page.locator("body").inner_text()
        uzunluk = len(body)

        # Düşünüyor mu?
        dusunuyor = "thought for" in body.lower() or "thinking" in body.lower() or "orchestrating" in body.lower()

        if uzunluk > son_uzunluk or dusunuyor:
            son_uzunluk = uzunluk
            stable_ticks = 0
        else:
            stable_ticks += 1
            if stable_ticks >= 4 and uzunluk > min_uzunluk:
                # Cevabı parse et
                return _cevapi_parse_et(body)

        # Timeout kontrol
        if (datetime.now() - baslangic_zaman).total_seconds() > timeout:
            print(f"[Arena] Cevap timeout ({timeout}sn)")
            return None

    return None


def _cevapi_parse_et(body: str) -> str | None:
    """Body text'ten gerçek cevabı çıkar."""
    satirlar = body.split("\n")

    # "--- CEVAP ---" veya "Thought for X" sonrasını al
    cevap_baslangic = None
    for i, satir in enumerate(satirlar):
        if "---" in satir and "cevap" in satir.lower():
            cevap_baslangic = i + 1
            break
        elif "thought for" in satir.lower():
            cevap_baslangic = i + 1
            break

    if cevap_baslangic is None:
        # Body'nin son %70'ini al (cevap kısmı)
        cevap_baslangic = len(satirlar) // 3

    cevap = "\n".join(satirlar[cevap_baslangic:]).strip()

    # Boş lines'ı temizle
    cevap = "\n".join(l for l in cevap.split("\n") if l.strip())

    # UI elements'ı çıkar
    cevap = re.sub(r"(Chat URL|Was this task|^(Yes|No|Keep|Workspace|Connectors|Agent|Auto)$)", "", cevap, flags=re.MULTILINE)

    return cevap.strip() if len(cevap.strip()) > 50 else None


def _kodu_calistir(kod: str, video_cikti: str) -> tuple:
    """Python kodunu çalıştır, metadata parse et. Döner: (basari, metadata)"""
    import subprocess
    import tempfile

    metadata = {
        "baslik": "BOBİ TV Absürt #Shorts",
        "aciklama": "BOBİ TV — Her gün absürt Türkçe Shorts!",
        "hashtag": "#shorts #komedi #türkçe"
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        # Auto-pip
        on = "import subprocess, sys\nfor pkg in ['Pillow','numpy']:\n    try:\n        __import__(pkg.lower().replace('pillow','PIL'))\n    except:\n        subprocess.run([sys.executable,'-m','pip','install',pkg,'-q'])\n"
        f.write(on + "\n" + kod)
        tmp = f.name

    try:
        result = subprocess.run(
            ["python3", tmp],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0:
            # Metadata ara
            for satir in result.stdout.split("\n"):
                if "{" in satir and "baslik" in satir:
                    try:
                        meta = json.loads(satir)
                        metadata.update(meta)
                    except:
                        pass

            if Path(video_cikti).exists():
                return True, metadata

        print(f"[Kod] Hata: {result.stderr[:300]}")
        return False, metadata

    except subprocess.TimeoutExpired:
        print("[Kod] Timeout")
        return False, metadata
    except Exception as e:
        print(f"[Kod] Hatası: {e}")
        return False, metadata
    finally:
        Path(tmp).unlink(missing_ok=True)


# CLI kullanım
if __name__ == "__main__":
    import sys

    video_no = int(sys.argv[1]) if len(sys.argv) > 1 else 1

    result = asyncio.run(arena_video_uret(video_no))
    if result:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("FAIL")
        sys.exit(1)
