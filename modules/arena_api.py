"""
BOBİ TV — Arena AI Yaratıcı Yönetmen & Pro Üretim Entegrasyonu v6.0
Mimari:
1. Arena AI (Playwright Headless) -> Master Loop JSON Senaryo (0.0s Kanca + Erkek/Kadın Diyalog + Twist + Kusursuz Döngü)
   (ARENA_COOKIES_JSON yoksa veya erişilemezse otomatik olarak modules/scenario.py v6.0 kuyruğuna/şablonlarına geçer)
2. modules/tts_engine.py v6.0 -> Ahmet + Emel Çift Ses + Nefes Kırpma + WordBoundary Senkronu
3. modules/video_render.py v6.0 -> Vektör Karakter Kartları + Karaoke Altyazı + SFX + Sidechain BGM (-20dB) + -14 LUFS + QC
4. modules/kapak_hatti.py -> Arena metni okur, kapak görseli videonun 1. karesine
"""
import os
import re
import json
import base64
import asyncio
from pathlib import Path
from datetime import UTC, datetime

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


def _json_nesnesi_ayikla(metin: str, gerekli_anahtarlar: tuple[str, ...]) -> dict | None:
    """Metindeki JSON nesnesini, verilen anahtarlardan birini içeren ilk/ son
    nesne olarak ayıklar. Kapak önerisi gibi TEK NESNE döndüren yanıtlar için
    kullanılır (senaryo ayıklayıcısı "diyaloglar" arar, kapak yanıtında yok)."""
    if not metin:
        return None
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
        if ch != "{":
            continue
        try:
            nesne, _ = decoder.raw_decode(aday_metin[i:])
        except Exception:
            continue
        if isinstance(nesne, dict) and any(k in nesne for k in gerekli_anahtarlar):
            bulunanlar.append(nesne)
    return bulunanlar[-1] if bulunanlar else None


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
    if oturum_doldu_mu():
        print("[Arena] Oturum dolmuş (bu koşuda tespit edildi) — atlandı.")
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
        browser = await _tarayici_ac(p.chromium.launch, headless=True)
        context = await browser.new_context(viewport={"width": 1366, "height": 900})
        await context.add_cookies([
            {"name": "arena-auth-prod-v1.0", "value": clean_cookie, "domain": "arena.ai", "path": "/"},
            {"name": "arena_build_bucket", "value": "stable", "domain": "arena.ai", "path": "/"},
            {"name": "user_country_code", "value": "TR", "domain": "arena.ai", "path": "/"},
        ])
        page = await context.new_page()

        print(f"[Arena] Video #{video_no} ({kategori}) için Master Loop senaryosu isteniyor...")
        cevap = await _arena_sorgusu_yap(page, prompt, min_cevap_uzunlugu=120)
        await _tarayiciyi_kapat(browser)

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


async def arena_kisa_cevap_al_async(prompt: str) -> str | None:
    """Arena'ya serbest metin sorusu sorar ve DÜZ METİN cevap döndürür.

    KULLANICI FİKRİ (2026-11-11): izleyici yorumlarını Arena'ya gönderip
    gelen cevabı yoruma yazmak. Bu fonksiyon "serbest sohbet" yoludur
    (senaryo JSON'u ya da kapak JSON'u değil).

    Çerez yoksa/erişilemezse None döner → çağıran taraf güvenli yedek metne
    düşer (`modules/yorum_cevap.guvenli_yedek_cevap`). Üretim DURMAZ.
    """
    cookies_raw = os.environ.get("ARENA_COOKIES_JSON", "").strip()
    if not cookies_raw:
        print("[Arena Cevap] ARENA_COOKIES_JSON yok — güvenli yedeğe düşülecek")
        return None
    if oturum_doldu_mu():
        print("[Arena Cevap] Oturum dolmuş (bu koşuda daha önce tespit edildi) — atlandı")
        return None
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("[Arena Cevap] Playwright kurulu değil — güvenli yedeğe düşülecek")
        return None

    try:
        clean_cookie = _arena_sayfasi_hazirla(cookies_raw)
    except Exception as e:
        print(f"[Arena Cevap] Çerez hazırlama uyarısı: {str(e)[:100]}")
        return None

    try:
        async with async_playwright() as p:
            browser = await _tarayici_ac(p.chromium.launch, headless=True)
            context = await browser.new_context(viewport={"width": 1366, "height": 900})
            await context.add_cookies([
                {"name": "arena-auth-prod-v1.0", "value": clean_cookie,
                 "domain": "arena.ai", "path": "/"},
                {"name": "arena_build_bucket", "value": "stable",
                 "domain": "arena.ai", "path": "/"},
                {"name": "user_country_code", "value": "TR",
                 "domain": "arena.ai", "path": "/"},
            ])
            page = await context.new_page()
            print("[Arena Cevap] Arena'ya soruluyor (kısa cevap)...")
            cevap = await _arena_sorgusu_yap(page, prompt, min_cevap_uzunlugu=20)
            # Kullanıcı isteği ("Yap"): oturum sağlıklıysa TAZELENMİŞ çerezi
            # secret'a geri yaz → kullanıcı çerezi bir kez verir, sistem besler.
            if cevap:
                await _cerezi_tazele(context)
            await _tarayiciyi_kapat(browser)
    except Exception as e:
        print(f"[Arena Cevap] Tarayıcı hatası: {str(e)[:120]}")
        return None

    if not cevap:
        return None
    print(f"[Arena Cevap] ✅ {cevap[:80]!r}")
    return cevap


