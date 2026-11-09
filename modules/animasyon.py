"""
BOBİ TV — Pro Görsel Sahne, Vektör Karakter Kartı ve Aktif-Kelime Karaoke Motoru v6.0
Özellikler:
- Sıfır geçici PNG: Ham kareler doğrudan FFmpeg stdin borusuna (pipe) akar (çok hızlı ve bellek dostu)
- YouTube Shorts Güvenli Bölge (Safe Zone) uyumlu yerleşim (üst bar, sağ butonlar ve alt açıklama alanı boş)
- Ses genliğine (RMS) duyarlı konuşan karakter halkası ve canlı ekolayzır çubukları
- Vektörel karakter avatarları (Müdür, İK/Kadın, Doktor, Yapay Zeka/Robot, Kedi, Şoför vb. — kırık emoji kutusu □ riski %0)
- Yaylanarak açılan (easeOutBack) cam efektli konuşma balonları
- CapCut / Hormozi stili yuvarlatılmış renkli kutulu (pill) kelime-kelime aktif karaoke altyazı
- Twist anında %118 dinamik zoom + kamera sarsıntısı (shake) + şok flaşı
- Opsiyonel Pexels dikey B-Roll arka plan desteği + Prosedürel Bokeh Stüdyo zemini
"""
import os
import re
import math
import wave
import subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
FPS = 30

FONT_YOLLARI = [
    "bobi_tv/assets/fonts/Montserrat-ExtraBold.ttf",
    "bobi_tv/assets/fonts/Montserrat-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]

# Kategoriye özel zengin sinematik stüdyo paletleri: (Üst RGB, Alt RGB, Vurgu1 RGB, Vurgu2 RGB)
KATEGORI_PALETLERI = {
    "kahve_hayati":       ((26, 14, 10),  (58, 28, 16),  (255, 196, 46),  (255, 112, 67)),
    "kurumsal_hayat":     ((10, 16, 36),  (24, 38, 78),  (56, 189, 248),  (250, 204, 21)),
    "ik_toplantisi":      ((14, 12, 38),  (38, 22, 72),  (168, 85, 247),  (250, 204, 21)),
    "pazartesi_sendromu": ((28, 10, 24),  (62, 16, 38),  (255, 59, 92),   (255, 214, 10)),
    "yapay_zeka":         ((6, 20, 32),   (12, 46, 64),  (0, 245, 212),   (59, 130, 246)),
    "saglik_sorunu":      ((8, 24, 34),   (18, 52, 68),  (52, 211, 153),  (250, 204, 21)),
    "trafik_kavgasi":     ((26, 16, 12),  (54, 26, 18),  (251, 146, 60),  (250, 204, 21)),
    "diyet_kavrami":      ((12, 28, 18),  (24, 56, 34),  (134, 239, 172), (250, 204, 21)),
    "varsayilan":         ((12, 14, 36),  (32, 20, 68),  (255, 214, 10),  (56, 189, 248)),
}

_FONT_ONBELLEK = {}


def font_al(boyut: int) -> ImageFont.FreeTypeFont:
    if boyut in _FONT_ONBELLEK:
        return _FONT_ONBELLEK[boyut]
    for yol in FONT_YOLLARI:
        if os.path.exists(yol):
            try:
                f = ImageFont.truetype(yol, boyut)
                _FONT_ONBELLEK[boyut] = f
                return f
            except Exception:
                continue
    f = ImageFont.load_default()
    _FONT_ONBELLEK[boyut] = f
    return f


def emoji_temizle(metin: str) -> str:
    return re.sub(
        r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF\uFE0F\u200D]+",
        "",
        str(metin),
    ).strip()


def tr_upper(metin: str) -> str:
    """Türkçe karakter uyumlu büyük harf dönüşümü (i -> İ, ı -> I)."""
    return str(metin).replace("i", "İ").replace("ı", "I").upper()


def metin_satirla(draw: ImageDraw.ImageDraw, metin: str, font, maks_genislik: int) -> list:
    kelimeler = metin.split()
    if not kelimeler:
        return [""]
    satirlar, mevcut = [], ""
    for k in kelimeler:
        aday = f"{mevcut} {k}".strip()
        bb = draw.textbbox((0, 0), aday, font=font)
        if (bb[2] - bb[0]) <= maks_genislik or not mevcut:
            mevcut = aday
        else:
            satirlar.append(mevcut)
            mevcut = k
    if mevcut:
        satirlar.append(mevcut)
    return satirlar


