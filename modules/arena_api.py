"""
BOBİ TV — Arena AI API Entegrasyonu v2.1 (Tam Sağlamlaştırılmış)
Playwright (headless Chromium) ile Arena.ai Agent üzerinden senaryo + animasyon kodu üretir.
"""
import os
import re
import json
import base64
import asyncio
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime


def sanitize_cookie_json(raw_text: str) -> str:
    """Markdown link bozulmalarını ([arena.ai](http://arena.ai)) temizler."""
    return re.sub(r"\[([^\]]+)\]\(https?://[^)]+\)", r"\1", raw_text).strip()


def build_clean_arena_cookie(cookies: list) -> str:
    """
    arena-auth-prod-v1.0, v1.1 ... parçalarını isim sırasına göre birleştirir.
    Parça sınırında kesilme olsa bile regex fallback ile oturumu kurtarır ve
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

    # 1. Tam birleştirilmiş Base64 JSON çözümlemesi dene
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

    # 2. Fallback: Kopyalama sırasında parça sonu kesildiyse ilk parçadan (v1.0) regex ile kurtar
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


async def arena_video_uret(video_no: int, output_dir: str = "bobi_tv/output") -> dict | None:
    """
    Arena AI'dan otonom video üretimi:
    1. Senaryo iste (kısa absürt Türkçe)
    2. Animasyon Python kodu iste ve çalıştır (hata verirse garantili yerel FFmpeg+TTS fallback)
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("[Arena] Playwright kurulu değil: pip install playwright")
        return None

    cookies_raw = os.environ.get("ARENA_COOKIES_JSON", "").strip()
    if not cookies_raw:
        print("[Arena] ARENA_COOKIES_JSON ortam değişkeni boş.")
        return None

    try:
        cookies_list = json.loads(sanitize_cookie_json(cookies_raw))
        clean_cookie = build_clean_arena_cookie(cookies_list)
    except Exception as e:
        print(f"[Arena] Çerez hazırlama hatası: {e}")
        return None

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    tarih = datetime.now().strftime("%Y%m%d")
    dosya_adi = f"{tarih}_{video_no:04d}_arena"
    video_cikti = f"{output_dir}/{dosya_adi}.mp4"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1366, "height": 900})

        # Yalnızca 3 temiz çerezi ekle (__cf_bm veya _dd_s EKLEME!)
        await context.add_cookies([
            {"name": "arena-auth-prod-v1.0", "value": clean_cookie, "domain": "arena.ai", "path": "/"},
            {"name": "arena_build_bucket", "value": "stable", "domain": "arena.ai", "path": "/"},
            {"name": "user_country_code", "value": "TR", "domain": "arena.ai", "path": "/"},
        ])

        page = await context.new_page()

        # === ADIM 1: Senaryo + Başlık JSON olarak iste ===
        print(f"[Arena] Video #{video_no}: Senaryo oluşturuluyor...")
        senaryo_paket = await _arena_senaryo_uret(page, video_no)
        await _guncel_cerezleri_kaydet(context)
        await browser.close()

        if not senaryo_paket:
            return None

        senaryo = "\n".join(senaryo_paket["satirlar"])
        print(f"[Arena] Senaryo alındı ({len(senaryo_paket['satirlar'])} satır): {senaryo_paket['baslik']}")

    # === ADIM 2: Garantili yüksek kaliteli Türkçe TTS + FFmpeg Shorts render ===
    basari, fb_meta = _garantili_shorts_render(senaryo, video_cikti, video_no)
    metadata = {
        "baslik": senaryo_paket.get("baslik") or fb_meta["baslik"],
        "aciklama": senaryo_paket.get("aciklama") or fb_meta["aciklama"],
        "hashtag": "#shorts #komedi #absürt #türkçe",
    }

    if basari and Path(video_cikti).exists() and Path(video_cikti).stat().st_size > 10_000:
        boyut_kb = Path(video_cikti).stat().st_size // 1024
        print(f"[Arena] ✅ Video hazır: {video_cikti} ({boyut_kb} KB)")

        return {
            "video_no": video_no,
            "dosya_adi": dosya_adi,
            "final_video": video_cikti,
            "baslik": metadata.get("baslik", f"BOBİ TV #{video_no} #Shorts"),
            "aciklama": metadata.get("aciklama", "BOBİ TV — Absürt Türkçe Shorts"),
            "hashtag": metadata.get("hashtag", "#shorts #komedi #türkçe"),
            "senaryo": {
                "acilis": senaryo[:200],
                "kategori": "absurt",
                "sabit_yorum": metadata.get("aciklama", "Sizce sonunda ne oldu?"),
                "etkilesim": "Yorumlara yazın!",
            },
            "olusturuldu": datetime.now().isoformat(),
        }

    print("[Arena] ❌ Video oluşturulamadı.")
    return None