def arena_kisa_cevap_al(prompt: str) -> str | None:
    """Sync sarmalayıcı — `modules/yorum_cevap.py` bunu çağırır."""
    try:
        return asyncio.run(arena_kisa_cevap_al_async(prompt))
    except RuntimeError:
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as havuz:
            return havuz.submit(
                lambda: asyncio.run(arena_kisa_cevap_al_async(prompt))
            ).result()
    except Exception as e:
        print(f"[Arena Cevap] Sync sarmalayıcı hatası: {str(e)[:120]}")
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

    # 1.5. KANCA MOTORU (A1 — 2026-11-11): ilk 1.5 saniye kancası zorunlu.
    #      TTS'den ÖNCE çalışır; üst bant + ilk replik + tts[0] kancayla yazılır.
    #      Kanca hatası üretimi DURDURMAZ (ölçüm loglanır, eski metin kalır).
    try:
        from modules.senaryo_v7.kanca_motoru import paket_kancasini_uygula

        kanca_ozeti = paket_kancasini_uygula(paket, video_no)
        if kanca_ozeti.get("uygulandi"):
            print(
                f"[Kanca] ✅ {kanca_ozeti['form']} formu ({kanca_ozeti['puan']}/100): "
                f"\"{kanca_ozeti['metin']}\""
            )
        else:
            print(f"[Kanca] ⚠️  uygulanamadı: {kanca_ozeti.get('gerekce')}")
    except Exception as e:
        print(f"[Kanca] Motor hatası (devam ediliyor): {str(e)[:120]}")

    # 1.6. DÖNGÜ UYGULAMA (2026-11-11 canlı test bulgusu): kalite kapısı 68/100
    #      ile KALDI çünkü döngü puanı 0'dı (son cümle "..." ile bitmiyor, ilk
    #      cümle bağlaçla başlamıyor). Öneri üretiliyor ama UYGULANMIYORDU.
    #      Burada düzeltilir; hemen ardından kalite kapısı yeniden puanlar.
    #      Hata üretimi DURDURMAZ.
    try:
        from modules.senaryo_v7.loop_validator import dongu_uygula

        senaryo_dict = paket.get("senaryo")
        if isinstance(senaryo_dict, dict):
            from modules.senaryo_v7.models import Senaryo

            senaryo_obj = Senaryo.from_dict(senaryo_dict)
            dongu = dongu_uygula(senaryo_obj)
            if dongu.uygulandi:
                # Düzeltilmiş diyalogları pakete geri yaz (TTS/render bunu okur)
                senaryo_dict["diyaloglar"] = [d.to_dict() for d in senaryo_obj.diyaloglar]
                if senaryo_obj.tts_metinleri:
                    senaryo_dict["tts_metinleri"] = list(senaryo_obj.tts_metinleri)
                print(
                    f"[Döngü] ✅ Uygulandı — döngü puanı {dongu.puan}/100 "
                    '(son cümle "...", ilk cümle bağlaçla)'
                )
    except Exception as e:
        print(f"[Döngü] Uygulama hatası (devam ediliyor): {str(e)[:120]}")

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
                "kanca_sonuc": {
                    "puan": kalite_raporu.kanca_sonuc.puan,
                    "form": (paket.get("kanca_ozeti") or {}).get("form", ""),
                    "motor_puan": (paket.get("kanca_ozeti") or {}).get("puan", 0),
                    "metin": (paket.get("kanca_ozeti") or {}).get("metin", ""),
                },
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

    # 5. KAPAK — tek yol: Arena tam metni okur, kapak GÖRSELİ üretir,
    #    görsel videonun 1. karesine yerleşir (modules/kapak_hatti.py).
    from modules.kapak_hatti import kapak_uret_ve_yerlestir

    kapak_uret_ve_yerlestir(paket)

    return paket



