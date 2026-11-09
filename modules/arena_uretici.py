"""
BOBİ TV — Arena AI Tam Üretim Modülü v1.0
Arena AI'ya senaryo, ses, animasyon, kapak ve metadata ürettirir.
Tek bir Arena oturumunda tüm video üretilir.
"""
import os
import json
import subprocess
import tempfile
import time
from pathlib import Path
from datetime import datetime

OUTPUT_YOLU = Path("bobi_tv/output")
RENDER_YOLU = Path("bobi_tv/production/render")
ARENA_SCRIPT = Path("arena-ask.mjs")


def arena_tam_uretim(video_no: int) -> dict | None:
    """
    Arena AI'ya tek seferde şunları ürettir:
    1. Absürt senaryo (diyaloglar)
    2. Python animasyon kodu (PIL + FFmpeg)
    3. Metadata (başlık, açıklama, hashtag)
    
    Döner: senaryo_paketi veya None
    """
    cookies_json = os.environ.get("ARENA_COOKIES_JSON", "")
    if not cookies_json:
        print("[Arena Tam] ARENA_COOKIES_JSON yok.")
        return None

    # Cookie'yi temizle ve auth token çıkar
    clean_cookie = _cookie_temizle(cookies_json)
    if not clean_cookie:
        print("[Arena Tam] Cookie parse başarısız.")
        return None

    tarih = datetime.now().strftime("%Y%m%d")
    dosya_adi = f"{tarih}_{video_no:04d}_arena"
    
    OUTPUT_YOLU.mkdir(parents=True, exist_ok=True)
    RENDER_YOLU.mkdir(parents=True, exist_ok=True)

    video_cikti = str(OUTPUT_YOLU / f"{dosya_adi}.mp4")

    # Arena'ya gönderilecek prompt
    prompt = f"""Türkçe absürt YouTube Shorts videosu için Python kodu yaz.

Görev:
1. Kısa absürt Türkçe diyalog senaryo yaz (4-5 satır, komik twist)
2. Bu senaryoyu animasyona çeviren Python kodu yaz:
   - PIL ile 1080x1920 px, 30fps, ~8 saniye
   - Koyu gradient arka plan (lacivert-mor)
   - Büyük sarı hook metni (ilk 1.5sn)
   - Her diyalog satırı beyaz metinle ortada göster
   - Alt köşe: küçük "BOBI TV" watermark
   - FFmpeg ile {video_cikti} olarak kaydet
3. Çalıştırılabilir tek Python scripti döndür (import dahil)
4. Scriptin sonunda JSON olarak metadata: baslik, aciklama, hashtag

Sadece Python kodu döndür, markdown yok."""

    print(f"[Arena Tam] Video #{video_no} üretimi başlıyor...")

    try:
        result = subprocess.run(
            ["node", str(ARENA_SCRIPT), prompt],
            env={**os.environ, "ARENA_AUTH_COOKIE": clean_cookie},
            capture_output=True,
            text=True,
            timeout=300
        )

        output = result.stdout.strip()
        if not output:
            print("[Arena Tam] Boş cevap.")
            return None

        print(f"[Arena Tam] Cevap alındı ({len(output)} char)")

        # Python kodunu çıkar
        kod = _kod_cikar(output)
        if not kod or len(kod) < 100:
            print("[Arena Tam] Yeterli Python kodu bulunamadı.")
            return None

        # Kodu çalıştır
        print(f"[Arena Tam] Animasyon kodu çalıştırılıyor...")
        basari, metadata = _kodu_calistir_ve_meta(kod, video_cikti)

        if basari and Path(video_cikti).exists() and Path(video_cikti).stat().st_size > 5000:
            boyut = Path(video_cikti).stat().st_size // 1024
            print(f"[Arena Tam] ✅ Video hazır: {video_cikti} ({boyut}KB)")

            return {
                "video_no": video_no,
                "dosya_adi": dosya_adi,
                "baslik": metadata.get("baslik", f"BOBİ TV #{video_no} 🎬"),
                "final_video": video_cikti,
                "senaryo": {"kategori": "arena_ai", "acilis": metadata.get("acilis", "")},
                "arena_metadata": metadata,
                "olusturuldu": datetime.now().isoformat(),
                "hash": f"arena_{video_no}_{tarih}"
            }
        else:
            print(f"[Arena Tam] Video oluşturulamadı.")
            return None

    except subprocess.TimeoutExpired:
        print("[Arena Tam] 5 dakika timeout.")
        return None
    except Exception as e:
        print(f"[Arena Tam] Hata: {e}")
        return None