async def _guncel_cerezleri_kaydet(context):
    """Supabase oturumu yenilediyse güncel çerezleri dosyaya yazar."""
    save_path = os.environ.get("SAVE_UPDATED_COOKIES", "").strip()
    if not save_path:
        return
    try:
        latest = await context.cookies("https://arena.ai")
        auth_cookies = [c for c in latest if str(c.get("name", "")).startswith("arena-auth-prod-v1")]
        if auth_cookies:
            p = Path(save_path)
            p.write_text(json.dumps(auth_cookies, indent=2), encoding="utf-8")
            p.chmod(0o600)
    except Exception as e:
        print(f"[Arena] Güncel çerez kaydetme uyarısı: {e}")


async def _arena_senaryo_uret(page, video_no: int) -> dict | None:
    prompt = (
        f"Türkçe absürt komedi YouTube Shorts senaryosu yaz (Bölüm #{video_no}). "
        "4 veya 5 kısa Türkçe diyalog cümlesi olsun, son cümle beklenmedik komik şok/twist olsun. "
        "Hiçbir araç kullanma, sadece şu JSON formatında yanıt ver: "
        '{"baslik": "Vurucu Türkçe Başlık 😱 #shorts", "aciklama": "Siz olsanız ne yapardınız?", "satirlar": ["1. cümle", "2. cümle", "3. cümle", "4. twist cümlesi"]}'
    )
    cevap = await _arena_sorgusu_yap(page, prompt, min_cevap_uzunlugu=60, timeout=120)
    if not cevap:
        return None

    # Yanıtın sonundaki geçerli JSON nesnesini cımbızla çıkar (önündeki Thought bloğunu tamamen yoksayar!)
    candidates = re.findall(r"\{[^{}]*\}", cevap)
    if "{" in cevap and "}" in cevap:
        candidates.append(cevap[cevap.find("{"):cevap.rfind("}") + 1])
    for raw_json in reversed(candidates):
        try:
            obj = json.loads(raw_json)
            if isinstance(obj.get("satirlar"), list) and len(obj["satirlar"]) >= 2:
                return {
                    "baslik": str(obj.get("baslik") or f"Sonunu Beklemiyordum 😱 #{video_no} #shorts"),
                    "aciklama": str(obj.get("aciklama") or "Yorumlara yazın!"),
                    "satirlar": [str(s).strip() for s in obj["satirlar"] if str(s).strip()],
                }
        except Exception:
            continue

    # JSON parse edilemezse sadece Türkçe karakter barındıran diyalog satırlarını al
    tr_lines = [
        l.strip() for l in cevap.splitlines()
        if len(l.strip()) > 5 and not re.match(r"^(Thought|Let me|I will|The user|Here)", l.strip(), re.I)
    ]
    if tr_lines:
        return {
            "baslik": f"{tr_lines[0][:50]} 😱 #shorts",
            "aciklama": "Sonuna kadar izleyin!",
            "satirlar": tr_lines[:5],
        }
    return None


