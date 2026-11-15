import os
import random
import subprocess
import tempfile
from pathlib import Path
import asyncio
from io import BytesIO

# Modülün gerektirdiği bağımlılıklar:
import edge_tts
from PIL import Image

# Google GenAI yerine proje gereksinimi olan çerez tabanlı gorsel_uret modülü kullanılıyor
from modules.gemini_web import gorsel_uret

# YÜKLEME İMPORTU YOK (2026-11-13): yüklemeyi main_pipeline yapar.
# Gemini ilk sürümde burada video_yukle() çağırıyordu; pipeline da çağırınca
# aynı video YİNE yükleniyordu → çift yükleme. Tek sorumluluk: dosya üret.


KONU_URETILEMEDI = "KONU_URETILEMEDI"


def ses_uret(metin: str, ses_dosyasi: str):
    asyncio.run(ses_uret_async(metin, ses_dosyasi))


#: KAPAK İSTEMİ — kullanıcının kendi cümlesi (2026-11-13).
def kapak_istemini_yaz(baslik: str) -> str:
    """Kapak istemi: video başlığı + kullanıcının cümlesi.

    2026-11-13 kullanıcı: "Şablonu çöpe at. Sadece benim dediğimi yap.
    Tüm kapak fotoğrafları için bunu kullan."
    """
    return (
        f"{baslik} İsimli short video için kapak fotoğrafı istiyorum etkileşim ve "
        "izlenme rekorları kırması için profesyonel şekilde tasarla kapak "
        "fotoğrafını gören merak edip tıklasın."
    )


