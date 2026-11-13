import os
import random
import subprocess
import tempfile
from google import genai
from google.genai import types

# Modülün gerektirdiği bağımlılıklar:
# pip install google-genai edge-tts pillow requests (ve sistemde ffmpeg kurulu olmalı)
import edge_tts
from PIL import Image

# YouTube yükleyici modülü çağrısı (proje yapısındaki mevcut dosya)
try:
    from modules.youtube_upload import video_yukle
except ImportError:
    # Test ortamları veya bağımlı modülün henüz yüklenmediği durumlar için fallback
    def video_yukle(paket):
        print(f"[MOCK] YouTube Yükleme Simülasyonu: {paket}")
        return True


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


def gorsel_uret(prompt_metin: str, cikis_yolu: str):
    """Gemini API kullanarak dikey (9:16) arka plan görseli üretir."""
    client = genai.Client()
    # Gemini 2.5 Flash / Imagen modeli ile dikey görsel üretimi
    response = client.models.generate_images(
        model="imagen-3.0-generate-002",
        prompt=f"{prompt_metin}, cinematic lighting, 8k resolution, highly detailed, vertical aspect ratio",
        config=types.GenerateImagesConfig(
            number_of_images=1,
            output_mime_type="image/jpeg",
            aspect_ratio="9:16",
        ),
    )

    for generated_image in response.generated_images:
        image = Image.open(BytesIO(generated_image.image.image_bytes))
        image.save(cikis_yolu)
        return True
    raise RuntimeError("Görsel üretilemedi.")


import asyncio
from io import BytesIO


async def ses_uret_async(metin: str, ses_dosyasi: str):
    """Edge-tts kullanarak metni seslendirir (Türkçe - Ahmet veya Dilara)."""
    communicate = edge_tts.Communicate(metin, "tr-TR-AhmetNeural")
    await communicate.save(ses_dosyasi)


def ses_uret(metin: str, ses_dosyasi: str):
    asyncio.run(ses_uret_async(metin, ses_dosyasi))


def video_uret(video_no: int) -> dict:
    """BOBİ TV ana motor fonksiyonu.

    Konu seçer, Gemini ile görsel üretir, edge-tts ile seslendirir, ffmpeg ile
    birleştirip YouTube'a yükler.
    """
    # 1. Konu Seçimi
    konu = KONU_LISTESI[video_no % len(KONU_LISTESI)]
    baslik = konu["baslik"]
    metin = konu["metin"]
    etiketler = konu["etiketler"]

    # Geçici dosya yolları
    tmp_dir = tempfile.gettempdir()
    gorsel_yolu = os.path.join(tmp_dir, f"bobi_gorsel_{video_no}.jpg")
    ses_yolu = os.path.join(tmp_dir, f"bobi_ses_{video_no}.mp3")
    final_video_yolu = os.path.join(tmp_dir, f"bobi_video_{video_no}.mp4")

    print(f"[BOBİ TV] Video üretiliyor: '{baslik}'")

    # 2. Görsel Üretimi (Gemini)
    try:
        gorsel_uret(
            f"A cinematic vertical background representing: {baslik}, minimalist aesthetic, engaging social media style",
            gorsel_yolu,
        )
    except Exception as e:
        print(f"[Uyarı] Gemini görsel üretimi atlandı/hata aldı ({e}), düz renk oluşturuluyor.")
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
    # Ses süresine göre video süresini ayarlama
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

    # 5. YouTube Yükleme Paketi Hazırlama
    paket = {
        "final_video": final_video_yolu,
        "baslik": f"{baslik} #shorts",
        "aciklama": f"{metin}\n\n#bobi #ilginçbilgiler #shorts",
        "etiketler": etiketler,
    }

    # YouTube'a Yükle
    print("[BOBİ TV] YouTube'a yükleniyor...")
    video_yukle(paket)

    print(f"[BOBİ TV] İşlem tamamlandı: {final_video_yolu}")
    return paket
