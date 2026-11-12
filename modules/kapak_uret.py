"""
BOBİ TV v6.2 PRO — Viral Stüdyo Kapak (Thumbnail) & 1. Kare Motoru
- 1080x1920 9:16 Dikey Sinematik "VS / Clash" Kompozisyonu
- Çift Karakter Vektör Portre Sahnesi (Sol vs Sağ + Merkez Şimşek Rozeti)
- 3D Ekstrüde (Extruded) Montserrat-ExtraBold Başlık + Türkçe Büyük Harf (i -> İ, ı -> I)
- Merak Boşluğu (Curiosity Gap) Konuşma Balonu + "SONUNU İZLE!" Damgası
- Videonun 1. Karesine (Frame 0) Gömme ve İlk Kareden Kapak Seçme Desteği
"""

import math
import os
import re
import subprocess
from pathlib import Path

from modules import calisma_dizinleri

from PIL import Image, ImageDraw, ImageFont


GENISLIK = 1080
YUKSEKLIK = 1920

FONT_DIZINI = Path(__file__).resolve().parent.parent / "bobi_tv" / "assets" / "fonts"

KATEGORI_ETIKETLERI = {
    "kurumsal_hayat": "KURUMSAL HAYAT",
    "ik_toplantisi": "İK TOPLANTISI",
    "evlilik_sohbeti": "EVLİLİK SOHBETİ",
    "komsu_kavgasi": "APARTMAN KRİZİ",
    "doktor_hasta": "DOKTOR & HASTA",
    "musteri_hizmetleri": "MÜŞTERİ HİZMETLERİ",
    "yazilimci_hayati": "YAZILIMCI HAYATI",
    "kahve_hayati": "MODERN HAYAT",
    "aile_sofrasi": "AİLE SOFRASI",
}


def tr_upper(metin: str) -> str:
    """Türkçe karakter kurallarına tam uyumlu büyük harf dönüşümü (i -> İ, ı -> I)."""
    if not metin:
        return ""
    return (
        str(metin)
        .replace("i", "İ")
        .replace("ı", "I")
        .replace("ğ", "Ğ")
        .replace("ü", "Ü")
        .replace("ş", "Ş")
        .replace("ö", "Ö")
        .replace("ç", "Ç")
        .upper()
    )


def emoji_temizle(metin: str) -> str:
    if not metin:
        return ""
    temiz = re.sub(
        r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF\uFE0F\u200D]+",
        "",
        str(metin),
    )
    return re.sub(r"\s+", " ", temiz).strip()


def _font_getir(boyut: int, kalin: bool = True) -> ImageFont.FreeTypeFont:
    adaylar = [
        FONT_DIZINI / ("Montserrat-ExtraBold.ttf" if kalin else "Montserrat-Bold.ttf"),
        FONT_DIZINI / "Montserrat-ExtraBold.ttf",
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ]
    for p in adaylar:
        if p.exists():
            try:
                return ImageFont.truetype(str(p), boyut)
            except Exception:
                continue
    return ImageFont.load_default()


def _metin_sar(cizim: ImageDraw.ImageDraw, metin: str, font, maks_genislik: int, maks_satir: int = 3) -> list:
    kelimeler = metin.split()
    if not kelimeler:
        return ["ŞOK OLAY!"]
    satirlar = []
    aktif = kelimeler[0]
    for k in kelimeler[1:]:
        aday = f"{aktif} {k}"
        kutu = cizim.textbbox((0, 0), aday, font=font)
        if (kutu[2] - kutu[0]) <= maks_genislik:
            aktif = aday
        else:
            satirlar.append(aktif)
            aktif = k
    satirlar.append(aktif)
    if len(satirlar) > maks_satir:
        satirlar = satirlar[:maks_satir]
        if not satirlar[-1].endswith("!"):
            satirlar[-1] = satirlar[-1].rstrip(".") + "!"
    return satirlar


def _3d_metin_ciz(
    cizim: ImageDraw.ImageDraw,
    xy: tuple,
    metin: str,
    font,
    dolgu: tuple,
    kontur_renk: tuple = (0, 0, 0, 255),
    kontur_kalinlik: int = 10,
    derinlik: int = 9,
    golge_renk: tuple = (0, 0, 0, 235),
    anchor: str = "mm",
):
    """MrBeast / Viral Shorts tarzı 3D ekstrüde blok gölgeli ve kalın konturlu metin çizer."""
    x, y = xy
    for d in range(derinlik, 0, -1):
        cizim.text(
            (x + d, y + d + 2),
            metin,
            font=font,
            fill=golge_renk,
            stroke_width=kontur_kalinlik,
            stroke_fill=golge_renk,
            anchor=anchor,
        )
    cizim.text(
        (x, y),
        metin,
        font=font,
        fill=dolgu,
        stroke_width=kontur_kalinlik,
        stroke_fill=kontur_renk,
        anchor=anchor,
    )