def _ses_zarfi_cikar(wav_yolu: str, toplam_kare: int) -> np.ndarray:
    """Her video karesi için [0.0, 1.0] aralığında konuşma enerji zarfı hesaplar."""
    zarf = np.zeros(max(1, toplam_kare), dtype=np.float32)
    if not wav_yolu or not os.path.exists(wav_yolu):
        return zarf
    try:
        with wave.open(wav_yolu, "rb") as wf:
            sr = wf.getframerate()
            ham = wf.readframes(wf.getnframes())
        arr = np.abs(np.frombuffer(ham, dtype=np.int16).astype(np.float32) / 32768.0)
        kare_ornek = max(1, int(sr / FPS))
        for i in range(toplam_kare):
            dilim = arr[i * kare_ornek:(i + 1) * kare_ornek]
            if len(dilim) > 0:
                zarf[i] = min(1.0, float(np.sqrt(np.mean(dilim * dilim))) * 4.8)
    except Exception:
        pass
    return zarf


def _vektor_avatar_ciz(karakter: str, cinsiyet: str, taraf: str, boyut: int = 136) -> Image.Image:
    """
    Kırık emoji kutusu riski olmadan her karaktere özel keskin vektörel portre rozeti çizer.
    """
    ss = 2
    B = boyut * ss
    img = Image.new("RGBA", (B, B), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    ad = karakter.upper()
    ana_renk = (56, 189, 248) if taraf == "sol" else (244, 114, 182)
    if "MÜDÜR" in ad or "PATRON" in ad or "YÖNETİCİ" in ad:
        ana_renk = (245, 158, 11)
    elif "DOKTOR" in ad or "HEMŞİRE" in ad or "DİYET" in ad:
        ana_renk = (16, 185, 129)
    elif "YAPAY" in ad or "ALARM" in ad or "NAVİGASYON" in ad:
        ana_renk = (0, 245, 212)

    # Dış daire gölge + renkli zemin
    d.ellipse([6, 6, B - 6, B - 6], fill=(*ana_renk, 255), outline=(255, 255, 255, 245), width=8)

    # Robot / Yapay Zeka / Alarm özel ikonu
    if any(k in ad for k in ("YAPAY", "ROBOT", "ALARM", "NAVİGASYON")):
        d.rounded_rectangle([B * 0.24, B * 0.28, B * 0.76, B * 0.74], radius=28, fill=(18, 24, 42, 255), outline=(255, 255, 255, 255), width=6)
        # Parlayan vizör gözler
        d.ellipse([B * 0.33, B * 0.43, B * 0.45, B * 0.55], fill=(0, 245, 212, 255))
        d.ellipse([B * 0.55, B * 0.43, B * 0.67, B * 0.55], fill=(0, 245, 212, 255))
        d.rounded_rectangle([B * 0.38, B * 0.62, B * 0.62, B * 0.67], radius=6, fill=(255, 214, 10, 255))
        # Anten
        d.line([(B * 0.5, B * 0.14), (B * 0.5, B * 0.28)], fill=(255, 255, 255, 255), width=7)
        d.ellipse([B * 0.45, B * 0.09, B * 0.55, B * 0.19], fill=(255, 70, 90, 255))
    else:
        # İnsan yüzü + saç + aksesuar
        ten = (255, 224, 189, 255)
        sac = (45, 30, 24, 255) if cinsiyet != "kadin" else (92, 38, 68, 255)

        if cinsiyet == "kadin":
            d.ellipse([B * 0.20, B * 0.18, B * 0.80, B * 0.84], fill=sac)
        # Omuz / Ceket
        ceket = (22, 30, 54, 255) if taraf == "sol" else (88, 28, 68, 255)
        if "DOKTOR" in ad:
            ceket = (245, 248, 252, 255)
        d.pieslice([B * 0.18, B * 0.62, B * 0.82, B * 1.12], start=180, end=360, fill=ceket)

        # Kravat (Müdür/Patron/Erkek)
        if "MÜDÜR" in ad or "PATRON" in ad:
            d.polygon([(B * 0.50, B * 0.68), (B * 0.45, B * 0.86), (B * 0.55, B * 0.86)], fill=(239, 68, 68, 255))

        # Baş
        d.ellipse([B * 0.27, B * 0.24, B * 0.73, B * 0.72], fill=ten)
        # Üst saç
        d.pieslice([B * 0.25, B * 0.18, B * 0.75, B * 0.56], start=180, end=360, fill=sac)

        # Gözler ve ifade kaşları
        d.ellipse([B * 0.37, B * 0.44, B * 0.44, B * 0.51], fill=(20, 20, 30, 255))
        d.ellipse([B * 0.56, B * 0.44, B * 0.63, B * 0.51], fill=(20, 20, 30, 255))
        d.line([(B * 0.35, B * 0.39), (B * 0.45, B * 0.41)], fill=sac, width=6)
        d.line([(B * 0.55, B * 0.41), (B * 0.65, B * 0.39)], fill=sac, width=6)

        # Ağız
        d.arc([B * 0.41, B * 0.53, B * 0.59, B * 0.64], start=10, end=170, fill=(185, 50, 60, 255), width=6)

    return img.resize((boyut, boyut), Image.LANCZOS)


def _pexels_broll_indir(sorgu: str, hedef_mp4: Path) -> bool:
    """PEXELS_API_KEY tanımlıysa dikey HD stok video indirir."""
    api_key = os.environ.get("PEXELS_API_KEY", "").strip()
    if not api_key:
        return False
    try:
        import requests
        r = requests.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": api_key},
            params={"query": sorgu, "orientation": "portrait", "size": "medium", "per_page": 5},
            timeout=12,
        )
        if r.status_code != 200:
            return False
        videolar = r.json().get("videos") or []
        for v in videolar:
            dosyalar = sorted(
                [f for f in v.get("video_files", []) if f.get("height", 0) >= 720 and f.get("width", 0) <= f.get("height", 0)],
                key=lambda x: abs(x.get("height", 0) - 1920),
            )
            if dosyalar:
                indir = requests.get(dosyalar[0]["link"], timeout=25)
                if indir.status_code == 200 and len(indir.content) > 50_000:
                    hedef_mp4.write_bytes(indir.content)
                    return True
    except Exception as e:
        print(f"[B-Roll] Pexels atlandı: {e}")
    return False


