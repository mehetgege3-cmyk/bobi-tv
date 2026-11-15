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


# İlginç konu havuzu (Türkçe, sade, "sen" dili)
KONU_LISTESI = [
    {
        "baslik": "Zamanın Nasıl Akıp Gittiğini Fark Ettin mi?",
        "metin": "Göz kırpma süren ortalama 100 milisaniyedir. Eğer hayatın boyunca göz kırptığın tüm süreleri toplarsan, yaklaşık 5 yılını karanlıkta geçirmiş olursun. Şaşırtıcı değil mi?",
        "etiketler": ["ilginçbilgiler", "shorts", "zaman", "bilgi"],
    },
    {
        "baslik": "Beyninin Asla Unutamadığı O Sır",
        "metin": "Yatmadan hemen önce izlediğin veya okuduğun şeyler, beynin tarafından gece boyunca uzun süreli belleğe aktarılır. Yani uykun, aslında senin gizli çalışma masandır.",
        "etiketler": ["beyin", "ilginçbilgiler", "psikoloji", "shorts"],
    },
    {
        "baslik": "Su İçerken Hiç Düşündün mü?",
        "metin": "İçtiğin bir bardak sudaki moleküllerin bir kısmının dinozorlar tarafından milyonlarca yıl önce içilmiş olabileceğini biliyor muydun? Su döngüsü sayesinde dünyadaki su hep aynı kalır.",
        "etiketler": ["su", "bilim", "ilginçbilgiler", "shorts"],
    },
    {
        "baslik": "Gözlerinin Hayret Edeceği Gerçek",
        "metin": "Gözlerimiz doğduğumuz andan itibaren neredeyse hiç büyümez; ancak burun ve kulaklarımız ömür boyu büyümeye devam eder. Vücudumuzdaki bu detay seni de şaşırttı mı?",
        "etiketler": ["vücut", "ilginçbilgiler", "şaşırtıcı", "shorts"],
    },
]


async def ses_uret_async(metin: str, ses_dosyasi: str):
    """Edge-tts kullanarak metni seslendirir (Türkçe - AhmetNeural)."""
    communicate = edge_tts.Communicate(metin, "tr-TR-AhmetNeural")
    await communicate.save(ses_dosyasi)


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
    """Kapağı 1080x1920 (9:16) tuvalde ortalar — görseli KIRPMAZ, uzatMАZ.

    Kapak iki yere gidiyor:
      1) videonun İLK 1.5 SANİYESİ (kullanıcı kararı) → dikey olmalı
      2) YouTube thumbnails.set                      → aynı dosya
    9:16 görsel zaten dikey; tuval yalnızca tam 1080x1920 olsun diye.
    Kenarlar bulanıklaştırılmaz, siyah bar konmaz — görselin kendisi kaplar.
    """
    from PIL import Image

    img = Image.open(kaynak).convert("RGB")
    if img.size != (1080, 1920):
        # en-boy oranını koruyarak 1080x1920'yi KAPLA (cover), ortadan kırp
        olcek = max(1080 / img.width, 1920 / img.height)
        yeni_g, yeni_y = int(img.width * olcek + 0.5), int(img.height * olcek + 0.5)
        img = img.resize((yeni_g, yeni_y), Image.LANCZOS)
        sol, ust = (yeni_g - 1080) // 2, (yeni_y - 1920) // 2
        img = img.crop((sol, ust, sol + 1080, ust + 1920))
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

    NİÇİN: Kanal ön izlemesinde ve Shorts rafında `oar2.jpg` görünür;
    `thumbnails.set` ona dokunamaz (docs/KAPAK_TESHIS.md §KÖK NEDEN 3).
    Tek çözüm: kapağı videonun başına koymak → YouTube onu ilk kare olarak alır.

    ⚠️ 1 kare (33 ms) YETMEZ — ölçüldü, göz görmüyor. En az 1.5 sn olmalı.
    """
    from pathlib import Path

    hedef = str(Path(video).with_name(Path(video).stem + "_kapakli.mp4"))
    filtre = (
        f"[1:v]scale=1080:1920,trim=duration={sn},setpts=PTS-STARTPTS[ilk];"
        f"[ilk][0:v]concat=n=2:v=1:a=0[v];"
        f"[0:a]adelay={int(sn * 1000)}|{int(sn * 1000)},asetpts=PTS-STARTPTS[a]"
    )
    cmd = [
        _ffmpeg(), "-y",
        "-i", video,
        "-loop", "1", "-i", kapak_jpg,
        "-filter_complex", filtre,
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        hedef,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if r.returncode != 0 or not Path(hedef).exists():
        print(f"[BOBİ TV] ⚠️ kapak gömme hatası: {r.stderr[-200:]}")
        return video
    print(f"[BOBİ TV] ✅ Kapak videonun ilk {sn} sn'sine gömüldü")
    return hedef


def video_uret(video_no: int) -> dict:
    """BOBİ TV ana motor fonksiyonu.

    Konu seçer, gorsel_uret ile görsel üretir, edge-tts ile seslendirir, ffmpeg ile
    birleştirip YouTube'a yükler.
    """
    # 1. Konu Seçimi
    konu = KONU_LISTESI[video_no % len(KONU_LISTESI)]
    baslik = konu["baslik"]
    metin = konu["metin"]
    etiketler = konu["etiketler"]

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

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

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
        final_video_yolu = ilk_kareye_gom(final_video_yolu, kapak_yolu)

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