def _sinematik_vs_arkaplan(W: int = GENISLIK, H: int = YUKSEKLIK) -> Image.Image:
    """
    Sol tarafı elektrik kırmızı/bordo, sağ tarafı siber mavi/mor çatışma (VS) atmosferli,
    merkez spot ışıklı ve çizgi roman hız çizgili 1080x1920 stüdyo arka planı üretir.
    """
    import numpy as np

    y_ind, x_ind = np.mgrid[0:H, 0:W].astype(np.float32)
    nx = x_ind / float(W)
    ny = y_ind / float(H)

    # Diyagonal ayrım çizgisi (sol vs sağ)
    ayrim = nx + (ny - 0.5) * 0.18
    sag_maske = np.clip((ayrim - 0.46) / 0.08, 0.0, 1.0)
    sol_maske = 1.0 - sag_maske

    # Sol: Koyu Bordo / Kızıl Enerji | Sağ: Derin Gece Mavisi / Siber Mor
    sol_r = 38.0 + 135.0 * np.exp(-((nx - 0.22) ** 2 / 0.12 + (ny - 0.46) ** 2 / 0.16))
    sol_g = 8.0 + 18.0 * (1.0 - ny)
    sol_b = 24.0 + 45.0 * np.exp(-((nx - 0.22) ** 2 / 0.15 + (ny - 0.46) ** 2 / 0.18))

    sag_r = 12.0 + 28.0 * np.exp(-((nx - 0.78) ** 2 / 0.15 + (ny - 0.46) ** 2 / 0.18))
    sag_g = 22.0 + 95.0 * np.exp(-((nx - 0.78) ** 2 / 0.12 + (ny - 0.46) ** 2 / 0.16))
    sag_b = 52.0 + 155.0 * np.exp(-((nx - 0.78) ** 2 / 0.13 + (ny - 0.46) ** 2 / 0.16))

    # Merkez altın patlama spotu
    merkez_spot = np.exp(-((nx - 0.5) ** 2 / 0.09 + (ny - 0.45) ** 2 / 0.11))

    r = sol_r * sol_maske + sag_r * sag_maske + merkez_spot * 65.0
    g = sol_g * sol_maske + sag_g * sag_maske + merkez_spot * 45.0
    b = sol_b * sol_maske + sag_b * sag_maske + merkez_spot * 15.0

    # Kenar vinyet (vignette)
    vinyet = 1.0 - 0.42 * (((nx - 0.5) * 1.35) ** 2 + ((ny - 0.48) * 1.25) ** 2)
    vinyet = np.clip(vinyet, 0.45, 1.0)

    rgb = np.stack([
        np.clip(r * vinyet, 0, 255),
        np.clip(g * vinyet, 0, 255),
        np.clip(b * vinyet, 0, 255),
    ], axis=-1).astype(np.uint8)

    img = Image.fromarray(rgb, mode="RGB").convert("RGBA")
    cizim = ImageDraw.Draw(img, "RGBA")

    # Merkez से dışa doğru radyal aksiyon ışınları (comic speed lines)
    mx, my = W // 2, int(H * 0.46)
    for aci_derece in range(0, 360, 12):
        rad = math.radians(aci_derece)
        x1 = mx + int(math.cos(rad) * 180)
        y1 = my + int(math.sin(rad) * 180)
        x2 = mx + int(math.cos(rad) * 1100)
        y2 = my + int(math.sin(rad) * 1100)
        cizim.line([(x1, y1), (x2, y2)], fill=(255, 255, 255, 11), width=3)

    # Üst ve alt sarı-siyah stüdyo şeritleri
    serit_y = 22
    for x in range(-40, W + 40, 56):
        cizim.polygon([(x, 0), (x + 28, 0), (x + 12, serit_y), (x - 16, serit_y)], fill=(255, 214, 10, 220))
        cizim.polygon([(x, H - serit_y), (x + 28, H - serit_y), (x + 12, H), (x - 16, H)], fill=(255, 214, 10, 220))

    return img