def _cookie_temizle(cookies_json: str) -> str | None:
    """ARENA_COOKIES_JSON'dan temiz cookie string'i döndür."""
    import re, base64
    try:
        cookies = json.loads(cookies_json)
        # arena-auth-prod-v1.X parçalarını sıralı birleştir
        parts = sorted(
            [(c['name'], c['value']) for c in cookies
             if c.get('name','').startswith('arena-auth-prod-v1.') and c.get('value')],
            key=lambda x: x[0]
        )
        if not parts:
            return None
        combined = ''.join(v for _, v in parts).replace('base64-', '', 1)
        # Sadece geçerli base64 karakterleri
        valid = re.sub(r'[^A-Za-z0-9+/]', '', combined)
        # 4'ün katına yuvarla
        pad = (4 - len(valid) % 4) % 4
        decoded = base64.b64decode(valid[:len(valid) - len(valid) % 4] + '=' * min(2, pad)).decode('utf-8', errors='replace')
        # Kontrol karakterlerini temizle
        clean = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\ufffd]', '', decoded)
        session = json.loads(clean)
        access = session.get('access_token', '')
        if access:
            # base64 formatında encode ederek cookie değeri oluştur
            minimal = {
                'access_token': access,
                'token_type': 'bearer',
                'expires_in': 3600,
                'refresh_token': session.get('refresh_token', ''),
                'user': {'id': session.get('user', {}).get('id', ''), 'email': session.get('user', {}).get('email', '')}
            }
            return f"base64-{base64.b64encode(json.dumps(minimal).encode()).decode()}"
    except Exception as e:
        print(f"[Arena] Cookie temizleme hatası: {e}")
    return None
    """Arena cevabından Python kodunu çıkar."""
    if "```python" in metin:
        return metin.split("```python")[1].split("```")[0].strip()
    if "```" in metin:
        # İlk kod bloğunu al
        parcalar = metin.split("```")
        if len(parcalar) >= 3:
            return parcalar[1].strip()
    # Kod bloğu yoksa import içeren satırları al
    satirlar = metin.split("\n")
    kod_satirlari = []
    basladi = False
    for satir in satirlar:
        if satir.strip().startswith(("import ", "from ", "def ", "class ", "#")):
            basladi = True
        if basladi:
            kod_satirlari.append(satir)
    return "\n".join(kod_satirlari) if kod_satirlari else metin


def _kodu_calistir_ve_meta(kod: str, beklenen_cikti: str) -> tuple:
    """
    Python kodunu çalıştır.
    Döner: (basari: bool, metadata: dict)
    """
    metadata = {
        "baslik": "BOBİ TV Absürt #Shorts",
        "aciklama": "BOBİ TV — Her gün absürt Türkçe Shorts!",
        "hashtag": "#shorts #komedi #absürt #türkçe #bobitv"
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        # Pip bağımlılıklarını otomatik kur
        on_kod = """
import subprocess, sys
for pkg in ["Pillow", "numpy"]:
    try:
        __import__(pkg.lower().replace("pillow","PIL").replace("numpy","numpy"))
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", pkg, "-q"])
"""
        f.write(on_kod + "\n" + kod)
        tmp_py = f.name

    try:
        result = subprocess.run(
            ["python3", tmp_py],
            capture_output=True, text=True, timeout=120,
            env={**os.environ}
        )

        if result.returncode == 0:
            # stdout'tan JSON metadata ara
            for satir in result.stdout.split("\n"):
                satir = satir.strip()
                if satir.startswith("{") and "baslik" in satir:
                    try:
                        meta = json.loads(satir)
                        metadata.update(meta)
                    except Exception:
                        pass

            if Path(beklenen_cikti).exists():
                return True, metadata
            else:
                print(f"[Kod] Çıktı dosyası yok: {beklenen_cikti}")
                print(f"[Kod] stdout: {result.stdout[:300]}")
                return False, metadata
        else:
            print(f"[Kod] Hata (exit {result.returncode}): {result.stderr[:400]}")
            return False, metadata

    except subprocess.TimeoutExpired:
        print("[Kod] 2 dakika timeout.")
        return False, metadata
    except Exception as e:
        print(f"[Kod] Çalıştırma hatası: {e}")
        return False, metadata
    finally:
        Path(tmp_py).unlink(missing_ok=True)