#: Arena yanıt sürelerinin kalıcı kaydı (panel + rapor bunu okur).
ARENA_SURE_YOLU = Path("bobi_tv/state/arena_sure.json")


def _arena_sure_kaydet(saniye: float, karakter: int, dusunme: str = "") -> None:
    """Arena'nın GERÇEK yanıt süresini state'e yazar (varsayım değil, ölçüm).

    Kullanıcı isteği (2026-11-11): süreç "anlık gösterilsin". Log tek başına
    kaybolur; panelin ve raporun okuyabilmesi için son 20 ölçüm saklanır.
    """
    try:
        try:
            veri = json.loads(ARENA_SURE_YOLU.read_text(encoding="utf-8"))
        except Exception:
            veri = {}
        olcumler = list(veri.get("olcumler") or [])
        olcumler.append({
            "zaman": datetime.now(UTC).isoformat(),
            "saniye": round(float(saniye), 1),
            "karakter": int(karakter),
            "arena_dusunme": dusunme,
        })
        olcumler = olcumler[-20:]
        sureler = [o["saniye"] for o in olcumler]
        ARENA_SURE_YOLU.parent.mkdir(parents=True, exist_ok=True)
        ARENA_SURE_YOLU.write_text(
            json.dumps({
                "son": olcumler[-1],
                "ortalama": round(sum(sureler) / len(sureler), 1),
                "en_uzun": max(sureler),
                "ornek": len(olcumler),
                "olcumler": olcumler,
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        print(f"[Arena] süre kaydı yazılamadı: {str(e)[:80]}", flush=True)


#: Çerez süresi dolduğunda her çağrıda 3,5 dakika boşa beklemeyi engeller.
#: CANLI KANIT (koşu 43143883459): içerik + kapak için iki kez denendi, ikisi de
#: "Oturum süresi dolmuş (Login modalı açıldı)" ile döndü → ~7 dk boşa gitti.
_OTURUM_DOLDU = {"deger": False}


def oturum_doldu_mu() -> bool:
    return bool(_OTURUM_DOLDU["deger"])


def oturum_bayragini_sifirla() -> None:
    """Test/elle kurtarma için bayrağı temizler."""
    _OTURUM_DOLDU["deger"] = False


def _oturum_doldu_isaretle() -> None:
    if not _OTURUM_DOLDU["deger"]:
        print(
            "[Arena] ⛔ ARENA_COOKIES_JSON SÜRESİ DOLMUŞ — çerez yenilenmeli. "
            "Bu koşuda Arena atlanıyor, üretim doğrulanmış bankadan sürecek.",
            flush=True,
        )
    _OTURUM_DOLDU["deger"] = True


async def _tarayici_ac(async_playwright_fn, *args, **kwargs):
    """Tarayıcıyı açar; açılış asılı kalırsa beklemeyi keser (45 sn).

    Teşhis (koşu 43145587605): oturum dolduğunda "ara" süre 3 dk 23 sn
    (03:04:47 tespit → 03:08:10 banka) çıktı; browser.close() artık 15 sn'de
    kesiliyor, kalan süre Chromium'un kendisinin asılı kalmasından geliyor.
    Bu bir cevap bekleme timeout'u DEĞİL — yalnız tarayıcı açma freni.
    """
    import asyncio

    return await asyncio.wait_for(async_playwright_fn(*args, **kwargs), timeout=45)


async def _cerezi_tazele(context) -> None:
    """Oturumdaki güncel Arena çerezlerini GitHub secret'ına yazar (best effort)."""
    import asyncio

    try:
        cerezler = await context.cookies()
        await asyncio.to_thread(_cerez_modulu().oturumdan_guncelle, cerezler)
    except Exception as e:  # asla üretimi düşürmez
        print(f"[Çerez] Tazeleme atlandı: {str(e)[:100]}")


def _cerez_modulu():
    from modules import arena_cerez

    return arena_cerez


async def _tarayiciyi_kapat(browser) -> None:
    """Tarayıcıyı kapatır; kapanma asılı kalırsa beklemeyi keser.

    Bu bir "Arena düşünme süresi" timeout'u DEĞİL (o yasak). Sorun şu:
    oturum düştüğünde `browser.close()` ~4 dakika asılı kalıyordu
    (koşu 43144741768: 02:57:28 tespit → 03:01:44 banka dönüşü).
    """
    import asyncio
    from contextlib import suppress

    with suppress(Exception):
        await asyncio.wait_for(browser.close(), timeout=15)


async def _promptu_gonder(page, prompt: str) -> bool:
    """Editöre yazar ve gönderir; GÖNDERİLDİĞİNİ DOĞRULAR.

    CANLI BULGU (2026-11-12): "Send message" düğmesine tıklanınca düğme mevcut
    ama gönderim sessizce olmuyordu (düğme pasif/devre dışı). Eski sürüm yine de
    `True` dönüyordu → kapak hattı 8 dakika boş sayfada bekliyordu ve log'a
    "gönderildi" yazıyordu. Bu SESSİZ YALANDI.

    Yeni sözleşme: editör boşaldıysa/Enter ile gönderim olduysa True; aksi hâlde
    False ve "GÖNDERİLEMEDİ" yazar. Çağıran taraf buna göre yedek yola düşer.
    """
    editor = page.locator('div.tiptap[contenteditable="true"]')
    try:
        await editor.wait_for(state="visible", timeout=30000)
    except Exception:
        print("[Arena] Editör görünmedi.", flush=True)
        return False

    async def _editor_bos() -> bool:
        try:
            return not (await editor.inner_text()).strip()
        except Exception:
            return False

    await editor.click()
    await page.wait_for_timeout(300)
    await page.keyboard.insert_text(prompt)
    await page.wait_for_timeout(600)

    # 1) Gönder düğmesi: görünür + etkin olmalı
    gonderildi = False
    try:
        dugme = page.locator('button[aria-label="Send message"]').first
        if await dugme.count():
            try:
                await dugme.wait_for(state="visible", timeout=5000)
                devre_disi = await dugme.get_attribute("disabled")
                if devre_disi is None:
                    await dugme.click(force=True)
                    gonderildi = True
                else:
                    print("[Arena] ⚠️ Gönder düğmesi pasif (disabled)", flush=True)
            except Exception as e:
                print(f"[Arena] Gönder düğmesi tıklanamadı: {str(e)[:90]}", flush=True)
    except Exception:
        pass

    # 2) Düğme işe yaramadıysa Enter ile gönder (Arena editörü Enter'ı gönderir)
    if not gonderildi:
        await editor.click()
        await page.keyboard.press("Enter")

    # 3) DOĞRULAMA: editör boşaldı mı? (gönderim gerçekten oldu mu)
    for _ in range(10):
        await page.wait_for_timeout(400)
        if await _editor_bos():
            print("[Arena] 📤 Prompt gönderildi (doğrulandı)", flush=True)
            return True

    print("[Arena] ❌ GÖNDERİLEMEDİ — editör hâlâ dolu (gönderim doğrulanamadı)", flush=True)
    return False


async def _arena_riza_modalini_kapat(page) -> bool:
    """Arena açılışta 'Terms of ... Agree' modalı gösterebiliyor.

    Kapatılmazsa cevap HİÇ gelmiyor ve sayfa metni modal olarak kalıyor.
    CANLI KANIT (koşu 43140690378, 02:21→02:25): 4,5 dakika beklendi; dönen
    metin "... Learn more about How it Works / Or hit Enter on your keyboard to
    agree / Agree / Close" oldu. ARENA_CONSENT_BUTTON_LABELS sabiti vardı ama
    hiçbir yerde kullanılmıyordu.
    """
    for etiket in ARENA_CONSENT_BUTTON_LABELS:
        try:
            btn = page.get_by_role("button", name=etiket, exact=True)
            if await btn.count():
                await btn.first.click(force=True, timeout=5000)
                print(f"[Arena] ✅ Onay modalı kapatıldı ('{etiket}')", flush=True)
                return True
        except Exception as e:
            print(f"[Arena] Onay modalı uyarısı ({etiket}): {str(e)[:70]}", flush=True)
    return False


async def _arena_sorgusu_yap(
    page,
    prompt: str,
    min_cevap_uzunlugu: int = 100,
    idle_timeout: int | None = None,
    max_timeout: int | None = None,
) -> str | None:
    """Arena'ya sorar ve cevabı döndürür — SABİT TIMEOUT YOK, CANLI İLERLEME VAR.

    KULLANICI İSTEĞİ (2026-11-11): "Timeout kullanma; Arena bazen uzun düşünüyor.
    Yanıtın oluşturma sürecini anlık olarak pipeline içinde gösterirsek, süreyi
    varsayımsal değil GERÇEK olarak göstermiş oluruz."

    Eski davranış: `while süre < 130 sn` → Arena 3 dakika düşünürse cevap
    ÇÖPE gidiyordu (üretim yerel şablona düşüyordu) ve kullanıcı neden
    düştüğünü göremiyordu.

    Yeni davranış:
      • Mutlak süre sınırı YOK. Yalnız iki GÜVENLİK freni var (ikisi de env ile
        ayarlanır, varsayılanı çok geniş):
          ARENA_IDLE_DK  (varsayılan 15) — bu kadar süre HİÇ değişiklik olmazsa
                                          "takıldı" sayılır (donmuş sayfa).
          ARENA_MAKS_DK  (varsayılan 45) — mutlak güvenlik tavanı (Actions job
                                          süresini korumak için, pratikte nadir).
      • Her ~10 saniyede TEK SATIR canlı ilerleme basılır (flush=True):
          ⏳ Arena 00:42 · düşünüyor · 213 karakter · son değişim 6 sn önce
      • Arena'nın kendi süre etiketi ("Thought for 12 seconds") görülürse
        ayrıca yazılır → GERÇEK düşünme süresi logda.
      • Bitiş: "Was this task successful?" işareti + yeterli metin, ya da
        20 sn boyunca metin değişmezse (cevap oturdu).
    """
    import os
    from datetime import datetime

    idle_dk = float(os.environ.get("ARENA_IDLE_DK", "15") or 15)
    maks_dk = float(os.environ.get("ARENA_MAKS_DK", "45") or 45)

    try:
        await page.goto("https://arena.ai/agent/", wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(3000)
        await _arena_riza_modalini_kapat(page)
        await page.wait_for_timeout(1000)

        ilk_body = await page.locator("body").inner_text()
        if "MIDDLEWARE_INVOCATION_FAILED" in ilk_body:
            print("[Arena] HATA: 500 Middleware hatası.", flush=True)
            return None

        editor = page.locator('div.tiptap[contenteditable="true"]')
        try:
            await editor.wait_for(state="visible", timeout=30000)
        except Exception:
            print("[Arena] Tiptap editörü görünmedi.", flush=True)
            return None

        await editor.click()
        await page.wait_for_timeout(300)
        await page.keyboard.insert_text(prompt)
        await page.wait_for_timeout(400)

        send_btn = page.locator('button[aria-label="Send message"]')
        await send_btn.click(force=True)
        gonderim = datetime.now()
        print("[Arena] 📤 Prompt gönderildi — cevap bekleniyor (süre sınırı yok)", flush=True)

        for _ in range(15):
            await page.wait_for_timeout(1000)
            if page.url != "https://arena.ai/agent/":
                break

        prompt_ilk_satir = prompt.splitlines()[0][:55]
        son_uzunluk = 0
        son_degisim = datetime.now()
        stable_ticks = 0
        son_kalp = -99
        dusunme_suresi = ""

        while True:
            await page.wait_for_timeout(2000)
            gecen = (datetime.now() - gonderim).total_seconds()
            body = await page.locator("body").inner_text()

            # Modal sonradan açılabiliyor (ya da ilk denemede kapanmamış olabilir):
            # sayfa metni modal ise kapat ve cevap sayacını sıfırla.
            if "to agree" in body.lower() or "How it Works" in body:
                if await _arena_riza_modalini_kapat(page):
                    gonderim = datetime.now()
                    son_degisim = datetime.now()
                    continue

            if "Sign in to continue" in body or "Continue with Google" in body:
                _oturum_doldu_isaretle()
                return None

            cevap = _ingilizce_onyuzu_at(
                _prompt_kuyrugunu_at(
                    _cevabi_ayikla(body, prompt, prompt_ilk_satir), prompt
                )
            )
            if _prompt_yankisi_mi(cevap):
                cevap = ""  # yalnız prompt yankısı var → gerçek cevap henüz gelmedi
            dusunuyor = "orchestrating" in body.lower() or "thinking" in body.lower()
            bitti_isareti = "Was this task successful?" in body

            # Arena'nın KENDİ süre etiketi: "Thought for 12 seconds"
            if not dusunme_suresi:
                m = re.search(r"Thought for ([\w\s]+?)(?:\n|$)", body)
                if m:
                    dusunme_suresi = m.group(1).strip()

            if len(body) != son_uzunluk or dusunuyor:
                son_uzunluk = len(body)
                son_degisim = datetime.now()
                stable_ticks = 0
            else:
                stable_ticks += 1

            # CANLI İLERLEME (her ~10 sn) — varsayım değil, gerçek durum
            if gecen - son_kalp >= 10 or gecen < 3:
                son_kalp = gecen
                durum = "düşünüyor" if dusunuyor else ("cevap yazıyor" if cevap else "bekliyor")
                sessiz = (datetime.now() - son_degisim).total_seconds()
                print(
                    f"[Arena] ⏳ {int(gecen) // 60:02d}:{int(gecen) % 60:02d} · {durum} · "
                    f"{len(cevap)} karakter · son değişim {int(sessiz)} sn önce"
                    + (f" · Arena: {dusunme_suresi}" if dusunme_suresi else ""),
                    flush=True,
                )

            if bitti_isareti and len(cevap) >= min_cevap_uzunlugu:
                print(
                    f"[Arena] ✅ Cevap alındı: {gecen:.0f} sn · {len(cevap)} karakter"
                    + (f" · Arena'nın kendi süresi: {dusunme_suresi}" if dusunme_suresi else ""),
                    flush=True,
                )
                _arena_sure_kaydet(gecen, len(cevap), dusunme_suresi)
                return cevap

            if stable_ticks >= 10 and len(cevap) >= min_cevap_uzunlugu:
                print(
                    f"[Arena] ✅ Cevap oturdu (20 sn değişmedi): {gecen:.0f} sn · "
                    f"{len(cevap)} karakter",
                    flush=True,
                )
                _arena_sure_kaydet(gecen, len(cevap), dusunme_suresi)
                return cevap

            # GÜVENLİK FRENLERİ (sabit timeout değil — donmuş sayfa koruması)
            sessiz_dk = (datetime.now() - son_degisim).total_seconds() / 60
            if sessiz_dk > idle_dk:
                print(
                    f"[Arena] ⚠️ {sessiz_dk:.0f} dk boyunca hiç değişiklik yok "
                    f"(ARENA_IDLE_DK={idle_dk}) — takıldı sayılıyor.",
                    flush=True,
                )
                return cevap if len(cevap) >= min_cevap_uzunlugu else None
            if gecen / 60 > maks_dk:
                print(
                    f"[Arena] ⚠️ ARENA_MAKS_DK={maks_dk} aşıldı ({gecen:.0f} sn) — "
                    "güvenlik freni.",
                    flush=True,
                )
                return cevap if len(cevap) >= min_cevap_uzunlugu else None

    except Exception as e:
        print(f"[Arena] Sorgu hatası: {e}", flush=True)
        return None


#: Prompt'un tanıtıcı parçaları — Arena bunları yankılıyor (canlı kanıt
#: koşu 43139582417: 3166 karakterlik "cevap" aslında bizim prompt'umuzdu ve
#: 20 sn hiç değişmedi → sahte "cevap oturdu").
PROMPT_IZLERI = (
    "Sen BOBİ TV için Türkçe kısa bilgi",
    "YAZIM KURALLARI:",
    "şablonu yankılama",
    # Arena, kullanıcı mesajını İngilizce özetleyip cevabın başına koyuyor
    # (canlı kanıt 43199457474: cevap '" = "Hello! Introduce yourself..."' ile başladı)
    "Respond in Turkish",
    "Simple question.",
)


def _prompt_yankisi_mi(metin: str) -> bool:
    """Dönen metin gerçek cevap değil, gönderdiğimiz prompt'un yankısı mı?"""
    return any(iz in str(metin or "") for iz in PROMPT_IZLERI)


def _prompt_kuyrugunu_at(cevap: str, prompt: str) -> str:
    """Yankılanan prompt'un arkasındaki GERÇEK cevabı bırakır."""
    t = str(cevap or "")
    if not _prompt_yankisi_mi(t):
        return t
    izler = (
        "şablonu yankılama",
        "sadece metin yaz.",
        "Emoji kullan ama abartma",
        "Respond in Turkish",
        "Simple question.",
    )
    # Yankı üst üste binen parçalardan oluşabilir ("Simple question. Respond in
    # Turkish with ...") → kesme işlemini sabitlenene kadar tekrarla.
    for _ in range(6):
        # Yankının SON işareti esas alınır: "Simple question. Respond in Turkish
        # with ..." gibi iç içe geçen parçalarda en sondaki işaret yankının bitişidir.
        adaylar = []
        for iz in izler:
            i = t.find(iz)
            if i != -1:
                adaylar.append((i, iz))
        if not adaylar:
            break
        i, iz = max(adaylar)
        kalan = t[i + len(iz):].strip()
        if not kalan or _prompt_yankisi_mi(kalan):
            break
        t = kalan
    # Son kırıntı: Arena'nın İngilizce özetinin Türkçe olmayan ilk paragrafları
    # (canlı kanıt: "... Respond in Turkish with a one-sentence self-introduction.")
    t = _ingilizce_onyuzu_at(t)
    return "" if _prompt_yankisi_mi(t) else t


def _ingilizce_onyuzu_at(metin: str) -> str:
    """Baştaki İngilizce özet paragraflarını atar (gerçek cevap Türkçedir).

    CANLI KANIT (43199931093): cevap şöyle geliyordu →
      'User asks in Turkish: "Hello! Introduce yourself in one sentence."
       Just answer in Turkish, one sentence.'
      'Merhaba! Ben Arena.ai'nin yardımcı ajanıyım...'
    Arena her cevabın başına kendi İngilizce açıklamasını ekliyor.
    """
    import re as _re

    parcalar = [p for p in _re.split(r"\n{2,}", str(metin or "")) if p.strip()]
    turkce = set("çğıöşüÇĞİÖŞÜ")
    while len(parcalar) > 1:
        ilk, kalan = parcalar[0], parcalar[1:]
        # Yalnız ilk paragraf Türkçe değilse VE sonrasında Türkçe bir paragraf
        # varsa at (JSON cevapları tek parça olduğu için korunur).
        if set(ilk) & turkce or not any(set(k) & turkce for k in kalan):
            break
        parcalar = kalan
    return "\n\n".join(parcalar).strip()


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
    # Arayüz etiketleri cevap sanılmasın
    for etiket in ("Was this task successful?", "Workspace", "Connectors"):
        if slice_text.strip() == etiket:
            slice_text = ""

    # Arena zaman etiketi: "2m 37s | just now" / "12:26 PM"
    slice_text = re.sub(
        r"\n+\s*(?:\d+m\s*)?\d+s?\s*\|\s*just now[\s\S]*$", "", slice_text, flags=re.IGNORECASE
    ).strip()
    slice_text = re.sub(r"\n+\s*\d{1,2}:\d{2}\s*(?:AM|PM)?\s*$", "", slice_text, flags=re.IGNORECASE).strip()
    # Arena, gönderdiğimiz prompt'u (özellikle JSON şablonunu) yankılayıp
    # ARDINDAN gerçek cevabı yazıyor. Yankı cevabın içinde kalırsa ayrıştırıcı
    # şablonu "cevap" sanıyordu (canlı kanıt: koşu 43138461248).
    _ilk = prompt_ilk_satir.strip()
    if _ilk:
        _i = slice_text.rfind(_ilk)
        if _i > 0:
            slice_text = slice_text[_i + len(_ilk):].strip()

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