async def _arena_kod_uret(page, senaryo: str, video_cikti: str) -> str | None:
    prompt = f"""Aşağıdaki Türkçe YouTube Shorts senaryosu için tek başına çalıştırılabilir Python 3 kodu yaz.
Hiçbir araç (bash/write_file) ÇAĞIRMA! Doğrudan mesajının içinde tek bir python kod bloğu olarak yaz.

Gereksinimler:
- 1080x1920 px (9:16), 24 FPS, ~8 saniye MP4 (`{video_cikti}`)
- Sadece PIL (Pillow) + `gtts` (veya sessiz/ton ses) + `subprocess` ile `ffmpeg` kullan (`moviepy` KULLANMA!)
- Font olarak `/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf` kullan.
- Senaryo satırlarını sırayla ortada büyük beyaz kutulu metin olarak göster, altta küçük "BOBI TV" yazsın:
{senaryo}

Kodun en sonunda şu JSON satırını print et:
{{"baslik": "Vurucu kısa Türkçe başlık #shorts", "aciklama": "İzleyiciye soru soran kısa açıklama", "hashtag": "#shorts #komedi #türkçe"}}"""

    cevap = await _arena_sorgusu_yap(page, prompt, min_cevap_uzunlugu=200, timeout=180)
    if not cevap:
        return None

    if "```python" in cevap:
        return cevap.split("```python", 1)[1].split("```", 1)[0].strip()
    if "```" in cevap:
        parts = cevap.split("```")
        if len(parts) >= 3:
            return parts[1].strip()
    return None


async def _arena_sorgusu_yap(page, prompt: str, min_cevap_uzunlugu: int = 60, timeout: int = 120) -> str | None:
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
            print(f"[Arena] HATA: Tiptap editörü görünmedi. Sayfa: {ilk_body[:250]}")
            return None

        await editor.click()
        await page.wait_for_timeout(300)
        await page.keyboard.insert_text(prompt)
        await page.wait_for_timeout(500)

        send_btn = page.locator('button[aria-label="Send message"]')
        await send_btn.click(force=True)

        # URL'nin /agent/<chat_id> adresine geçmesini bekle
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
                print("[Arena] HATA: Oturum süresi dolmuş veya geçersiz (Login modalı açıldı)!")
                return None

            cevap = _cevabi_ayikla(body, prompt, prompt_ilk_satir)
            dusunuyor = (
                "orchestrating" in body.lower()
                or "thinking" in body.lower()
            )
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

        print(f"[Arena] Cevap zaman aşımı ({timeout}sn).")
        return None

    except Exception as e:
        print(f"[Arena] Sorgu hatası: {e}")
        return None


def _cevabi_ayikla(full_body: str, prompt: str, prompt_ilk_satir: str) -> str:
    # Prompt'un son satirini referans alarak prompt govdesinin tamamen sonrasina gec
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

    # "Thought for X second(s)" dusunce blogu basligini ve ilk dusunce satirini temizle
    lines = [l for l in slice_text.splitlines()]
    if lines and re.match(r"^Thought for \d+", lines[0].strip(), re.IGNORECASE):
        lines = lines[1:]
        while lines and not lines[0].strip():
            lines.pop(0)
        # Eger bir sonraki satir tek cumlelik ic dusunce ozeti ise ("Kullanıcı ... istiyor.") ve altinda bos satir varsa atla
        if len(lines) >= 3 and not lines[1].strip() and re.match(r"^(Kullanıcı|The user)\b", lines[0].strip(), re.IGNORECASE):
            lines = lines[2:]
    return "\n".join(lines).strip()


