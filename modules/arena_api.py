"""
BOBİ TV — Arena AI Yaratıcı Yönetmen & Pro Üretim Entegrasyonu v6.0
Mimari:
1. Arena AI (Playwright Headless) -> Master Loop JSON Senaryo (0.0s Kanca + Erkek/Kadın Diyalog + Twist + Kusursuz Döngü)
   (ARENA_COOKIES_JSON yoksa veya erişilemezse otomatik olarak modules/scenario.py v6.0 kuyruğuna/şablonlarına geçer)
2. modules/tts_engine.py v6.0 -> Ahmet + Emel Çift Ses + Nefes Kırpma + WordBoundary Senkronu
3. modules/video_render.py v6.0 -> Vektör Karakter Kartları + Karaoke Altyazı + SFX + Sidechain BGM (-20dB) + -14 LUFS + QC
4. modules/kapak_uret.py v6.0 -> Montserrat-ExtraBold Kapak
"""
import os
import re
import json
import base64
import asyncio
from pathlib import Path
from datetime import datetime

from modules.scenario import (
    SENARYO_SABLONLARI,
    KONU_ACIKLAMALARI,
    siradaki_kategori,
    kuyruktan_arena_senaryosu_al,
    senaryo_dogrula_ve_zenginlestir,
    senaryo_paketi_olustur,
)
from modules.tts_engine import senaryo_seslendir
from modules.video_render import video_render
from modules.kapak_uret import kapak_uret

KATEGORILER = [s["kategori"] for s in SENARYO_SABLONLARI]

# --- Arena DOM seçici sabitleri — TEK KAYNAK --------------------------------
# JS karşılığı: skills/arena-playwright-agent/scripts/arena-dom.mjs
# (EDITOR_FALLBACKS, SEND_SELECTORS, CONSENT_BUTTON_LABELS).
# Bu listeler değiştirilirse HER İKİ taraf da güncellenmeli;
# tests/test_arena_selector_parity.py ayrışmayı yakalar ve testi kırar.
ARENA_EDITOR_SELECTOR = 'div.tiptap[contenteditable="true"]'
ARENA_EDITOR_FALLBACKS = [
    ARENA_EDITOR_SELECTOR,
    'div[contenteditable="true"][role="textbox"]',
    'div[contenteditable="true"]',
    'textarea',
]
ARENA_SEND_SELECTORS = [
    'button[aria-label="Send message"]',
    'button[aria-label="Send Message"]',
    'button[data-testid="send-button"]',
    'button[type="submit"]',
]
ARENA_CONSENT_BUTTON_LABELS = ['Agree', 'Kabul et', 'Accept']


# --- Arena DOM seçici sabitleri — TEK KAYNAK --------------------------------
# JS karşılığı: skills/arena-playwright-agent/scripts/arena-dom.mjs
# (EDITOR_FALLBACKS, SEND_SELECTORS, CONSENT_BUTTON_LABELS).
# Bu listeler değiştirilirse HER İKİ taraf da güncellenmeli;
# tests/test_arena_selector_parity.py ayrışmayı yakalar ve testi kırar.
ARENA_EDITOR_SELECTOR = 'div.tiptap[contenteditable="true"]'
ARENA_EDITOR_FALLBACKS = [
    ARENA_EDITOR_SELECTOR,
    'div[contenteditable="true"][role="textbox"]',
    'div[contenteditable="true"]',
    'textarea',
]
ARENA_SEND_SELECTORS = [
    'button[aria-label="Send message"]',
    'button[aria-label="Send Message"]',
    'button[data-testid="send-button"]',
    'button[type="submit"]',
]
ARENA_CONSENT_BUTTON_LABELS = ['Agree', 'Kabul et', 'Accept']


def sanitize_cookie_json(raw_text: str) -> str:
    """Markdown link bozulmalarını ([arena.ai](http://arena.ai)) temizler."""
    return re.sub(r"\[([^\]]+)\]\(https?://[^)]+\)", r"\1", raw_text).strip()


