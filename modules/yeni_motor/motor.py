import os
import random
import subprocess
import tempfile
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


#: KAPAK İSTEMİ — kullanıcının tek cümlesi, BİREBİR (K8). Değiştirme.
def kapak_istemini_yaz(baslik: str) -> str:
    """Kullanıcının kapak istemi — ŞABLON, birebir. Değiştirme, sadeleştirme yapma.

    2026-11-13: yatay (16:9) istendi çünkü YouTube kapak alanı 16:9'dur.
    9:16 görsel gönderilince YouTube %68 blur dolgu ekliyordu (ölçüldü).
    """
    return (
        f"{baslik} İsimli short video için kapak fotoğrafı istiyorum; etkileşim ve "
        "izlenme rekorları kırması için profesyonel şekilde tasarla. Kapak "
        "fotoğrafını gören merak edip tıklasın. "
        "YATAY (16:9) formatta, 1280x720 piksel, manşet kalitesinde üret. "
        "Yazı yazma, sadece görsel olsun."
    )


def kapak_olcekle(kaynak: str, hedef: str) -> str:
    """Kapağı 1280x720 (16:9) yapar — YouTube kapak alanı.

    ÖNEMLİ: 1080x1920 (9:16) GÖNDERME. YouTube 16:9 alana oturturken yanlara
    blur dolgu ekler; ölçüm (2026-11-13): 1280 px'in yalnız 405 px'i gerçek
    görsel, %68'i dolgu → amatör görünüm.
    """
    from PIL import Image

    img = Image.open(kaynak).convert("RGB")
    hg, hy = img.size

    # Zaten 16:9 ise sadece ölçekle
    if abs((hg / hy) - (16 / 9)) < 0.05:
        img.resize((1280, 720), Image.LANCZOS).save(hedef, "JPEG", quality=93)
        return hedef

    # Değilse: 16:9 tuval oluştur, görselin TAMAMINI sığdır (contain),
    # kenarları görselin kendi bulanık hâliyle doldur — siyah bar bırakma.
    tuval = Image.new("RGB", (1280, 720))
    arka = img.copy()
    arka.thumbnail((1280, 720))
    arka = arka.resize((1280, 720), Image.LANCZOS).filter(
        __import__("PIL.ImageFilter", fromlist=["GaussianBlur"]).GaussianBlur(40)
    )
    on = img.copy()
    on.thumbnail((1280, 720), Image.LANCZOS)
    tuval.paste(arka, (0, 0))
    tuval.paste(on, ((1280 - on.width) // 2, (720 - on.height) // 2))
    tuval.save(hedef, "JPEG", quality=93)
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
    gorsel_yolu = os.path.join(tmp_dir, f"bobi_gorsel_{video_no}.jpg")
    ses_yolu = os.path.join(tmp_dir, f"bobi_ses_{video_no}.mp3")
    final_video_yolu = os.path.join(tmp_dir, f"bobi_video_{video_no}.mp4")

    print(f"[BOBİ TV] Video üretiliyor: '{baslik}'")

    # 2. Görsel Üretimi (gorsel_uret fonksiyonu ile)
    # VİDEO ARKA PLANI: konuya özel, dikey, YAZISIZ.
    # Eski istem İngilizce ve geneldi ("A cinematic vertical background
    # representing: ...") → alakasız, rastgele stok görsel çıkıyordu.
    prompt_metin = (
        f"Dikey (9:16) sinematik fotoğraf, konu: {konu['metin'][:120]}. "
        "Tek bir güçlü görsel, yakın plan, sıcak ışık, yüksek detay. "
        "ÜZERİNDE YAZI OLMAYACAK, logo yok, filigran yok, insan yüzü yok."
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
    kapak_yolu = os.path.join(tmp_dir, f"bobi_kapak_{video_no}.jpg")
    try:
        ham_kapak = os.path.join(tmp_dir, f"bobi_kapak_ham_{video_no}.jpg")
        uretildi = gorsel_uret(kapak_istemini_yaz(baslik), ham_kapak)
        if uretildi:
            kapak_olcekle(ham_kapak, kapak_yolu)
            print(f"[BOBİ TV] ✅ Kapak hazır: {kapak_yolu}")
        else:
            print("[BOBİ TV] ⚠️ Kapak üretilemedi (Gemini), video karesi kullanılacak")
    except Exception as e:
        print(f"[BOBİ TV] ⚠️ Kapak hatası: {e}")

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