def _baz_arkaplan_matrisi(kategori: str) -> tuple:
    """1920x1080x3 float32 baz gradyan + vinyet matrisi üretir (tek seferlik hesaplanır)."""
    ust, alt, vurgu1, vurgu2 = KATEGORI_PALETLERI.get(kategori, KATEGORI_PALETLERI["varsayilan"])
    y_oran = np.linspace(0.0, 1.0, H, dtype=np.float32)[:, None, None]
    ust_arr = np.array(ust, dtype=np.float32)[None, None, :]
    alt_arr = np.array(alt, dtype=np.float32)[None, None, :]
    baz = ust_arr * (1.0 - y_oran) + alt_arr * y_oran
    baz = np.broadcast_to(baz, (H, W, 3)).copy()

    # Yumuşak sinematik kenar vinyeti
    yy, xx = np.ogrid[:H, :W]
    merkez_uzaklik = ((xx - W * 0.5) / (W * 0.62)) ** 2 + ((yy - H * 0.48) / (H * 0.58)) ** 2
    vinyet = np.clip(1.0 - 0.34 * merkez_uzaklik, 0.52, 1.0).astype(np.float32)[:, :, None]
    baz *= vinyet
    return baz, vurgu1, vurgu2


def _ust_kanca_karti_olustur(hook_metni: str, twist_modu: bool = False) -> Image.Image:
    """Ekranın üst güvenli bölgesinde (y=170) dikkat çekici kanca başlık bandı üretir."""
    kart_g, kart_y = 920, 168
    img = Image.new("RGBA", (kart_g, kart_y), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    arka = (220, 24, 58, 245) if twist_modu else (255, 214, 10, 248)
    kenar = (255, 255, 255, 255) if twist_modu else (20, 20, 35, 255)
    yazi_renk = (255, 255, 255, 255) if twist_modu else (14, 14, 24, 255)

    # Gölge + ana kutu
    d.rounded_rectangle([8, 10, kart_g - 2, kart_y - 2], radius=28, fill=(0, 0, 0, 140))
    d.rounded_rectangle([0, 0, kart_g - 10, kart_y - 10], radius=28, fill=arka, outline=kenar, width=5)

    temiz = tr_upper(emoji_temizle(hook_metni))
    f = font_al(44 if len(temiz) <= 26 else 36)
    satirlar = metin_satirla(d, temiz, f, kart_g - 70)[:2]
    satir_yuk = 48 if len(satirlar) > 1 else 54
    bas_y = ((kart_y - 10) - len(satirlar) * satir_yuk) // 2 - 2

    for s in satirlar:
        bb = d.textbbox((0, 0), s, font=f)
        x = ((kart_g - 10) - (bb[2] - bb[0])) // 2
        d.text((x, bas_y), s, font=f, fill=yazi_renk)
        bas_y += satir_yuk

    return img


def _konusma_balonu_olustur(
    karakter: str,
    metin: str,
    taraf: str,
    avatar: Image.Image,
    twist_mi: bool = False,
    soluk_mu: bool = False,
) -> Image.Image:
    """Avatarlı, cam efektli modern konuşma kartı üretir (önbelleklenir)."""
    kart_g = 900
    f_isim = font_al(28)
    f_metin = font_al(38)
    gecici = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    temiz_metin = emoji_temizle(metin)
    satirlar = metin_satirla(gecici, temiz_metin, f_metin, kart_g - 235)[:4]
    kart_y = max(176, 86 + len(satirlar) * 48)

    img = Image.new("RGBA", (kart_g, kart_y), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    alfa_katsayi = 0.52 if soluk_mu else 1.0
    vurgu = (255, 59, 92) if twist_mi else ((56, 189, 248) if taraf == "sol" else (244, 114, 182))
    kutu_alfa = int(228 * alfa_katsayi)
    kenar_alfa = int(245 * alfa_katsayi)

    balon_sol = 158 if taraf == "sol" else 12
    balon_sag = kart_g - 12 if taraf == "sol" else kart_g - 158

    # Gölge + Cam Kart
    if not soluk_mu:
        d.rounded_rectangle([balon_sol + 6, 14, balon_sag + 6, kart_y - 2], radius=30, fill=(0, 0, 0, 125))
    d.rounded_rectangle(
        [balon_sol, 6, balon_sag, kart_y - 10],
        radius=30,
        fill=(22, 26, 48, kutu_alfa),
        outline=(*vurgu, kenar_alfa),
        width=4 if not twist_mi else 6,
    )

    # Karakter rozeti
    etiket = tr_upper(emoji_temizle(karakter))
    ibb = d.textbbox((0, 0), etiket, font=f_isim)
    rozet_g = (ibb[2] - ibb[0]) + 34
    rozet_x = balon_sol + 26 if taraf == "sol" else balon_sag - rozet_g - 26
    d.rounded_rectangle(
        [rozet_x, 20, rozet_x + rozet_g, 58],
        radius=14,
        fill=(*vurgu, int(235 * alfa_katsayi)),
    )
    d.text((rozet_x + 17, 23), etiket, font=f_isim, fill=(12, 14, 24, int(255 * alfa_katsayi)))

    # Diyalog satırları
    y_imlec = 70
    for s in satirlar:
        if taraf == "sol":
            x_yazi = balon_sol + 28
        else:
            sbb = d.textbbox((0, 0), s, font=f_metin)
            x_yazi = max(balon_sol + 24, balon_sag - (sbb[2] - sbb[0]) - 28)
        d.text(
            (x_yazi, y_imlec),
            s,
            font=f_metin,
            fill=(255, 255, 255, int(250 * alfa_katsayi)),
        )
        y_imlec += 46

    # Avatar yerleştirme
    av_x = 6 if taraf == "sol" else kart_g - avatar.width - 6
    av_y = (kart_y - avatar.height) // 2
    if soluk_mu:
        av_kopya = avatar.copy()
        r, g, b, a = av_kopya.split()
        a = a.point(lambda p: int(p * 0.55))
        av_kopya = Image.merge("RGBA", (r, g, b, a))
        img.alpha_composite(av_kopya, (av_x, av_y))
    else:
        img.alpha_composite(avatar, (av_x, av_y))

    return img


def _karaoke_altyazi_katmani(
    kelime_grubu: list,
    aktif_idx: int,
    twist_mi: bool = False,
    stil: str = "normal",
) -> Image.Image:
    """
    CapCut / Hormozi stili:
    2-3 kelimelik satırda o salise okunan kelimenin arkasına parlak yuvarlatılmış kutu (pill)
    ve %112 büyüklük vurgusu çizer! Tüm kelimeler aynı taban çizgisinde (baseline) hizalanır.
    """
    kat_g, kat_y = 960, 210
    img = Image.new("RGBA", (kat_g, kat_y), (0, 0, 0, 0))
    if not kelime_grubu:
        return img

    d = ImageDraw.Draw(img)

    def _satir_olc(boyut_n: int, boyut_a: int, bosluk_px: int):
        fn = font_al(boyut_n)
        fa = font_al(boyut_a)
        liste = []
        top_g = 0
        for idx, k in enumerate(kelime_grubu):
            metin = tr_upper(emoji_temizle(k["kelime"]))
            if not metin:
                continue
            aktif = (idx == aktif_idx)
            f = fa if aktif else fn
            bb = d.textbbox((0, 0), metin, font=f, anchor="lm", stroke_width=6)
            kg = bb[2] - bb[0]
            liste.append((metin, aktif, f, kg, bb))
            top_g += kg
        if liste:
            top_g += bosluk_px * (len(liste) - 1)
        return liste, top_g

    buyuk = stil == "büyük"
    font_normal, font_aktif = (66, 74) if buyuk else (58, 64)
    bosluk = 24
    parcalar, toplam_g = _satir_olc(font_normal, font_aktif, bosluk)
    if not parcalar:
        return img

    if toplam_g > kat_g - 56:
        bosluk = 18
        parcalar, toplam_g = _satir_olc(45, 50)

    x_imlec = (kat_g - toplam_g) // 2
    merkez_y = kat_y // 2

    kutu_renk = (
        (255, 42, 84, 252)
        if twist_mi
        else (45, 170, 255, 252)
        if stil == "renkli"
        else (255, 214, 10, 252)
    )
    aktif_yazi_renk = (255, 255, 255, 255) if twist_mi or stil == "renkli" else (14, 14, 24, 255)

    # Önce aktif kelimenin yuvarlatılmış kutusunu çiz
    gecici_x = x_imlec
    for metin, aktif, f, kg, bb in parcalar:
        if aktif:
            y_ust = merkez_y + bb[1] - 14
            y_alt = merkez_y + bb[3] + 14
            d.rounded_rectangle(
                [gecici_x - 16, y_ust + 5, gecici_x + kg + 16, y_alt + 5],
                radius=20,
                fill=(0, 0, 0, 150),
            )
            d.rounded_rectangle(
                [gecici_x - 16, y_ust, gecici_x + kg + 16, y_alt],
                radius=20,
                fill=kutu_renk,
            )
        gecici_x += kg + bosluk

    # Tüm kelimeleri aynı sol-orta (lm) taban çizgisinde çiz -> sıfır dikey kayma!
    gecici_x = x_imlec
    for metin, aktif, f, kg, bb in parcalar:
        if aktif:
            d.text((gecici_x, merkez_y), metin, font=f, anchor="lm", fill=aktif_yazi_renk)
        else:
            d.text(
                (gecici_x, merkez_y),
                metin,
                font=f,
                anchor="lm",
                fill=(255, 255, 255, 255),
                stroke_width=6,
                stroke_fill=(0, 0, 0, 255),
            )
        gecici_x += kg + bosluk

    if stil == "titreşimli":
        img = img.rotate(2 if aktif_idx % 2 == 0 else -2, resample=Image.BICUBIC, center=(kat_g // 2, kat_y // 2))
    return img


def pro_sahne_videosu_uret(
    senaryo_paketi: dict,
    birlesik_ses_wav: str,
    cikis_video_mp4: str,
) -> str:
    """
    Tüm görsel katmanları 1080x1920 30FPS olarak birleştirip doğrudan FFmpeg borusuyla
    nihai MP4 dosyasına encode eder.
    """
    senaryo = senaryo_paketi["senaryo"]
    ses_dosyalari = senaryo_paketi.get("ses_dosyalari", [])
    kategori = senaryo.get("kategori", "varsayilan")
    hook_bant_metni = senaryo.get("hook_ust_bant") or senaryo.get("hook_metni") or "BOBİ TV"

    toplam_sure = sum(
        float(s.get("sure", 1.8))
        + (int(s.get("duraklamams", 0)) / 1000 if index < len(ses_dosyalari) - 1 else 0.0)
        for index, s in enumerate(ses_dosyalari)
    )
    toplam_kare = max(30, int(round(toplam_sure * FPS)))
    ses_zarfi = _ses_zarfi_cikar(birlesik_ses_wav, toplam_kare)

    baz_matris, vurgu1, vurgu2 = _baz_arkaplan_matrisi(kategori)

    # Bokeh küre merkezleri (normalize koordinatlar)
    kureler = [
        (0.22, 0.28, 210, vurgu1, 0.22, 0.9),
        (0.78, 0.62, 250, vurgu2, 0.18, 1.3),
        (0.35, 0.78, 180, vurgu1, 0.15, 1.7),
    ]
    yy_kucuk, xx_kucuk = np.mgrid[0:H:4, 0:W:4].astype(np.float32)

    # Üst kanca kartları (normal ve twist anı için önbellekli)
    kanca_normal = _ust_kanca_karti_olustur(hook_bant_metni, twist_modu=False)
    kanca_twist = _ust_kanca_karti_olustur(hook_bant_metni, twist_modu=True)

    # Üst BOBİ TV marka rozeti
    marka_katman = Image.new("RGBA", (240, 62), (0, 0, 0, 0))
    md = ImageDraw.Draw(marka_katman)
    md.rounded_rectangle([0, 0, 236, 58], radius=29, fill=(14, 16, 32, 195), outline=(255, 214, 10, 210), width=3)
    md.ellipse([18, 17, 42, 41], fill=(255, 42, 84, 255))
    md.text((54, 11), "BOBİ TV", font=font_al(28), fill=(255, 255, 255, 255))

    # Diyalog segmentlerini zaman çizelgesine yerleştir ve görsel kartları önbellekle
    avatar_onbellek = {}
    segmentler = []
    imlec_sn = 0.0

    for idx, s in enumerate(ses_dosyalari):
        sure = float(s.get("sure", 1.8))
        karakter = s.get("karakter", "BOBİ")
        cinsiyet = s.get("cinsiyet", "erkek")
        taraf = s.get("taraf", "sol" if idx % 2 == 0 else "sag")
        twist_mi = bool(s.get("twist_mi", False))

        av_key = (karakter.upper(), cinsiyet, taraf)
        if av_key not in avatar_onbellek:
            avatar_onbellek[av_key] = _vektor_avatar_ciz(karakter, cinsiyet, taraf)

        aktif_kart = _konusma_balonu_olustur(
            karakter, s["metin"], taraf, avatar_onbellek[av_key], twist_mi=twist_mi, soluk_mu=False
        )
        soluk_kart = _konusma_balonu_olustur(
            karakter, s["metin"], taraf, avatar_onbellek[av_key], twist_mi=False, soluk_mu=True
        )

        # Kelimeleri 3'lü karaoke gruplarına böl ve her aktif kelime durumunu önbellekle
        zamanlar = s.get("zamanlamalar", [])
        kelime_durumlari = []
        grup_boyut = 3
        for g_bas in range(0, len(zamanlar), grup_boyut):
            grup = zamanlar[g_bas:g_bas + grup_boyut]
            for k_i, k_obj in enumerate(grup):
                katman_img = _karaoke_altyazi_katmani(
                    grup,
                    k_i,
                    twist_mi=twist_mi,
                    stil=str(s.get("altyazistili", "normal")),
                )
                kelime_durumlari.append({
                    "bas": imlec_sn + k_obj["baslangic"],
                    "bit": imlec_sn + k_obj["bitis"],
                    "img": katman_img,
                })

        pause_seconds = int(s.get("duraklamams", 0)) / 1000 if idx < len(ses_dosyalari) - 1 else 0.0
        segmentler.append({
            "idx": idx,
            "bas": imlec_sn,
            "bit": imlec_sn + sure + pause_seconds,
            "taraf": taraf,
            "twist_mi": twist_mi,
            "kamera": str(s.get("kamera", "cut")),
            "emojioverlay": s.get("emojioverlay"),
            "aktif_kart": aktif_kart,
            "soluk_kart": soluk_kart,
            "kelime_durumlari": kelime_durumlari,
        })
        imlec_sn += sure + pause_seconds

    # FFmpeg ham video + master ses birleştirme süreci
    Path(cikis_video_mp4).parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}",
        "-r", str(FPS),
        "-i", "-",
        "-i", str(birlesik_ses_wav),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "20",
        "-g", "25",
        "-force_key_frames", "expr:eq(n,0)",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        str(cikis_video_mp4),
    ]

    # 1. Kareye (Frame 0) yerleştirilecek profesyonel kapak görselini hazırla
    from modules.kapak_uret import kapak_resmi_olustur

    kapak_yolu = senaryo_paketi.get("kapak_yolu") or str(cikis_video_mp4).replace(".mp4", "_thumb.jpg")
    if not os.path.exists(kapak_yolu):
        kapak_resmi_olustur(senaryo_paketi, kapak_yolu)
    senaryo_paketi["kapak_yolu"] = kapak_yolu
    ilk_kare_kapak_rgb = Image.open(kapak_yolu).convert("RGB").resize((W, H), Image.BILINEAR)

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    rng_shake = np.random.default_rng(77)

    try:
        seg_ptr = 0
        for kare_no in range(toplam_kare):
            # KURAL: Videonun 1. karesi (Frame 0, t=0.00s) profesyonel kapak fotoğrafıdır
            if kare_no == 0:
                proc.stdin.write(ilk_kare_kapak_rgb.tobytes())
                continue

            t = kare_no / float(FPS)
            enerji = float(ses_zarfi[kare_no])

            while seg_ptr < len(segmentler) - 1 and t >= segmentler[seg_ptr]["bit"]:
                seg_ptr += 1
            seg = segmentler[seg_ptr]
            onceki_seg = segmentler[seg_ptr - 1] if seg_ptr > 0 else None
            yerel_t = max(0.0, t - seg["bas"])

            # 1. Canlı Hareketli Bokeh Stüdyo Arka Planı (düşük çözünürlüklü ışık + tam çözünürlüklü baz)
            isik = np.zeros((H // 4, W // 4, 3), dtype=np.float32)
            for kx, ky, yaricap, renk, guc, hiz in kureler:
                cx = (kx + 0.09 * math.sin(t * hiz)) * (W / 4.0)
                cy = (ky + 0.07 * math.cos(t * hiz * 0.85)) * (H / 4.0)
                r_kucuk = (yaricap * (1.0 + 0.16 * enerji)) / 4.0
                d2 = (xx_kucuk - cx) ** 2 + (yy_kucuk - cy) ** 2
                maske = np.exp(-d2 / (2.0 * r_kucuk * r_kucuk)) * guc
                isik += maske[:, :, None] * np.array(renk, dtype=np.float32)[None, None, :]

            isik_tam = np.repeat(np.repeat(isik, 4, axis=0), 4, axis=1)
            kare_rgb = np.clip(baz_matris + isik_tam, 0, 255).astype(np.uint8)

            # Twist ilk 0.18 saniyesinde sinematik kırmızı/beyaz şok flaşı
            if seg["twist_mi"] and yerel_t < 0.18:
                flas = (1.0 - yerel_t / 0.18) * 55.0
                kare_rgb = np.clip(kare_rgb.astype(np.float32) + np.array([flas * 1.4, flas * 0.3, flas * 0.4]), 0, 255).astype(np.uint8)

            tuval = Image.fromarray(kare_rgb, mode="RGB").convert("RGBA")
            cizim = ImageDraw.Draw(tuval)

            # 2. Üst Marka Rozeti + Kanca Bandı (Güvenli Bölge y=72 ve y=165)
            tuval.alpha_composite(marka_katman, ((W - marka_katman.width) // 2, 74))

            kanca_img = kanca_twist if seg["twist_mi"] else kanca_normal
            if kare_no < 8:
                # İlk 8 karede yaylanarak giriş
                oran = kare_no / 8.0
                olcek = 0.78 + 0.26 * math.sin(oran * math.pi * 0.68)
                yg = max(10, int(kanca_img.width * olcek))
                yy = max(10, int(kanca_img.height * olcek))
                k_kopya = kanca_img.resize((yg, yy), Image.BILINEAR)
                tuval.alpha_composite(k_kopya, ((W - yg) // 2, 162 + (kanca_img.height - yy) // 2))
            else:
                tuval.alpha_composite(kanca_img, ((W - kanca_img.width) // 2, 162))

            # 3. Önceki Konuşma Balonu (üstte hafif soluk bağlam olarak kalır)
            if onceki_seg is not None:
                ust_kart = onceki_seg["soluk_kart"]
                tuval.alpha_composite(ust_kart, ((W - ust_kart.width) // 2 - 20, 395))

            # 4. Aktif Konuşma Balonu (easeOutBack yaylanma + sesle nefes alma)
            aktif_kart = seg["aktif_kart"]
            hedef_y = 665 if onceki_seg is not None else 540
            if yerel_t < 0.18:
                p = yerel_t / 0.18
                c1 = 1.70158
                c3 = c1 + 1.0
                yay = 1.0 + c3 * ((p - 1.0) ** 3) + c1 * ((p - 1.0) ** 2)
                olcek_b = max(0.75, min(1.08, yay))
            else:
                olcek_b = 1.0 + 0.018 * enerji

            bg_w = max(20, int(aktif_kart.width * olcek_b))
            bg_h = max(20, int(aktif_kart.height * olcek_b))
            kart_render = aktif_kart.resize((bg_w, bg_h), Image.BILINEAR) if abs(olcek_b - 1.0) > 0.006 else aktif_kart
            kart_x = (W - kart_render.width) // 2 - 18
            kart_y = hedef_y + (aktif_kart.height - kart_render.height) // 2
            tuval.alpha_composite(kart_render, (kart_x, kart_y))

            # 5. Canlı Ses Dalgası Çubukları (y=1145 — konuşma enerjisiyle senkron dans eder)
            cubuk_sayisi = 21
            merkez_x = W // 2 - 15
            for cb in range(cubuk_sayisi):
                uzaklik = abs(cb - cubuk_sayisi // 2) / (cubuk_sayisi / 2.0)
                faz = math.sin(t * 16.0 + cb * 0.75) * 0.5 + 0.5
                yukseklik = int(8 + (52 * enerji * (1.0 - 0.55 * uzaklik) * (0.45 + 0.55 * faz)))
                cx = merkez_x + (cb - cubuk_sayisi // 2) * 24
                renk_cb = (255, 42, 84, 220) if seg["twist_mi"] else (255, 214, 10, 210)
                cizim.rounded_rectangle(
                    [cx - 6, 1165 - yukseklik, cx + 6, 1165 + yukseklik],
                    radius=6,
                    fill=renk_cb,
                )

            # 6. Aktif-Kelime Kutulu Karaoke Altyazı (y=1255 — YouTube alt açıklama alanının üstünde!)
            aktif_altyazi = None
            for kd in seg["kelime_durumlari"]:
                if kd["bas"] <= t <= kd["bit"]:
                    aktif_altyazi = kd["img"]
                    break
            if aktif_altyazi is None and seg["kelime_durumlari"]:
                # Kelime arası mikroskobik boşlukta en yakın kelimeyi koru
                en_yakin = min(seg["kelime_durumlari"], key=lambda x: min(abs(t - x["bas"]), abs(t - x["bit"])))
                aktif_altyazi = en_yakin["img"]

            if aktif_altyazi is not None:
                tuval.alpha_composite(aktif_altyazi, ((W - aktif_altyazi.width) // 2 - 10, 1255))

            # 7. Alt Altın İlerleme Çubuğu (Loop Progress Bar — y=1906..1920)
            ilerleme_g = int(W * ((kare_no + 1) / float(toplam_kare)))
            cizim.rectangle([0, H - 14, W, H], fill=(255, 255, 255, 45))
            cizim.rectangle([0, H - 14, ilerleme_g, H], fill=(255, 214, 10, 255))

            son_rgb = tuval.convert("RGB")

            # Satır başına kesme/zoom/shake/whippan; twist gerektiğinde güçlü punch-in uygular.
            camera = seg["kamera"]
            seg_duration = max(0.1, seg["bit"] - seg["bas"])
            progress = min(1.0, yerel_t / seg_duration)
            zoom = 1.04 if seg["idx"] % 2 == 1 else 1.00
            sx, sy = 0, 0
            if camera == "zoomin":
                zoom = 1.0 + 0.12 * progress
            elif camera == "zoomout":
                zoom = 1.12 - 0.12 * progress
            elif camera == "shake":
                intensity = int(8 * (1.0 - progress))
                if intensity > 0:
                    sx = int(rng_shake.integers(-intensity, intensity + 1))
                    sy = int(rng_shake.integers(-intensity, intensity + 1))
            elif camera == "whippan":
                sx = int((1.0 - progress * 2.0) * 36)
            if seg["twist_mi"]:
                zoom = max(zoom, min(1.18, 1.06 + yerel_t * 0.45) if yerel_t < 0.28 else 1.16)
                if yerel_t < 0.26:
                    siddet = int((1.0 - yerel_t / 0.26) * 16)
                    if siddet > 1:
                        sx += int(rng_shake.integers(-siddet, siddet + 1))
                        sy += int(rng_shake.integers(-siddet, siddet + 1))

            if zoom > 1.005 or sx != 0 or sy != 0:
                kirp_g = int(W / zoom)
                kirp_y = int(H / zoom)
                sol = max(0, min(W - kirp_g, (W - kirp_g) // 2 + sx))
                ust = max(0, min(H - kirp_y, (H - kirp_y) // 2 + sy))
                son_rgb = son_rgb.crop((sol, ust, sol + kirp_g, ust + kirp_y)).resize((W, H), Image.BILINEAR)

            proc.stdin.write(son_rgb.tobytes())

        proc.stdin.flush()
        proc.stdin.close()
        proc.stdin = None
        _, stderr_bytes = proc.communicate(timeout=180)
        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg encode hatası: {stderr_bytes.decode(errors='ignore')[-400:]}")
    except Exception:
        proc.kill()
        raise

    return str(cikis_video_mp4)


# Geriye dönük uyumluluk sarmalayıcıları
def basit_animasyon_uret(senaryo_paketi: dict) -> str:
    cikti = str(Path("bobi_tv/production/render") / f"{senaryo_paketi['dosya_adi']}_anim.mp4")
    return pro_sahne_videosu_uret(senaryo_paketi, "", cikti)


def arena_animasyon_uret(senaryo_paketi: dict) -> str:
    return basit_animasyon_uret(senaryo_paketi)
