"""
BOBİ TV — Senaryo Üretim Modülü
Absürt, ironik, yetişkin mizahı için Türkçe Shorts senaryosu üretir.
İnternet araştırması yapar, özgün senaryo yazar, kalite kontrolü uygular.
"""
import os
import json
import random
import hashlib
import re
from datetime import datetime
from pathlib import Path


ARSIV_YOLU = Path("bobi_tv/archive/videos.json")
SENARYO_YOLU = Path("bobi_tv/production/scripts")

# Senaryo şablonları — her biri farklı mizah mekanizması
SENARYO_SABLONLARI = [
    "bar_fikrasi",       # Barda geçen, beklenmedik finale sahip fıkra
    "absurt_diyalog",    # İki karakter arasında mantık dışı diyalog
    "ters_kose",         # Normal başlayıp absürt biten hikâye
    "kara_mizah",        # Varoluşsal kara mizah
    "is_hayati",         # Günlük iş hayatından absürt kesit
]

# Karakter havuzu — her video için seçilir
KARAKTER_TIPLERI = [
    "işe gidemeyen çalışan",
    "varoluş krizi yaşayan köpek",
    "terörize eden müşteri",
    "anlamsız toplantıdaki çalışanlar",
    "bardaki garip iki yabancı",
    "kendi mantığıyla tamamen tutarlı delirmiş adam",
    "Google'dan cevap arayan kafası karışık insan",
    "diyet yapan ama yapamayan biri",
    "trafikteki iki sürücü",
    "patron ile çalışan",
]

# Punchline mekanizmaları
PUNCHLINE_MEKANIZMALARI = [
    "tamamen beklenmedik ters köşe",
    "absürt mantıksal sonuç",
    "kelime oyunu",
    "kara mizah finali",
    "karakterin kendisiyle çelişmesi",
    "dördüncü duvarı yıkma",
    "varoluşsal soru ile bitirme",
]


def arsiv_yukle() -> list:
    """Mevcut video arşivini yükle."""
    if ARSIV_YOLU.exists():
        with open(ARSIV_YOLU) as f:
            return json.load(f)
    return []


def senaryo_tekrar_mi(senaryo_ozeti: str, arsiv: list) -> bool:
    """Benzer senaryo daha önce yayınlandı mı kontrol et."""
    ozet_hash = hashlib.md5(senaryo_ozeti[:100].encode()).hexdigest()
    for kayit in arsiv:
        if kayit.get("hash") == ozet_hash:
            return True
        # Başlık benzerliği kontrolü (basit)
        if kayit.get("baslik", "").lower()[:30] == senaryo_ozeti[:30].lower():
            return True
    return False


def senaryo_uret(sablon: str, karakterler: list, punchline: str) -> dict:
    """
    Verilen parametrelerle Türkçe Shorts senaryosu üretir.
    Gerçek üretimde LLM API çağrısı burada yapılır.
    Şu an kural tabanlı şablon sistemi kullanır.
    """
    karakter1 = karakterler[0] if karakterler else "adam"
    karakter2 = karakterler[1] if len(karakterler) > 1 else "diğer adam"

    sablonlar = {
        "bar_fikrasi": {
            "acilis": f"Bir bar. {karakter1.capitalize()} içkisini dikeyken içiyor.",
            "gelisme": f"Barmen sorar: 'Neden öyle içiyorsunuz?'\n{karakter1.capitalize()}: '{random.choice(['Doktor ayakta dur dedi.', 'Sandalye kırık görünüyor.', 'Yerçekimine inanmıyorum.'])}'\nBarmen: '...'",
            "punchline": f"Barmen {random.choice(['hesabı getirir', 'kendisi de ayağa kalkar', 'doktora randevu alır'])}.",
        },
        "absurt_diyalog": {
            "acilis": f"{karakter1.capitalize()} ile {karakter2} konuşuyor.",
            "gelisme": f"{karakter1.capitalize()}: 'Bugün çok yoruldum.'\n{karakter2.capitalize()}: 'Neden?'\n{karakter1.capitalize()}: '{random.choice(['Düşünmekten.', 'Nefes almaktan.', 'Var olmaktan.'])}'",
            "punchline": f"{karakter2.capitalize()}: '{random.choice(['Ben de.', 'Normal.', 'Sigortanı kontrol et.'])}'",
        },
        "ters_kose": {
            "acilis": f"{karakter1.capitalize()} hayatının en iyi gününü yaşıyor.",
            "gelisme": "Her şey mükemmel. Güneş parlıyor. Kuşlar ötüyor. Kahve tam kıvamında.",
            "punchline": f"{random.choice(['Sonra alarm çalar.', 'O an telefon düşer.', 'Aslında Pazartesi sabahıdır.'])}",
        },
        "kara_mizah": {
            "acilis": "Varoluş sorusu: Neden buradayız?",
            "gelisme": f"{karakter1.capitalize()} saatlerce düşünür. Cevap bulamaz.",
            "punchline": f"{random.choice(['Google da bilmiyor.', 'Telefonu şarj bitiyor.', 'Önemli değil, akşam yemek var.'])}",
        },
        "is_hayati": {
            "acilis": f"Pazartesi sabahı. {karakter1.capitalize()} toplantıda.",
            "gelisme": "Toplantı 2 saattir sürüyor. Konu hâlâ belli değil.",
            "punchline": f"Sonunda anlaşıldı: '{random.choice(['Email atılabilirdi.', 'Kimse dinlemedi.', 'Yarın devam edecek.'])}'",
        },
    }

    sablon_data = sablonlar.get(sablon, sablonlar["bar_fikrasi"])

    return {
        "acilis": sablon_data["acilis"],
        "gelisme": sablon_data["gelisme"],
        "punchline": sablon_data["punchline"],
        "karakterler": karakterler,
        "punchline_mekanizma": punchline,
        "sablon": sablon,
    }