def _kodu_calistir(kod: str, video_cikti: str) -> tuple:
    metadata = {
        "baslik": "BOBİ TV Absürt #Shorts",
        "aciklama": "BOBİ TV — Her gün absürt Türkçe Shorts!",
        "hashtag": "#shorts #komedi #türkçe",
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(kod)
        tmp = f.name

    try:
        result = subprocess.run(
            ["python3", tmp],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if result.returncode == 0:
            for satir in result.stdout.splitlines():
                if "{" in satir and "baslik" in satir:
                    try:
                        s = satir[satir.find("{"):satir.rfind("}") + 1]
                        metadata.update(json.loads(s))
                    except Exception:
                        pass
            if Path(video_cikti).exists():
                return True, metadata

        print(f"[Kod] Çalıştırma hatası (rc={result.returncode}): {result.stderr[-400:]}")
        return False, metadata
    except Exception as e:
        print(f"[Kod] İstisna: {e}")
        return False, metadata
    finally:
        Path(tmp).unlink(missing_ok=True)


def _garantili_shorts_render(senaryo: str, video_cikti: str, video_no: int) -> tuple:
    """Arena'nın ürettiği senaryoyu garantili olarak 1080x1920 Türkçe TTS + FFmpeg MP4'e dönüştürür."""
    import textwrap
    from PIL import Image, ImageDraw, ImageFont

    satirlar = [s.strip(" -•*") for s in senaryo.splitlines() if len(s.strip()) > 2][:6]
    if not satirlar:
        satirlar = ["Bir terslik var...", "Ama sonunu kimse tahmin edemedi!"]

    ilk_baslik = re.sub(r"^[^:]+:\s*", "", satirlar[0])[:55].strip()
    meta = {
        "baslik": f"{ilk_baslik} 😱 #shorts",
        "aciklama": "Son cümleyi bekleyin! Siz olsanız ne yapardınız?",
        "hashtag": "#shorts #komedi #absürt #türkçe",
    }

    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    try:
        font_main = ImageFont.truetype(font_path, 58)
        font_wm = ImageFont.truetype(font_path, 36)
    except Exception:
        font_main = ImageFont.load_default()
        font_wm = ImageFont.load_default()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        concat_lines = []
        audio_files = []

        for idx, satir in enumerate(satirlar):
            # Görsel kare üret
            img = Image.new("RGB", (1080, 1920), (18, 16, 46))
            draw = ImageDraw.Draw(img)
            # Basit modern kart
            draw.rounded_rectangle([(80, 620), (1000, 1300)], radius=40, fill=(34, 30, 82), outline=(130, 100, 255), width=4)
            wrapped = "\n".join(textwrap.wrap(satir, width=24))
            draw.multiline_text((540, 960), wrapped, fill=(255, 255, 255), font=font_main, anchor="mm", align="center", spacing=18)
            draw.text((540, 1780), "BOBİ TV", fill=(180, 170, 230), font=font_wm, anchor="mm")

            img_path = tmp / f"slide_{idx:02d}.png"
            img.save(img_path)

            # Ses üret (gTTS dene)
            temiz_ses_metni = re.sub(r"^[^:]{1,20}:\s*", "", satir).strip() or satir
            mp3_path = tmp / f"voice_{idx:02d}.mp3"
            sure = 2.2
            try:
                from gtts import gTTS
                gTTS(text=temiz_ses_metni, lang="tr").save(str(mp3_path))
                probe = subprocess.run(
                    ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(mp3_path)],
                    capture_output=True, text=True, timeout=10
                )
                sure = max(1.8, float(probe.stdout.strip()) + 0.35)
                audio_files.append(mp3_path)
            except Exception:
                pass

            seg_path = tmp / f"seg_{idx:02d}.mp4"
            if mp3_path.exists():
                cmd = [
                    "ffmpeg", "-y", "-loop", "1", "-i", str(img_path), "-i", str(mp3_path),
                    "-t", f"{sure:.2f}", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "24",
                    "-c:a", "aac", "-b:a", "128k", "-shortest", str(seg_path)
                ]
            else:
                cmd = [
                    "ffmpeg", "-y", "-loop", "1", "-i", str(img_path),
                    "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                    "-t", f"{sure:.2f}", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "24",
                    "-c:a", "aac", "-shortest", str(seg_path)
                ]
            subprocess.run(cmd, capture_output=True, check=True, timeout=60)
            concat_lines.append(f"file '{seg_path}'")

        concat_txt = tmp / "list.txt"
        concat_txt.write_text("\n".join(concat_lines), encoding="utf-8")
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt), "-c", "copy", str(video_cikti)],
            capture_output=True, check=True, timeout=90
        )

    return Path(video_cikti).exists(), meta


if __name__ == "__main__":
    import sys
    v_no = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    res = asyncio.run(arena_video_uret(v_no))
    if res:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        sys.exit(1)