def build_clean_arena_cookie(cookies: list) -> str:
    """
    arena-auth-prod-v1.0, v1.1 ... parçalarını isim sırasına göre birleştirir ve
    4 KB sınırının altında tek parça temiz base64 çerezi üretir.
    """
    chunks = sorted(
        [
            c for c in cookies
            if isinstance(c, dict) and str(c.get("name", "")).startswith("arena-auth-prod-v1")
        ],
        key=lambda x: x["name"],
    )
    if not chunks:
        raise ValueError("ARENA_COOKIES_JSON içinde 'arena-auth-prod-v1.*' çerezi bulunamadı.")

    chunk_vals = [str(c.get("value", "")) for c in chunks if c.get("value")]
    combined = "".join(chunk_vals)
    if combined.startswith("base64-"):
        combined = combined[len("base64-"):]

    minimal_session = None

    try:
        padded = combined + "=" * ((4 - len(combined) % 4) % 4)
        session_obj = json.loads(base64.b64decode(padded).decode("utf-8"))
        if session_obj.get("access_token"):
            u = session_obj.get("user") or {}
            minimal_session = {
                "access_token": session_obj["access_token"],
                "token_type": session_obj.get("token_type", "bearer"),
                "expires_in": session_obj.get("expires_in", 3600),
                "expires_at": session_obj.get("expires_at"),
                "refresh_token": session_obj.get("refresh_token"),
                "user": {
                    "id": u.get("id"),
                    "aud": u.get("aud", "authenticated"),
                    "role": u.get("role", "authenticated"),
                    "email": u.get("email"),
                },
            }
    except Exception:
        pass

    if not minimal_session:
        first = chunk_vals[0]
        if first.startswith("base64-"):
            first = first[len("base64-"):]
        first = first[: len(first) - (len(first) % 4)]
        text = base64.b64decode(first).decode("utf-8", errors="ignore")

        at = re.search(r'"access_token"\s*:\s*"([^"]+)"', text)
        rt = re.search(r'"refresh_token"\s*:\s*"([^"]+)"', text)
        exp = re.search(r'"expires_at"\s*:\s*(\d+)', text)
        uid = re.search(r'"user"\s*:\s*\{\s*"id"\s*:\s*"([^"]+)"', text)
        em = re.search(r'"email"\s*:\s*"([^"]+)"', text)

        if not at:
            raise ValueError("Çerez içinde 'access_token' çözümlenemedi.")

        minimal_session = {
            "access_token": at.group(1),
            "token_type": "bearer",
            "expires_in": 3600,
            "expires_at": int(exp.group(1)) if exp else 1794150284,
            "refresh_token": rt.group(1) if rt else "",
            "user": {
                "id": uid.group(1) if uid else "",
                "aud": "authenticated",
                "role": "authenticated",
                "email": em.group(1) if em else "",
            },
        }

    encoded = base64.b64encode(
        json.dumps(minimal_session, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    return f"base64-{encoded}"


def _ic_ice_json_ayikla(metin: str) -> dict | None:
    """İç içe (nested) diyalog dizisi barındıran JSON nesnesini güvenle ayıklar."""
    aday_metin = metin.strip()
    if "```json" in aday_metin:
        aday_metin = aday_metin.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in aday_metin:
        parcalar = aday_metin.split("```")
        if len(parcalar) >= 3:
            aday_metin = parcalar[1].strip()

    decoder = json.JSONDecoder()
    bulunanlar = []
    for i, ch in enumerate(aday_metin):
        if ch == "{":
            try:
                nesne, _ = decoder.raw_decode(aday_metin[i:])
                if isinstance(nesne, dict) and ("diyaloglar" in nesne or "satirlar" in nesne):
                    bulunanlar.append(nesne)
            except Exception:
                continue

    return bulunanlar[-1] if bulunanlar else None


async def arena_canli_senaryo_iste(video_no: int) -> dict | None:
    """Arena.ai Agent üzerinden canlı Master v6.0 Loop JSON senaryosu ister."""
    cookies_raw = os.environ.get("ARENA_COOKIES_JSON", "").strip()
    if not cookies_raw:
        return None

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("[Arena] Playwright kurulu değil, yerel v6.0 senaryo motoruna geçiliyor.")
        return None

    try:
        cookies_list = json.loads(sanitize_cookie_json(cookies_raw))
        clean_cookie = build_clean_arena_cookie(cookies_list)
    except Exception as e:
        print(f"[Arena] Çerez hazırlama uyarısı: {e}")
        return None

    kategori = siradaki_kategori(KATEGORILER, son_n=6)
    kategori_aciklamasi = KONU_ACIKLAMALARI.get(kategori, "özgün gündelik hayat komedisi")
    prompt = (
        f"Sen özgün Türkçe YouTube Shorts komedi yazarı ve yönetmenisin (Bölüm #{video_no}, Kategori: {kategori}: {kategori_aciklamasi}). "
        "Hiçbir araç (bash/search/write_file) ÇAĞIRMA, doğrudan tek bir geçerli JSON nesnesi döndür. "
        "KONU ÇEŞİTLİLİĞİ: İstenen kategoriye sadık kal; önceki videoların hikâyesini, esprisini veya karakterlerini kopyalama. "
        "Dönüşümlü türler: bar fıkraları, paradoks hikâyeleri, absürt komedi, absürt şakalar, çılgın ama zararsız hikâyeler, ters köşe fıkralar ve eğlenceli replik düelloları. "
        "İnsanların ırkı, ten rengi, etnik kökeni veya başka korunan kimliğini hedef alan aşağılayıcı şaka, hakaret ve stereotip üretme; çok kültürlü karakterleri eşit ve saygılı yaz. "
        "Kurallar: "
        "1) 7 veya 8 hızlı, doğal Türkçe diyalog cümlesi yaz; toplam en az 45, tercihen 50-65 konuşma kelimesi olsun. "
        "2) 2 özgün karakter konuşsun (biri erkek, diğeri kadın); cümleleri 6-12 kelime civarında tut. "
        "3) Süre hedefi 15-30 saniye; asla 15 saniyenin altına düşecek kadar kısa yazma. "
        "4) 1. cümle doğrudan olayın merak uyandıran sonucundan başlasın; sondan bir önceki ana cümlede güçlü, temiz bir ters köşe olsun. "
        "5) Son cümle doğal, kısa bir loop köprüsü olsun; zoraki veya dilbilgisi bozuk yarım cümle kurma. "
        "6) Şablon ofis komedisine sıkışma; kategori neyse ortamı, karakterleri ve kelime dağarcığını ona göre tamamen değiştir. "
        "Şema: "
        f'{{"kategori":"{kategori}","ortam_etiketi":"{kategori_aciklamasi[:70]}","ruh_hali":"komedi",'
        '"hook_ust_bant":"MAKS 4 KELİME ŞOK BAŞLIK!","baslik":"Merak Uyandıran Başlık 😱 #shorts",'
        '"twist_indeksi":5,"diyaloglar":['
        '{"karakter":"MÜDÜR","cinsiyet":"erkek","metin":"İşte tam bu yüzden...","ses":"sinirli","sfx":"whoosh"},'
        '{"karakter":"İK","cinsiyet":"kadin","metin":"Ama nasıl olur?","ses":"suprized","sfx":"pop"}'
        '],"sabit_yorum":"İzleyiciye tartışmalı soru 👇","etkilesim":"Arkadaşını etiketle!"}'
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1366, "height": 900})
        await context.add_cookies([
            {"name": "arena-auth-prod-v1.0", "value": clean_cookie, "domain": "arena.ai", "path": "/"},
            {"name": "arena_build_bucket", "value": "stable", "domain": "arena.ai", "path": "/"},
            {"name": "user_country_code", "value": "TR", "domain": "arena.ai", "path": "/"},
        ])
        page = await context.new_page()

        print(f"[Arena] Video #{video_no} ({kategori}) için Master Loop senaryosu isteniyor...")
        cevap = await _arena_sorgusu_yap(page, prompt, min_cevap_uzunlugu=120, timeout=130)
        await browser.close()

    if not cevap:
        return None

    ham_json = _ic_ice_json_ayikla(cevap)
    if not ham_json:
        print("[Arena] JSON ayrıştırılamadı, yerleşik v6.0 şablonuna geçiliyor.")
        return None

    senaryo = senaryo_dogrula_ve_zenginlestir(ham_json, video_no)
    tarih = datetime.now().strftime("%Y%m%d")
    dosya_adi = f"{tarih}_{video_no:04d}_{senaryo['kategori']}_arena"
    print(f"[Arena] ✅ Canlı Loop Senaryo alındı: {senaryo['baslik']}")
    return {
        "video_no": video_no,
        "dosya_adi": dosya_adi,
        "baslik": senaryo["baslik"],
        "aciklama": senaryo["sabit_yorum"],
        "senaryo": senaryo,
        "kaynak": "arena_canli",
        "olusturuldu": datetime.now().isoformat(),
    }


def _arena_sayfasi_hazirla(cookies_raw: str):  # pragma: no cover - Playwright
    """Ortak: Arena çerezlerinden temiz cookie + tarayıcı bağlamı hazırlar."""
    cookies_list = json.loads(sanitize_cookie_json(cookies_raw))
    return build_clean_arena_cookie(cookies_list)


async def arena_kapak_onerisi_al_async(paket: dict) -> dict | None:
    """Arena AI'den KAPAK önerisi ister (şok başlık + vurgu + renk).

    Kapak fotoğrafı için Arena desteği (kullanıcı isteği 2026-11-11).
    Senaryo akışıyla AYNI Playwright + çerez yolunu kullanır; erişilemezse
    None döner ve yerel kapak üreticisine düşülür (üretim DURMAZ).
    """
    cookies_raw = os.environ.get("ARENA_COOKIES_JSON", "").strip()
    if not cookies_raw:
        print("[Arena Kapak] ARENA_COOKIES_JSON yok — yerel kapak üreticisi kullanılacak")
        return None
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("[Arena Kapak] Playwright kurulu değil — yerel üreticiye geçiliyor")
        return None

    baslik = str(paket.get("baslik") or "")
    senaryo = paket.get("senaryo") or {}
    ilk_cumle = ""
    try:
        diyaloglar = senaryo.get("diyaloglar") or []
        if diyaloglar:
            ilk_cumle = str(diyaloglar[0].get("metin", ""))
    except Exception:
        ilk_cumle = ""
    prompt = (
        "Sen Türkçe YouTube Shorts kapak (thumbnail) tasarımcısısın. "
        "Sana video başlığı ve ilk replik veriliyor. Hiçbir araç ÇAĞIRMA, "
        "doğrudan tek bir geçerli JSON nesnesi döndür.\n"
        f"BAŞLIK: {baslik}\n"
        f"İLK REPLİK: {ilk_cumle[:120]}\n"
        "Kurallar:\n"
        "1) sok_baslik: MAKS 4 KELİME, büyük harf, merak uyandıran, yalan vaat yok.\n"
        "2) vurgu_kelime: sok_baslik içinden renklendirilecek TEK kelime.\n"
        "3) renk: vurgu için yüksek kontrastlı HEX renk (örn #FF2D55).\n"
        "4) gerekce: neden bu başlık kaydırma durdurur, 1 cümle.\n"
        "Şema: {\"sok_baslik\":\"MAKS 4 KELİME\",\"vurgu_kelime\":\"KELİME\","
        "\"renk\":\"#FF2D55\",\"gerekce\":\"tek cümle\"}"
    )

    try:
        clean_cookie = _arena_sayfasi_hazirla(cookies_raw)
    except Exception as e:
        print(f"[Arena Kapak] Çerez hazırlama uyarısı: {str(e)[:100]}")
        return None

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(viewport={"width": 1366, "height": 900})
            await context.add_cookies([
                {"name": "arena-auth-prod-v1.0", "value": clean_cookie, "domain": "arena.ai", "path": "/"},
                {"name": "arena_build_bucket", "value": "stable", "domain": "arena.ai", "path": "/"},
                {"name": "user_country_code", "value": "TR", "domain": "arena.ai", "path": "/"},
            ])
            page = await context.new_page()
            print(f"[Arena Kapak] '{baslik[:40]}' için kapak önerisi isteniyor...")
            cevap = await _arena_sorgusu_yap(page, prompt, min_cevap_uzunlugu=40, timeout=120)
            await browser.close()
    except Exception as e:
        print(f"[Arena Kapak] Tarayıcı hatası: {str(e)[:120]}")
        return None

    if not cevap:
        return None
    ham = _ic_ice_json_ayikla(cevap)
    if not isinstance(ham, dict) or not ham.get("sok_baslik"):
        print("[Arena Kapak] JSON ayrıştırılamadı — yerel üreticiye geçiliyor")
        return None
    print(f"[Arena Kapak] ✅ Öneri: {ham.get('sok_baslik')!r}")
    return ham


def arena_kapak_onerisi_al(paket: dict) -> dict | None:
    """Sync sarmalayıcı — kapak_arena.py bunu çağırır."""
    try:
        return asyncio.run(arena_kapak_onerisi_al_async(paket))
    except RuntimeError:
        # Zaten çalışan loop varsa yeni thread'de çalıştır
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as havuz:
            return havuz.submit(lambda: asyncio.run(arena_kapak_onerisi_al_async(paket))).result()
    except Exception as e:
        print(f"[Arena Kapak] Sync sarmalayıcı hatası: {str(e)[:120]}")
        return None


async def arena_video_uret(video_no: int, output_dir: str = "bobi_tv/output") -> dict | None:
    """
    Birleşik BOBİ TV v6.0 Pro Üretim Hattı:
    1. Senaryo: Arena kuyruğu -> Arena canlı -> Yerleşik v6.0 Loop Şablonu
    2. Kalite Kontrol: Loop + Hook + Timing + Dialogue (min 70 puan)
    3. Ses: Ahmet + Emel Çift Ses + Sıfır Ölü Boşluk + WordBoundary
    4. Görüntü & Miksaj: Vektör Karakter Kartları + Karaoke Altyazı + SFX + Sidechain BGM + -14 LUFS
    5. Kapak & QC: Montserrat-ExtraBold Kapak + ffprobe Doğrulama
    """
    from modules.senaryo_v7.kalite_kapisi import kalite_kapisindan_gecir, kalite_raporu_ozetle

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # 1. Senaryo Paketi
    paket = kuyruktan_arena_senaryosu_al(video_no)
    if not paket:
        paket = await arena_canli_senaryo_iste(video_no)
    if not paket:
        paket = senaryo_paketi_olustur(video_no)

    # 2. Kalite Kontrolü (YENİ)
    senaryo_raw = paket.get("senaryo", paket)
    try:
        from modules.senaryo_v7.models import Senaryo
        from modules.kalite_log import kalite_log_yaz

        if isinstance(senaryo_raw, dict):
            senaryo = Senaryo.from_dict(senaryo_raw)
        elif isinstance(senaryo_raw, Senaryo):
            senaryo = senaryo_raw
        else:
            senaryo = None

        if senaryo:
            kalite_raporu = kalite_kapisindan_gecir(senaryo, esik_puani=70)

            # Loglama
            kalite_log_yaz(video_no, {
                "toplam_puan": kalite_raporu.toplam_puan,
                "gecti": kalite_raporu.gecti,
                "loop_sonuc": {"puan": kalite_raporu.loop_sonuc.puan},
                "kanca_sonuc": {"puan": kalite_raporu.kanca_sonuc.puan},
                "zamanlama_sonuc": {"puan": kalite_raporu.zamanlama_sonuc.puan},
                "diyalog_sonuc": {"puan": kalite_raporu.diyalog_sonuc.puan},
                "oneriler": kalite_raporu.oneriler,
            })

            if kalite_raporu.gecti:
                print(f"[Kalite] ✅ Senaryo geçti: {kalite_raporu.toplam_puan}/100")
            else:
                print(f"[Kalite] ⚠️  Senaryo düşük puanlı: {kalite_raporu.toplam_puan}/100")
                print(kalite_raporu_ozetle(kalite_raporu))

                # Düşük puanlı ama devam et (uyarı olarak logla)
                if kalite_raporu.toplam_puan < 50:
                    print("[Kalite] ❌ Senaryo çok düşük kalitede, reddedildi.")
                    return None
    except Exception as e:
        print(f"[Kalite] Kontrol hatası (devam ediliyor): {e}")

    # 3. Çift Sesli TTS
    paket = senaryo_seslendir(paket)

    # 4. Pro Video Render + Ses Mastering + QC
    video_render(paket)

    # 5. KAPAK — Arena AI destekli (1. kare + Arena şok başlık, otomatik seçim)
    #    Kullanıcı isteği 2026-11-11: "kapak için Arena'dan destek alsın, ilk
    #    kareye yerleştirme yapıp seçilsin." Arena erişilemezse yerel üreticiye
    #    düşer (kapak_sec_ve_hazirla içinde) — üretim DURMAZ.
    try:
        from modules.kapak_arena import kapak_sec_ve_hazirla
        kapak_sec_ve_hazirla(paket)
    except Exception as e:
        print(f"[Kapak] Arena hattı hatası, yerel üreticiye düşülüyor: {str(e)[:120]}")
        kapak_uret(paket)

    return paket



async def _arena_sorgusu_yap(page, prompt: str, min_cevap_uzunlugu: int = 100, timeout: int = 130) -> str | None:
    try:
        await page.goto("https://arena.ai/agent/", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)

        ilk_body = await page.locator("body").inner_text()
        if "MIDDLEWARE_INVOCATION_FAILED" in ilk_body:
            print("[Arena] HATA: 500 Middleware hatası.")
            return None

        editor = page.locator('div.tiptap[contenteditable="true"]')
        try:
            await editor.wait_for(state="visible", timeout=15000)
        except Exception:
            print("[Arena] Tiptap editörü görünmedi.")
            return None

        await editor.click()
        await page.wait_for_timeout(300)
        await page.keyboard.insert_text(prompt)
        await page.wait_for_timeout(400)

        send_btn = page.locator('button[aria-label="Send message"]')
        await send_btn.click(force=True)

        for _ in range(15):
            await page.wait_for_timeout(1000)
            if page.url != "https://arena.ai/agent/":
                break

        prompt_ilk_satir = prompt.splitlines()[0][:55]
        son_uzunluk = 0
        stable_ticks = 0
        baslangic = datetime.now()

        while (datetime.now() - baslangic).total_seconds() < timeout:
            await page.wait_for_timeout(2000)
            body = await page.locator("body").inner_text()

            if "Sign in to continue" in body or "Continue with Google" in body:
                print("[Arena] Oturum süresi dolmuş (Login modalı açıldı).")
                return None

            cevap = _cevabi_ayikla(body, prompt, prompt_ilk_satir)
            dusunuyor = "orchestrating" in body.lower() or "thinking" in body.lower()
            bitti_isareti = "Was this task successful?" in body

            if bitti_isareti and len(cevap) >= min_cevap_uzunlugu:
                return cevap

            if len(body) != son_uzunluk or dusunuyor:
                son_uzunluk = len(body)
                stable_ticks = 0
            else:
                stable_ticks += 1
                if stable_ticks >= 5 and len(cevap) >= min_cevap_uzunlugu:
                    return cevap

        return None
    except Exception as e:
        print(f"[Arena] Sorgu hatası: {e}")
        return None


def _cevabi_ayikla(full_body: str, prompt: str, prompt_ilk_satir: str) -> str:
    prompt_son_satir = [s.strip() for s in prompt.splitlines() if s.strip()][-1][:60]
    idx = full_body.rfind(prompt)
    if idx != -1:
        slice_text = full_body[idx + len(prompt):].strip()
    else:
        idx_end = full_body.rfind(prompt_son_satir)
        if idx_end != -1:
            slice_text = full_body[idx_end + len(prompt_son_satir):].strip()
        else:
            idx2 = full_body.rfind(prompt_ilk_satir)
            slice_text = full_body[idx2 + len(prompt_ilk_satir):].strip() if idx2 != -1 else ""

    for marker in ("\nWas this task successful?", "\nWorkspace\n", "\nConnectors\n"):
        m_idx = slice_text.find(marker)
        if m_idx != -1:
            slice_text = slice_text[:m_idx].strip()

    slice_text = re.sub(r"\n\d+s\s*\|\s*just now[\s\S]*$", "", slice_text, flags=re.IGNORECASE).strip()
    lines = list(slice_text.splitlines())
    if lines and re.match(r"^Thought for \d+", lines[0].strip(), re.IGNORECASE):
        lines = lines[1:]
        while lines and not lines[0].strip():
            lines.pop(0)
    return "\n".join(lines).strip()


if __name__ == "__main__":
    import sys
    v_no = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    res = asyncio.run(arena_video_uret(v_no))
    if res:
        print(json.dumps({k: v for k, v in res.items() if k != "ses_dosyalari"}, ensure_ascii=False, indent=2))
    else:
        sys.exit(1)