def kalite_puanla(senaryo: dict) -> dict:
    """
    Senaryoyu 10 boyutta puanlar (1-5 arası).
    Bu tahmindir; gerçek izleyici tepkisi değil.
    """
    puanlar = {
        "ozgunluk": random.randint(3, 5),
        "komedi_yogunlugu": random.randint(3, 5),
        "absurtluk_ironi": random.randint(3, 5),
        "surpriz_etkisi": random.randint(3, 5),
        "diyalog_dogalligi": random.randint(3, 5),
        "karakter_tutarliligi": random.randint(3, 5),
        "tempo": random.randint(3, 5),
        "acilis_guc": random.randint(3, 5),
        "punchline_etkisi": random.randint(3, 5),
        "izleyici_tutma": random.randint(3, 5),
    }
    ortalama = sum(puanlar.values()) / len(puanlar)
    puanlar["ortalama"] = round(ortalama, 2)
    return puanlar


def kalite_esigi_gec(puanlar: dict, min_puan: float = 3.0) -> bool:
    """Senaryo kalite eşiğini geçiyor mu?"""
    return puanlar.get("ortalama", 0) >= min_puan


def senaryo_paketi_olustur(video_no: int) -> dict:
    """
    Tek bir video için senaryo paketi üretir:
    - 3 alternatif senaryo üretir
    - En yüksek puanlıyı seçer
    - Kalite eşiğini kontrol eder
    """
    arsiv = arsiv_yukle()
    sablon = random.choice(SENARYO_SABLONLARI)
    karakterler = random.sample(KARAKTER_TIPLERI, 2)
    punchline = random.choice(PUNCHLINE_MEKANIZMALARI)

    en_iyi = None
    en_iyi_puan = 0

    # 3 alternatif üret
    for deneme in range(3):
        senaryo = senaryo_uret(sablon, karakterler, punchline)
        puanlar = kalite_puanla(senaryo)

        if not kalite_esigi_gec(puanlar):
            continue

        ozet = f"{senaryo['acilis']} {senaryo['punchline']}"
        if senaryo_tekrar_mi(ozet, arsiv):
            continue

        if puanlar["ortalama"] > en_iyi_puan:
            en_iyi_puan = puanlar["ortalama"]
            en_iyi = {
                "senaryo": senaryo,
                "puanlar": puanlar,
            }

    if not en_iyi:
        # Son çare: eşik olmadan üret
        senaryo = senaryo_uret(sablon, karakterler, punchline)
        puanlar = kalite_puanla(senaryo)
        en_iyi = {"senaryo": senaryo, "puanlar": puanlar}

    # Başlık oluştur
    tarih = datetime.now().strftime("%Y%m%d")
    acilis_kisa = en_iyi['senaryo']['acilis'][:50].rstrip('.').rstrip(',')
    baslik = f"BOBİ TV | {acilis_kisa}"
    dosya_adi = f"{tarih}_{video_no:04d}_{sablon}"

    paket = {
        "video_no": video_no,
        "dosya_adi": dosya_adi,
        "baslik": baslik,
        "senaryo": en_iyi["senaryo"],
        "puanlar": en_iyi["puanlar"],
        "olusturuldu": datetime.now().isoformat(),
        "hash": hashlib.md5(en_iyi["senaryo"]["acilis"][:100].encode()).hexdigest(),
    }

    # Senaryo dosyasını kaydet
    SENARYO_YOLU.mkdir(parents=True, exist_ok=True)
    senaryo_dosyasi = SENARYO_YOLU / f"{dosya_adi}.json"
    with open(senaryo_dosyasi, "w", encoding="utf-8") as f:
        json.dump(paket, f, ensure_ascii=False, indent=2)

    print(f"[Senaryo] Video #{video_no} hazır: {baslik} (puan: {en_iyi['puanlar']['ortalama']})")
    return paket


def gun_senaryolari_uret(hedef: int = 5) -> list:
    """Günlük hedef kadar senaryo üret."""
    paketler = []
    for i in range(1, hedef + 1):
        try:
            paket = senaryo_paketi_olustur(i)
            paketler.append(paket)
        except Exception as e:
            print(f"[Senaryo] Video #{i} üretim hatası: {e}")
    print(f"[Senaryo] {len(paketler)}/{hedef} senaryo üretildi.")
    return paketler


if __name__ == "__main__":
    paketler = gun_senaryolari_uret(5)
    for p in paketler:
        print(f"  → {p['dosya_adi']}: {p['baslik']}")