def _detayli_karakter_portresi_ciz(
    rol_adi: str,
    taraf: str,
    ifade: str = "sok",
    kart_g: int = 445,
    kart_y: int = 510,
) -> Image.Image:
    """
    Kapak için yüksek detaylı, ifadeli 2D vektör karakter portre kartı üretir.
    taraf: 'sol' (kırmızı/altın çerçeve, patron/erkek profili) veya 'sag' (turkuaz/mor çerçeve, İK/kadın profili)
    """
    img = Image.new("RGBA", (kart_g + 24, kart_y + 24), (0, 0, 0, 0))
    cizim = ImageDraw.Draw(img, "RGBA")

    ana_renk = (255, 42, 84, 255) if taraf == "sol" else (0, 245, 212, 255)
    arka_ust = (48, 14, 28, 250) if taraf == "sol" else (12, 36, 54, 250)

    # 3D Gölge
    cizim.rounded_rectangle([16, 18, kart_g + 16, kart_y + 18], radius=42, fill=(0, 0, 0, 210))
    # Ana Portre Kartı
    cizim.rounded_rectangle(
        [8, 8, kart_g + 8, kart_y + 8],
        radius=42,
        fill=arka_ust,
        outline=ana_renk,
        width=7,
    )

    # İç parlama halkası
    cx = 8 + kart_g // 2
    cy = 8 + int(kart_y * 0.46)
    cizim.ellipse([cx - 155, cy - 155, cx + 155, cy + 155], fill=(255, 255, 255, 18), outline=(255, 255, 255, 40), width=3)

    rol_u = tr_upper(rol_adi)
    kadin_mi = any(k in rol_u for k in ["İK", "KADIN", "ANNE", "GELİN", "SEVGİLİ", "EŞ", "PELİN", "ECE", "MÜŞTERİ"])
    if taraf == "sag" and not any(k in rol_u for k in ["BABA", "PATRON", "MÜDÜR", "DAMAT", "ERKEK"]):
        kadin_mi = True

    # Gövde / Omuzlar (Takım elbise veya şık ceket)
    omuz_renk = (28, 37, 54, 255) if not kadin_mi else (124, 32, 88, 255)
    cizim.pieslice([cx - 155, cy + 55, cx + 155, cy + 295], start=180, end=360, fill=omuz_renk, outline=(0, 0, 0, 255), width=5)

    # Gömlek & Kravat / Yaka detayı
    cizim.polygon([(cx - 38, cy + 68), (cx + 38, cy + 68), (cx, cy + 155)], fill=(248, 250, 252, 255))
    if not kadin_mi:
        cizim.polygon([(cx - 12, cy + 82), (cx + 12, cy + 82), (cx + 18, cy + 162), (cx, cy + 180), (cx - 18, cy + 162)], fill=(239, 68, 68, 255))
    else:
        cizim.ellipse([cx - 24, cy + 82, cx + 24, cy + 112], fill=(255, 214, 10, 255))

    # Uzun saç arka katmanı (kadın karakter için)
    sac_renk = (35, 24, 20, 255) if not kadin_mi else (72, 28, 18, 255)
    if kadin_mi:
        cizim.rounded_rectangle([cx - 118, cy - 115, cx + 118, cy + 95], radius=55, fill=sac_renk, outline=(0, 0, 0, 255), width=5)

    # Kulaklar
    ten_renk = (255, 214, 176, 255)
    cizim.ellipse([cx - 108, cy - 28, cx - 78, cy + 18], fill=ten_renk, outline=(0, 0, 0, 255), width=4)
    cizim.ellipse([cx + 78, cy - 28, cx + 108, cy + 18], fill=ten_renk, outline=(0, 0, 0, 255), width=4)

    # Baş / Yüz
    cizim.rounded_rectangle([cx - 92, cy - 110, cx + 92, cy + 78], radius=76, fill=ten_renk, outline=(0, 0, 0, 255), width=5)

    # Yanak kızarıklığı / Kontur
    cizim.ellipse([cx - 72, cy + 2, cx - 38, cy + 24], fill=(255, 125, 125, 110))
    cizim.ellipse([cx + 38, cy + 2, cx + 72, cy + 24], fill=(255, 125, 125, 110))

    # Saç Üst Katmanı
    if not kadin_mi:
        cizim.pieslice([cx - 98, cy - 132, cx + 98, cy - 15], start=180, end=360, fill=sac_renk, outline=(0, 0, 0, 255), width=5)
        cizim.polygon([(cx - 65, cy - 115), (cx - 20, cy - 142), (cx + 35, cy - 118)], fill=sac_renk)
    else:
        cizim.pieslice([cx - 98, cy - 130, cx + 98, cy - 20], start=180, end=360, fill=sac_renk, outline=(0, 0, 0, 255), width=5)

    # Gözler (İri, parlak, ifadeli)
    for gx in (cx - 40, cx + 40):
        cizim.ellipse([gx - 24, cy - 38, gx + 24, cy + 6], fill=(255, 255, 255, 255), outline=(0, 0, 0, 255), width=4)
        bebek_dx = 4 if taraf == "sol" else -4
        cizim.ellipse([gx - 11 + bebek_dx, cy - 25, gx + 11 + bebek_dx, cy - 3], fill=(20, 24, 38, 255))
        cizim.ellipse([gx - 6 + bebek_dx, cy - 22, gx + 1 + bebek_dx, cy - 15], fill=(255, 255, 255, 255))

    # Kaşlar (Sol karakter kızgın/şok, sağ karakter kurnaz/şaşkın)
    if taraf == "sol":
        cizim.line([(cx - 66, cy - 58), (cx - 16, cy - 42)], fill=(0, 0, 0, 255), width=9)
        cizim.line([(cx + 16, cy - 42), (cx + 66, cy - 58)], fill=(0, 0, 0, 255), width=9)
    else:
        cizim.line([(cx - 64, cy - 50), (cx - 18, cy - 56)], fill=(0, 0, 0, 255), width=8)
        cizim.line([(cx + 18, cy - 64), (cx + 64, cy - 50)], fill=(0, 0, 0, 255), width=8)

    # Ağız (Şok / Kahkaha açık ağız + diş + dil)
    if taraf == "sol":
        # Şok / Bağırış ağzı
        cizim.rounded_rectangle([cx - 34, cy + 18, cx + 34, cy + 58], radius=18, fill=(140, 18, 35, 255), outline=(0, 0, 0, 255), width=4)
        cizim.rectangle([cx - 24, cy + 20, cx + 24, cy + 31], fill=(255, 255, 255, 255))
        cizim.pieslice([cx - 20, cy + 36, cx + 20, cy + 58], start=180, end=360, fill=(255, 105, 135, 255))
    else:
        # Kurnaz / Şaşkın geniş gülüş
        cizim.pieslice([cx - 38, cy + 8, cx + 38, cy + 56], start=0, end=180, fill=(160, 20, 45, 255), outline=(0, 0, 0, 255), width=4)
        cizim.rectangle([cx - 28, cy + 28, cx + 28, cy + 38], fill=(255, 255, 255, 255))

    # Köşe Reaksiyon Rozeti (! veya ?)
    rozet_x = kart_g - 52 if taraf == "sol" else 64
    rozet_y = 62
    cizim.ellipse([rozet_x - 36, rozet_y - 36, rozet_x + 36, rozet_y + 36], fill=(255, 214, 10, 255), outline=(0, 0, 0, 255), width=5)
    f_rozet = _font_getir(44, kalin=True)
    cizim.text((rozet_x, rozet_y), "!" if taraf == "sol" else "?", font=f_rozet, fill=(0, 0, 0, 255), anchor="mm")

    # Alt Karakter İsim Plakası
    plaka_y1 = kart_y - 68
    plaka_y2 = kart_y - 4
    cizim.rounded_rectangle(
        [34, plaka_y1, kart_g - 18, plaka_y2],
        radius=22,
        fill=ana_renk,
        outline=(0, 0, 0, 255),
        width=5,
    )
    f_isim = _font_getir(34, kalin=True)
    kisa_rol = rol_u[:14]
    metin_renk = (255, 255, 255, 255) if taraf == "sol" else (10, 18, 30, 255)
    cizim.text(
        (8 + kart_g // 2, (plaka_y1 + plaka_y2) // 2),
        kisa_rol,
        font=f_isim,
        fill=metin_renk,
        stroke_width=4 if taraf == "sol" else 0,
        stroke_fill=(0, 0, 0, 255),
        anchor="mm",
    )

    return img


def _merkez_vs_simsek_rozeti() -> Image.Image:
    """İki karakterin tam ortasına yerleşen 3D altın/kırmızı VS çarpışma rozeti."""
    boyut = 156
    img = Image.new("RGBA", (boyut, boyut), (0, 0, 0, 0))
    cizim = ImageDraw.Draw(img, "RGBA")
    m = boyut // 2

    # Dış parlama ve siyah konturlu altın daire
    cizim.ellipse([8, 12, boyut - 4, boyut], fill=(0, 0, 0, 220))
    cizim.ellipse([6, 6, boyut - 6, boyut - 6], fill=(255, 42, 84, 255), outline=(255, 214, 10, 255), width=8)
    cizim.ellipse([20, 20, boyut - 20, boyut - 20], fill=(18, 22, 36, 255), outline=(0, 0, 0, 255), width=4)

    f_vs = _font_getir(54, kalin=True)
    _3d_metin_ciz(
        cizim,
        (m, m),
        "VS",
        f_vs,
        dolgu=(255, 214, 10, 255),
        kontur_renk=(0, 0, 0, 255),
        kontur_kalinlik=7,
        derinlik=5,
    )
    return img


def _bilgi_arkaplan(senaryo: dict) -> Image.Image:
    """Kategoriye göre dikey gradyan + yumuşak ışık huzmeleri (VS çizgileri yok).

    Neden: kullanıcı "her video farklı görünsün" diyor; kategori renk paleti
    (`ilginc_bilgi/kategoriler.py`) sekiz farklı görünümün temelini verir.
    """
    from modules.ilginc_bilgi.kategoriler import kategori_al

    ana_hex, orta_hex, acik_hex = kategori_al(str(senaryo.get("kategori") or ""))["renk"]
    ana = acik_rgb(ana_hex)
    orta = acik_rgb(orta_hex)
    koyu = _karart(ana, 0.35)

    tuval = Image.new("RGBA", (GENISLIK, YUKSEKLIK), (*koyu, 255))
    gradyan = Image.new("RGBA", (1, YUKSEKLIK))
    g_ciz = ImageDraw.Draw(gradyan)
    for y in range(YUKSEKLIK):
        t = y / max(1, YUKSEKLIK - 1)
        # üstte koyu → ortada kategori rengi → altta koyu
        if t < 0.55:
            k = t / 0.55
            renk = tuple(int(koyu[i] + (orta[i] - koyu[i]) * k * 0.75) for i in range(3))
        else:
            k = (t - 0.55) / 0.45
            renk = tuple(int(orta[i] * 0.75 + (koyu[i] - orta[i] * 0.75) * k) for i in range(3))
        g_ciz.point((0, y), fill=(*renk, 255))
    tuval = gradyan.resize((GENISLIK, YUKSEKLIK), Image.BILINEAR).convert("RGBA")

    # Yumuşak ışık huzmeleri (diyagonal, düşük alfa)
    huzme = Image.new("RGBA", (GENISLIK, YUKSEKLIK), (0, 0, 0, 0))
    h_ciz = ImageDraw.Draw(huzme, "RGBA")
    for i in range(-2, 8):
        x = i * 190
        h_ciz.polygon(
            [(x, 0), (x + 120, 0), (x + 420, YUKSEKLIK), (x + 300, YUKSEKLIK)],
            fill=(255, 255, 255, 8),
        )
    tuval.alpha_composite(huzme)

    # Hafif vinyet (kenarları karart)
    vinyet = Image.new("L", (GENISLIK, YUKSEKLIK), 0)
    v_ciz = ImageDraw.Draw(vinyet)
    for r in range(1200, 300, -40):
        v_ciz.ellipse(
            [GENISLIK // 2 - r, YUKSEKLIK // 2 - int(r * 1.5),
             GENISLIK // 2 + r, YUKSEKLIK // 2 + int(r * 1.5)],
            fill=min(255, 60 + (1200 - r) // 6),
        )
    karartma = Image.new("RGBA", (GENISLIK, YUKSEKLIK), (*_karart(ana, 0.2), 120))
    tuval = Image.composite(tuval, Image.alpha_composite(tuval, karartma), vinyet)
    return tuval


def _bilgi_rozeti_ekle(tuval, cizim, senaryo: dict) -> None:
    """İlginç bilgi kapağı: dev kategori emojisi + merkez 'BİLİYOR MUYDUN?' rozeti.

    Neden: VS düellosu kaldırıldı (kullanıcı talimatı); tek anlatıcılı bilgi
    formatında kapağın işi merak uyandırmak, karakter çatışması değil.
    """
    try:
        from modules.ilginc_bilgi.kategoriler import kategori_al

        kat = kategori_al(str(senaryo.get("kategori") or ""))
        ana, orta, acik = kat["renk"]
        ana_rgb = tuple(int(ana.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
        orta_rgb = tuple(int(orta.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))

        # Yumuşak radyal hale (kategori rengine göre)
        hale = Image.new("RGBA", (GENISLIK, 620), (0, 0, 0, 0))
        h_ciz = ImageDraw.Draw(hale, "RGBA")
        for r in range(300, 40, -12):
            alfa = int(6 + (300 - r) * 0.30)
            h_ciz.ellipse(
                [GENISLIK // 2 - r, 310 - r, GENISLIK // 2 + r, 310 + r],
                fill=(*orta_rgb, min(alfa, 90)),
            )
        tuval.alpha_composite(hale, (0, 500))

        # Merkez görsel: renkli emoji fontu sunucuda yok (tofu kutusu çıkıyor),
        # bu yüzden vektörel "bilgi halkası" + kategori adı çizilir.
        merkez_y = 790
        for k in range(3):
            r = 200 - k * 46
            cizim.ellipse(
                [GENISLIK // 2 - r, merkez_y - r, GENISLIK // 2 + r, merkez_y + r],
                outline=(*acik_rgb(acik), 90 - k * 25), width=10 - k * 2,
            )
        f_soru = _font_getir(96, kalin=True)
        cizim.text((GENISLIK // 2, merkez_y), "?", font=f_soru,
                   fill=(255, 255, 255, 250), anchor="mm",
                   stroke_width=7, stroke_fill=(0, 0, 0, 255))
        # Kategori adı üstteki rozette zaten var (BOBİ TV • HAYVANLAR);
        # burada tekrar yazmak kalabalık yapıyordu — kaldırıldı.

        # Merkez rozet: "BİLİYOR MUYDUN?"
        f_rozet = _font_getir(46, kalin=True)
        yazi = "BİLİYOR MUYDUN?"
        kutu = cizim.textbbox((0, 0), yazi, font=f_rozet)
        g = (kutu[2] - kutu[0]) + 96
        x1 = (GENISLIK - g) // 2
        cizim.rounded_rectangle(
            [x1, 960, x1 + g, 1060], radius=50,
            fill=(*_karart(ana_rgb, 0.55), 245), outline=(*acik_rgb(acik), 255), width=6,
        )
        cizim.text((GENISLIK // 2, 1010), yazi, font=f_rozet,
                   fill=(255, 255, 255, 255), anchor="mm")
    except Exception as e:
        print(f"[Kapak] Bilgi rozeti eklenemedi: {str(e)[:100]}")


def _karart(rgb: tuple[int, int, int], oran: float) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(c * oran))) for c in rgb)


def acik_rgb(hex_renk: str) -> tuple[int, int, int]:
    h = hex_renk.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def kapak_resmi_olustur(senaryo_paketi: dict, cikis_jpg: str) -> str:
    """
    Viral tıklanma oranı (CTR) odaklı 1080x1920 profesyonel kapak üretir:
    1. Üstte 3D Ekstrüde Dev Kanca Başlık Banner'ı (Sarı + Beyaz + Kırmızı Vurgulu)
    2. Ortada Sol vs Sağ İfadeli Karakter Portreleri + VS Rozeti
    3. Altta Merak Uyandıran Konuşma Balonu + "SONUNU İZLE!" Damgası
    """
    senaryo = senaryo_paketi.get("senaryo", {})
    diyaloglar = senaryo.get("diyaloglar", [])
    ham_kat = emoji_temizle(senaryo.get("kategori", "kurumsal_hayat")).strip().lower()
    kategori = KATEGORI_ETIKETLERI.get(ham_kat, tr_upper(ham_kat.replace("_", " ")))

    # Kanca başlığı seç (kapak_metni -> hook_cümlesi -> baslik)
    ham_kanca = (
        senaryo.get("kapak_baslik")
        or senaryo.get("kapak_metni")
        or senaryo.get("soru")
        or senaryo.get("hook_cumlesi")
        or senaryo.get("baslik", "").replace("#shorts", "")
        or "BU OLAYIN SONU ŞOK ETTİ!"
    )
    kanca_ust = tr_upper(emoji_temizle(ham_kanca))
    # Başlık 40 karakteri aşarsa TAM KELİME sınırında kırp (kelime ortasından
    # kesmek amatör görünüyor: "... BİRİ Y!" gibi).
    if len(kanca_ust) > 40:
        parcalar = kanca_ust.split()
        kisa = ""
        for parca in parcalar:
            aday = (kisa + " " + parca).strip()
            if len(aday) > 38:
                break
            kisa = aday
        kanca_ust = (kisa or parcalar[0]) + "…"
    if not kanca_ust.endswith(("!", "?")):
        kanca_ust += "!"

    # İki ana karakteri belirle
    karakterler = []
    for d in diyaloglar:
        k_adi = tr_upper(emoji_temizle(d.get("karakter", "KARAKTER")))
        if k_adi and k_adi not in karakterler:
            karakterler.append(k_adi)
    sol_rol = karakterler[0] if len(karakterler) >= 1 else "MÜDÜR"
    sag_rol = karakterler[1] if len(karakterler) >= 2 else "İK UZMANI"

    # Merak uyandıran alıntı (Twist öncesi veya 2. replik)
    alinti_ham = ""
    if str(senaryo.get("semaversiyonu", "")).startswith("8.0"):
        # Bilgi formatında balonda SORU görünür (merak boşluğu); cevabı
        # kapağa yazmak tıklama vaadini öldürüyordu.
        alinti_ham = emoji_temizle(str(senaryo.get("soru") or senaryo.get("hook_metni") or ""))
    if not alinti_ham and len(diyaloglar) >= 2:
        alinti_ham = emoji_temizle(diyaloglar[1].get("metin", ""))
    elif not alinti_ham and diyaloglar:
        alinti_ham = emoji_temizle(diyaloglar[0].get("metin", ""))
    alinti_kelimeler = alinti_ham.split()
    if len(alinti_kelimeler) > 8:
        alinti_metin = " ".join(alinti_kelimeler[:8]) + "..."
    else:
        alinti_metin = alinti_ham or "Bunu kimse beklemiyordu..."

    # 1. Arka plan: bilgi formatında sakin kategori gradyanı, eski formatta VS
    bilgi_formati_bg = str(senaryo.get("semaversiyonu", "")).startswith("8.0")
    if bilgi_formati_bg:
        tuval = _bilgi_arkaplan(senaryo)
    else:
        tuval = _sinematik_vs_arkaplan(GENISLIK, YUKSEKLIK)
    cizim = ImageDraw.Draw(tuval, "RGBA")

    # 2. Üst Kanal & Kategori Rozeti (y=58..130)
    f_ust = _font_getir(30, kalin=True)
    ust_etiket = f"BOBİ TV  •  {kategori}"
    kutu_u = cizim.textbbox((0, 0), ust_etiket, font=f_ust)
    rozet_g = (kutu_u[2] - kutu_u[0]) + 95
    rx1 = (GENISLIK - rozet_g) // 2
    cizim.rounded_rectangle(
        [rx1, 56, rx1 + rozet_g, 126],
        radius=35,
        fill=(12, 16, 28, 240),
        outline=(255, 214, 10, 255),
        width=4,
    )
    cizim.ellipse([rx1 + 24, 79, rx1 + 48, 103], fill=(255, 42, 84, 255))
    cizim.text((rx1 + 66, 91), ust_etiket, font=f_ust, fill=(255, 255, 255, 255), anchor="lm")

    # 3. Dev 3D Kanca Başlık Banner'ı (y=155..555)
    banner_g = 996
    banner_y = 390
    banner_img = Image.new("RGBA", (banner_g + 28, banner_y + 44), (0, 0, 0, 0))
    b_ciz = ImageDraw.Draw(banner_img, "RGBA")

    # Banner 3D sert gölge + Ana Kutu
    b_ciz.rounded_rectangle([18, 30, banner_g + 18, banner_y + 30], radius=38, fill=(0, 0, 0, 230))
    b_ciz.rounded_rectangle(
        [8, 18, banner_g + 8, banner_y + 18],
        radius=38,
        fill=(14, 18, 32, 250),
        outline=(255, 214, 10, 255),
        width=8,
    )

    # Üst Kırmızı "ŞOK OLAY" Şeridi
    b_ciz.rounded_rectangle(
        [banner_g // 2 - 210, 0, banner_g // 2 + 210, 56],
        radius=20,
        fill=(255, 42, 84, 255),
        outline=(0, 0, 0, 255),
        width=5,
    )
    f_sok = _font_getir(29, kalin=True)
    if str(senaryo.get("semaversiyonu", "")).startswith("8.0"):
        serit = "BUNU DUYUNCA ŞAŞIRACAKSIN!"
    else:
        serit = "YOK ARTIK DEDİRTEN OLAY!"
    b_ciz.text((banner_g // 2, 28), serit, font=f_sok, fill=(255, 255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0, 255), anchor="mm")

    # Başlık metnini otomatik boyutlandır (2 veya 3 satır)
    font_boyut = 78 if len(kanca_ust) <= 28 else (68 if len(kanca_ust) <= 40 else 58)
    f_kanca = _font_getir(font_boyut, kalin=True)
    satirlar = _metin_sar(b_ciz, kanca_ust, f_kanca, maks_genislik=banner_g - 76, maks_satir=3)

    satir_aralik = font_boyut + 20
    toplam_m_yuk = len(satirlar) * satir_aralik
    bas_y = 32 + (banner_y - toplam_m_yuk) // 2 + font_boyut // 2

    renk_paleti = [
        (255, 255, 255, 255),  # 1. satır Saf Beyaz
        (255, 214, 10, 255),   # 2. satır Neon Altın Sarı
        (0, 245, 212, 255),    # 3. satır Siber Turkuaz
    ]
    for idx, satir in enumerate(satirlar):
        y_konum = bas_y + idx * satir_aralik
        renk = renk_paleti[idx % len(renk_paleti)]
        _3d_metin_ciz(
            b_ciz,
            (8 + banner_g // 2, y_konum),
            satir,
            f_kanca,
            dolgu=renk,
            kontur_renk=(0, 0, 0, 255),
            kontur_kalinlik=10,
            derinlik=8,
        )

    banner_donuk = banner_img.rotate(1.4, resample=Image.BICUBIC, expand=True)
    tuval.alpha_composite(banner_donuk, ((GENISLIK - banner_donuk.width) // 2, 148))

    # 4. Karakter sahnesi — FORMAT DEVRİMİ (2026-11-11)
    # Yeni içerik hattı tek anlatıcılı bilgi formatı; "VS / çift karakter
    # düellosu" kullanıcı talimatıyla kaldırıldı. Bilgi formatında bunun
    # yerine dev kategori emojisi + merkez "BİLİYOR MUYDUN?" rozeti gelir.
    bilgi_formati = str(senaryo.get("semaversiyonu", "")).startswith("8.0")
    if bilgi_formati:
        _bilgi_rozeti_ekle(tuval, cizim, senaryo)
    else:
        sol_portre = _detayli_karakter_portresi_ciz(sol_rol, taraf="sol")
        sag_portre = _detayli_karakter_portresi_ciz(sag_rol, taraf="sag")
        tuval.alpha_composite(sol_portre, (42, 585))
        tuval.alpha_composite(sag_portre, (GENISLIK - sag_portre.width - 42, 585))
        vs_rozet = _merkez_vs_simsek_rozeti()
        tuval.alpha_composite(vs_rozet, ((GENISLIK - vs_rozet.width) // 2, 765))

    # 5. Merak Uyandıran Konuşma Balonu + "SONUNU İZLE!" Damgası (y=1145..1435)
    balon_x1, balon_y1 = 56, 1155
    balon_x2, balon_y2 = GENISLIK - 56, 1415

    # Balon gölgesi
    cizim.rounded_rectangle([balon_x1 + 12, balon_y1 + 14, balon_x2 + 12, balon_y2 + 14], radius=36, fill=(0, 0, 0, 215))
    # Balon ok ucu (yukarı, karakterlere doğru)
    cizim.polygon([(310, balon_y1), (360, balon_y1), (320, balon_y1 - 34)], fill=(255, 255, 255, 255), outline=(0, 0, 0, 255))
    # Ana Beyaz Konuşma Balonu
    cizim.rounded_rectangle(
        [balon_x1, balon_y1, balon_x2, balon_y2],
        radius=36,
        fill=(255, 255, 255, 255),
        outline=(0, 0, 0, 255),
        width=7,
    )

    f_alinti = _font_getir(42, kalin=True)
    alinti_satirlar = _metin_sar(cizim, f'"{alinti_metin}"', f_alinti, maks_genislik=880, maks_satir=2)
    ay_bas = balon_y1 + 58
    for s_i, a_satir in enumerate(alinti_satirlar):
        cizim.text(
            (GENISLIK // 2, ay_bas + s_i * 54),
            a_satir,
            font=f_alinti,
            fill=(15, 23, 42, 255),
            anchor="mm",
        )

    # Sağ alt "SONU ŞOK!" Damgası
    damga_x1, damga_y1 = GENISLIK - 410, balon_y2 - 42
    damga_x2, damga_y2 = GENISLIK - 78, balon_y2 + 32
    cizim.rounded_rectangle(
        [damga_x1, damga_y1, damga_x2, damga_y2],
        radius=22,
        fill=(255, 42, 84, 255),
        outline=(255, 214, 10, 255),
        width=5,
    )
    f_damga = _font_getir(33, kalin=True)
    _bilgi = str(senaryo.get("semaversiyonu", "")).startswith("8.0")
    cizim.text(
        ((damga_x1 + damga_x2) // 2, (damga_y1 + damga_y2) // 2),
        "CEVAP SONDA!" if _bilgi else "SONUNU BEKLE!",
        font=f_damga,
        fill=(255, 255, 255, 255),
        stroke_width=4,
        stroke_fill=(0, 0, 0, 255),
        anchor="mm",
    )

    # 6. Alt Güvenli Bölge (Safe-Zone) Etkileşim Çubuğu (y=1490..1580)
    cta_x1, cta_y1 = 150, 1495
    cta_x2, cta_y2 = GENISLIK - 150, 1575
    cizim.rounded_rectangle(
        [cta_x1, cta_y1, cta_x2, cta_y2],
        radius=40,
        fill=(255, 214, 10, 255),
        outline=(0, 0, 0, 255),
        width=6,
    )
    f_cta = _font_getir(34, kalin=True)
    _cta_metni = (
        "▶  SEN DE ŞAŞIRACAKSIN!"
        if str(senaryo.get("semaversiyonu", "")).startswith("8.0")
        else "▶  FİNALDEKİ CEVAP EFSANE!"
    )
    cizim.text(
        (GENISLIK // 2, (cta_y1 + cta_y2) // 2),
        _cta_metni,
        font=f_cta,
        fill=(10, 14, 24, 255),
        anchor="mm",
    )

    Path(cikis_jpg).parent.mkdir(parents=True, exist_ok=True)
    tuval.convert("RGB").save(cikis_jpg, "JPEG", quality=95, subsampling=0)
    return cikis_jpg


def videodan_ilk_kareyi_kapak_sec(video_yolu: str, cikis_jpg: str) -> str:
    """
    Videonun 1. karesine (Frame 0, t=0.0s) yerleştirilmiş profesyonel kapağı
    doğrudan MP4 akışının ilk karesinden seçip yüksek kaliteli JPEG olarak çıkarır.
    """
    Path(cikis_jpg).parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", str(video_yolu),
                "-vf", "select=eq(n\\,0)",
                "-frames:v", "1",
                "-q:v", "2",
                str(cikis_jpg),
            ],
            capture_output=True,
            check=True,
            timeout=20,
        )
        if os.path.exists(cikis_jpg) and os.path.getsize(cikis_jpg) > 10_000:
            return cikis_jpg
    except Exception as e:
        print(f"[Kapak] İlk kare çıkarma uyarısı: {e}")
    return cikis_jpg


def kapak_uret(paket_veya_yol, senaryo_paketi: dict = None) -> str:
    """
    Hem kapak_uret(paket) hem de kapak_uret(video_yolu, paket) çağrı imzasını destekler.
    1. Profesyonel 1080x1920 VS/Clash kapak görselini oluşturur.
    2. Video render edildiyse videonun 1. karesinden (Frame 0) seçilen kapağı çıkarıp doğrular.
    3. Pakete hem 'kapak_dosyasi' hem 'kapak_yolu' anahtarlarını yazar.
    """
    if isinstance(paket_veya_yol, dict):
        paket = paket_veya_yol
        dosya_adi = paket.get("dosya_adi", "video")
        video_yolu = paket.get("final_video") or str(calisma_dizinleri.OUTPUT_YOLU / f"{dosya_adi}.mp4")
    else:
        video_yolu = str(paket_veya_yol)
        paket = senaryo_paketi if isinstance(senaryo_paketi, dict) else {}

    cikis_jpg = str(video_yolu).replace(".mp4", "_thumb.jpg")
    if not os.path.exists(cikis_jpg):
        kapak_resmi_olustur(paket, cikis_jpg)

    if os.path.exists(video_yolu) and os.path.getsize(video_yolu) > 25_000:
        videodan_ilk_kareyi_kapak_sec(video_yolu, cikis_jpg)

    paket["kapak_dosyasi"] = cikis_jpg
    paket["kapak_yolu"] = cikis_jpg
    print(f"[Kapak] ✅ Profesyonel 1. Kare Kapak Seçildi: {Path(cikis_jpg).name}")
    return cikis_jpg


if __name__ == "__main__":
    print("BOBİ TV kapak_uret.py v6.2 PRO hazır.")