def kapak_olcekle(kaynak: str, hedef: str) -> str:
    """Kapağı 1080x1920 (9:16) tuvalde ortalar — METNİ ASLA KESMEZ.

    REGRESYON DÜZELTMESİ (2026-11-08). Geçmiş ölçümü:

    | Tarih | Yöntem | Sonuç |
    |---|---|---|
    | 2026-11-14 (21868da) | GÖRSELE DOKUNMA | 9:16 kapaklar kusursuz geçti |
    | 2026-11-15 (8f7398a) | 1080×1920 COVER + crop | **kırpma eklendi** |
    | bugün | 1:1 kapak + crop | metnin %44'ü kesildi: "İNİZ", "DİNİ NASIL YİY" |

    Kök neden: 8f7398a'da videonun ilk 1.5 sn'sine gömme eklenirken bu
    fonksiyona da "cover" kırpması kondu. İlk 1.5 sn için tuval 1080×1920
    olmalı — doğru — ama görseli KIRPMADAN oturtmak gerekiyordu.

    YÖNTEM (2 gün önce çalışan yol): görselin TAMAMINI sığdır (contain),
    boş kalan kenarları görselin kendi bulanık hâliyle doldur. Metin kesilmez,
    siyah bar olmaz. YouTube'un kendi 16:9 kırpması ayrı dosyada yapılır.
    """
    from PIL import Image

    img = Image.open(kaynak).convert("RGB")
    oran = img.width / img.height
    if img.size != (1080, 1920):
        if abs(oran - (9 / 16)) < 0.02:
            # Zaten 9:16 → sadece ölçekle, hiç kırpma yok.
            img = img.resize((1080, 1920), Image.LANCZOS)
        else:
            # CONTAIN: görselin tamamı sığar, kenarlar bulanık dolgu.
            # KIRPMA YOK → metin korunur.
            from PIL import ImageFilter

            arka = img.resize((1080, 1920), Image.LANCZOS).filter(
                ImageFilter.GaussianBlur(45))
            olcek = min(1080 / img.width, 1920 / img.height)
            ig = max(1, int(img.width * olcek + 0.5))
            iy = max(1, int(img.height * olcek + 0.5))
            on = img.resize((ig, iy), Image.LANCZOS)
            arka.paste(on, ((1080 - ig) // 2, (1920 - iy) // 2))
            img = arka
    for kalite in (92, 88, 84, 78, 70):
        img.save(hedef, "JPEG", quality=kalite, optimize=True)
        if Path(hedef).stat().st_size <= 2 * 1024 * 1024:
            break
    return hedef


def _ffmpeg() -> str:
    """ffmpeg yolunu çöz: PATH'te varsa onu, yoksa imageio paketini kullan."""
    import shutil as _sh

    yol = _sh.which("ffmpeg")
    if yol:
        return yol
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def ilk_kareye_gom(video: str, kapak_jpg: str, sn: float = 1.5) -> str:
    """Kapağı videonun İLK `sn` SANİYESİNE göm — kullanıcı kararı (2026-11-11).

    NİÇİN: YouTube Shorts iki görsel tutar. `thumbnails.set` yalnız
    maxresdefault/hqdefault'yu değiştirir; Shorts rafındaki `oar2.jpg`'ye API
    ile DOKUNULAMAZ (docs/KAPAK_TESHIS.md §KÖK NEDEN 3). Tek çözüm: kapağı
    videonun başına koymak.

    ⚠️ 1 kare (33 ms) YETMEZ — ölçüldü, göz görmüyor. En az 1.5 sn.

    YÖNTEM: tek filter_complex yerine İKİ ADIM (daha sağlam).
      1) kapağı sn saniyelik, sessiz ama SES KANALLI bir mp4'e çevir
      2) concat demuxer ile [kapak mp4] + [video] birleştir
    Tek adımlı filter_complex runner'da "streams received no packets" ile
    düşüyordu (koşu 43732515084). İki adım her ffmpeg sürümünde çalışır.
    """
    from pathlib import Path

    ff = _ffmpeg()
    calisma = str(Path(video).parent)
    sessiz = str(Path(video).with_name("_kapak_sessiz.mp4"))
    liste = str(Path(video).with_name("_concat.txt"))
    hedef = str(Path(video).with_name(Path(video).stem + "_kapakli.mp4"))

    # 1) kapak → sn saniyelik video (sessiz ses kanalı dâhil)
    r1 = subprocess.run(
        [
            ff, "-y",
            "-loop", "1", "-t", str(sn), "-i", kapak_jpg,
            "-f", "lavfi", "-t", str(sn), "-i", "anullsrc=r=44100:cl=stereo",
            "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,"
                   "crop=1080:1920,fps=30,setsar=1",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
            "-c:a", "aac", "-b:a", "192k", "-shortest",
            "-movflags", "+faststart",
            sessiz,
        ],
        capture_output=True, text=True, timeout=300,
    )
    if r1.returncode != 0 or not Path(sessiz).exists():
        print(f"[BOBİ TV] ⚠️ kapak klibi üretilemedi: {r1.stderr[-200:]}")
        return video

    # 2) concat demuxer: kapak ÖNCE, video SONRA
    Path(liste).write_text(
        f"file '{sessiz}'\nfile '{video}'\n", encoding="utf-8"
    )
    r2 = subprocess.run(
        [ff, "-y", "-f", "concat", "-safe", "0", "-i", liste,
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", hedef],
        capture_output=True, text=True, timeout=600,
    )
    for gecici in (sessiz, liste):
        Path(gecici).unlink(missing_ok=True)
    if r2.returncode != 0 or not Path(hedef).exists():
        print(f"[BOBİ TV] ⚠️ kapak birleştirme hatası: {r2.stderr[-200:]}")
        return video
    print(f"[BOBİ TV] ✅ Kapak ilk {sn} sn'ye gömüldü")
    return hedef


def kapak_youtube_surumu(kaynak: str, hedef: str) -> str:
    """Aynı kapağın 16:9 (1280×720) sürümü — YouTube kapak alanı için.

    NİÇİN AYRI DOSYA (2026-11-08):
      Video 9:16 → kapağın dikey sürümü kullanılır (ilk 1.5 sn).
      YouTube kapak alanı 16:9 → dikey görseli verince YouTube %68 blur dolgu
      ekliyordu (2026-11-13 ölçümü, d4ee933). 2 gün önceki videolarda doğru
      yöntem buydu: ORTADA net görsel, kenarlarda bulanık dolgu (ölçüm: net
      alan %32, ama metin TAM).

    YÖNTEM: 1280×720 tuval + görselin tamamı ortada (contain) + kendi bulanık
    hâliyle dolgu. Kırpma YOK, siyah bar YOK.
    """
    from PIL import Image, ImageFilter

    img = Image.open(kaynak).convert("RGB")
    tuval = Image.new("RGB", (1280, 720))
    arka = img.resize((1280, 720), Image.LANCZOS).filter(
        ImageFilter.GaussianBlur(45))
    tuval.paste(arka, (0, 0))
    olcek = min(1280 / img.width, 720 / img.height)
    g = max(1, int(img.width * olcek + 0.5))
    y = max(1, int(img.height * olcek + 0.5))
    on = img.resize((g, y), Image.LANCZOS)
    tuval.paste(on, ((1280 - g) // 2, (720 - y) // 2))

    for kalite in (92, 88, 84, 78, 70):
        tuval.save(hedef, "JPEG", quality=kalite, optimize=True)
        if Path(hedef).stat().st_size <= 2 * 1024 * 1024:
            break
    return hedef


def konu_uret(video_no: int) -> dict | None:
    """Konuyu üretir. Kaynak henüz bağlı değil.

    Dönmeli: {"baslik": str, "metin": str, "etiketler": list[str]}
    Bağlanana kadar video üretimi durur — sabit/yedek havuz YOK (kullanıcı kararı).
    """
    return None


def video_uret(video_no: int, konu: dict | None = None) -> dict:
    """BOBİ TV ana motor fonksiyonu.

    Konuyu alır (parametre veya konu_uret), görsel üretir, seslendirir, ffmpeg ile
    birleştirir, kapağı ilk 1.5 sn'ye gömer. Yükleme main_pipeline'da.
    """
    # 1. KONU — dışarıdan verilmediyse konu_uret()'ten alınır.
    # Sabit konu havuzu YOK (kullanıcı kararı 2026-11-15).
    if konu is None:
        konu = konu_uret(video_no)
    if not konu:
        raise RuntimeError(f"{KONU_URETILEMEDI}: konu üretilemedi (video_no={video_no})")
    baslik = konu["baslik"]
    metin = konu["metin"]
    etiketler = konu.get("etiketler", ["shorts"])

    # Geçici dosya yolları
    tmp_dir = tempfile.gettempdir()
    # BENZERSİZ damga: aynı video_no ile tekrar koşulduğunda dosya adı çakışmasın.
    # Çakışınca arşiv "zaten yayında" diyor ve yeni video hiç yüklenmiyordu.
    from datetime import datetime as _dt
    damga = _dt.now().strftime("%Y%m%d_%H%M%S")
    gorsel_yolu = os.path.join(tmp_dir, f"bobi_gorsel_{damga}.jpg")
    ses_yolu = os.path.join(tmp_dir, f"bobi_ses_{damga}.mp3")
    final_video_yolu = os.path.join(tmp_dir, f"bobi_{damga}.mp4")

    print(f"[BOBİ TV] Video üretiliyor: '{baslik}'")

    # 2. Görsel Üretimi (gorsel_uret fonksiyonu ile)
    prompt_metin = (
        f"Dikey (9:16) sinematik fotoğraf, konu: {konu['metin'][:120]}. "
        "Tek bir güçlü görsel, yakın plan, sıcak ışık, yüksek detay."
    )
    try:
        sonuc = gorsel_uret(prompt_metin, gorsel_yolu)
        if not sonuc or not os.path.exists(gorsel_yolu):
            raise RuntimeError("gorsel_uret dosya oluşturamadı.")
    except Exception as e:
        print(f"[Uyarı] Görsel üretimi atlandı/hata aldı ({e}), düz renk oluşturuluyor.")
        # Fallback: Ffmpeg ile düz arka plan oluştur
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=navy:s=1080x1920:d=1",
                "-frames:v",
                "1",
                gorsel_yolu,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    # 3. Seslendirme Üretimi (Edge-TTS)
    ses_uret(metin, ses_yolu)

    # 4. FFMPEG ile Görsel ve Sesi Birleştirme (1080x1920, dikey)
    cmd = [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-i",
        gorsel_yolu,
        "-i",
        ses_yolu,
        "-c:v",
        "libx264",
        "-tune",
        "stillimage",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-pix_fmt",
        "yuv420p",
        "-shortest",
        "-s",
        "1080x1920",
        final_video_yolu,
    ]

    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"[BOBİ TV] ❌ ffmpeg birleştirme hatası: {r.stderr[-300:]}")
    else:
        print(f"[BOBİ TV] 🎬 Videoya çevrildi: {os.path.basename(final_video_yolu)}")

    # 4.5. KAPAK GÖRSELİ (2026-11-13): video arka planından AYRI üretilir.
    # NİÇİN: youtube_upload `kapak_dosyasi` alanını okuyup thumbnails.set ile
    # yüklüyor. Bu alan boş kalırsa video kapaksız yayınlanır (kullanıcı bildirdi).
    kapak_yolu = os.path.join(tmp_dir, f"bobi_kapak_{damga}.jpg")
    try:
        ham_kapak = os.path.join(tmp_dir, f"bobi_kapak_ham_{damga}.jpg")
        uretildi = gorsel_uret(kapak_istemini_yaz(baslik), ham_kapak)
        if uretildi:
            kapak_olcekle(ham_kapak, kapak_yolu)
            print(f"[BOBİ TV] ✅ Kapak hazır: {kapak_yolu}")
        else:
            print("[BOBİ TV] ⚠️ Kapak üretilemedi (Gemini), video karesi kullanılacak")
    except Exception as e:
        print(f"[BOBİ TV] ⚠️ Kapak hatası: {e}")

    # Kapağı videonun İLK 1.5 SANİYESİNE göm (kullanıcı kararı 2026-11-11).
    # thumbnails.set `oar2.jpg`'yi değiştiremiyor; kanal ön izlemesinde görünen
    # kare videonun 1. karesidir. Bu yüzden kapak videoya da girmeli.
    if os.path.exists(kapak_yolu):
        yeni_yol = ilk_kareye_gom(final_video_yolu, kapak_yolu)
        if yeni_yol == final_video_yolu:
            print("[BOBİ TV] ❌ KAPAK GÖMÜLEMEDİ — video kapaksız gidiyor")
        else:
            final_video_yolu = yeni_yol
            print(f"[BOBİ TV] 📼 Gömülü dosya: {os.path.basename(final_video_yolu)}")

    # Kapak yoksa videonun 1. karesini kapak yap (üretim durmasın)
    if not os.path.exists(kapak_yolu):
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", final_video_yolu, "-frames:v", "1",
                 "-q:v", "2", kapak_yolu],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60,
            )
        except Exception:
            pass

    # 5. Paket hazırla (yüklemeyi main_pipeline -> toplu_yukle yapar)
    dosya_adi = os.path.splitext(os.path.basename(final_video_yolu))[0]
    paket = {
        "dosya_adi": dosya_adi,
        "final_video": final_video_yolu,
        "baslik": f"{baslik} #shorts",
        "aciklama": f"{metin}\n\n#bobi #ilginçbilgiler #shorts",
        "etiketler": etiketler,
        # youtube_upload bu alanı okur → thumbnails.set ile kapak yüklenir.
        "kapak_dosyasi": kapak_yolu if os.path.exists(kapak_yolu) else "",
    }

    # Yükleme YOK — pipeline `toplu_yukle()` ile yapacak.
    print(f"[BOBİ TV] Paket hazır (yükleme pipeline'da): {baslik}")

    # main_pipeline bu alanı loglar (sözdizimi sözleşmesi)
    try:
        import subprocess as _sp
        _s = _sp.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", final_video_yolu],
            capture_output=True, text=True, timeout=60,
        ).stdout.strip()
        paket["video_suresi"] = round(float(_s), 2) if _s else 0
    except Exception:
        paket["video_suresi"] = 0

    print(f"[BOBİ TV] İşlem tamamlandı: {final_video_yolu}")
    return paket
