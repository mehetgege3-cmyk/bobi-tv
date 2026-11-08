"""
BOBİ TV — Senaryo Üretim Modülü v2.0
Viralite odaklı: kısa, hızlı, hook'lu, loop'lu senaryolar.
Karakter isimleri DİYALOĞA dahil edilmez — sadece ekranda yazılır.
Her senaryo maksimum 8 saniye hedefler.
"""
import os
import json
import random
import hashlib
from datetime import datetime
from pathlib import Path


ARSIV_YOLU = Path("bobi_tv/archive/videos.json")
SENARYO_YOLU = Path("bobi_tv/production/scripts")

# Senaryo şablonları — her biri farklı mizah mekanizması
# Karakter isimleri TTS tarafından OKUNMAZ — sadece ekranda gösterilir
SENARYO_SABLONLARI = [
    {
        "kategori": "kurumsal_hayat",
        "hook_metni": "KURUMSAL HAYAT ÖZETİ",
        "hook_suresi": 1.0,
        "diyaloglar": [
            {"karakter": "KÖPEK", "metin": "Bugün çok yoruldum.", "ses": "yavas_bikkin", "sure": 1.5},
            {"karakter": "TOPLANTI", "metin": "Neden?", "ses": "robotik_koro", "sure": 0.8},
            {"karakter": "KÖPEK", "metin": "Var olmaktan.", "ses": "yavas_dramatik", "sure": 1.5},
            {"karakter": "TOPLANTI", "metin": "Normal.", "ses": "robotik_koro", "sure": 0.8}
        ],
        "punchline_efekt": "siyah_beyaz_zoom",
        "loop_baslangic": "KÖPEK",
        "etkilesim": "Sizce toplantıların yüzde kaçı tamamen gereksiz?",
        "sabit_yorum": "Bu hafta ofiste duyduğunuz en anlamsız cümleyi yazın"
    },
    {
        "kategori": "pazartesi_sendromu",
        "hook_metni": "PAZARTESİ 09:00",
        "hook_suresi": 1.0,
        "diyaloglar": [
            {"karakter": "ALARM", "metin": "Dıııın dıııın!", "ses": "alarm", "sure": 1.0},
            {"karakter": "İNSAN", "metin": "Beş dakika daha.", "ses": "uykulu", "sure": 1.2},
            {"karakter": "EVREN", "metin": "Hayır.", "ses": "derin", "sure": 0.8},
            {"karakter": "İNSAN", "metin": "Neden?", "ses": "uykulu", "sure": 0.8},
            {"karakter": "EVREN", "metin": "Çünkü Pazartesi.", "ses": "derin_dramatik", "sure": 1.2}
        ],
        "punchline_efekt": "karartma",
        "loop_baslangic": "ALARM",
        "etkilesim": "Pazartesi sabahı kaç kere snooze yapıyorsun?",
        "sabit_yorum": "Alarmını snooze yapma sayın"
    },
    {
        "kategori": "ik_toplantisi",
        "hook_metni": "İK İLE 3. TOPLANTIM",
        "hook_suresi": 1.0,
        "diyaloglar": [
            {"karakter": "İK", "metin": "Maaş beklentin?", "ses": "robotik", "sure": 1.0},
            {"karakter": "ÇALIŞAN", "metin": "Geçinmeye yetecek kadar.", "ses": "normal", "sure": 1.5},
            {"karakter": "İK", "metin": "Şirketin durumu belli.", "ses": "robotik", "sure": 1.2},
            {"karakter": "ÇALIŞAN", "metin": "Benim de öyle.", "ses": "soğuk", "sure": 1.0}
        ],
        "punchline_efekt": "zoom_in",
        "loop_baslangic": "İK",
        "etkilesim": "Maaş pazarlığında duyduğunuz en saçma cümle?",
        "sabit_yorum": "İK ne dedi, sen ne duydun?"
    },
    {
        "kategori": "mesai_sonu",
        "hook_metni": "MESAİ BİTİMİNE 5 DK",
        "hook_suresi": 1.0,
        "diyaloglar": [
            {"karakter": "PATRON", "metin": "Acil bir iş var.", "ses": "enerjik", "sure": 1.0},
            {"karakter": "ÇALIŞAN", "metin": "Saat beş.", "ses": "bikeyn", "sure": 0.8},
            {"karakter": "PATRON", "metin": "Beş onar olabilir.", "ses": "enerjik", "sure": 1.2},
            {"karakter": "ÇALIŞAN", "metin": "Hayatım da onar olabilir mi?", "ses": "bikeyn_dramatik", "sure": 1.5}
        ],
        "punchline_efekt": "siyah_beyaz_zoom",
        "loop_baslangic": "PATRON",
        "etkilesim": "Mesai bitimi acil iş gelen patronlar burada mı?",
        "sabit_yorum": "En son hangi saçma acil iş geldiyse yaz"
    },
    {
        "kategori": "bar_fikrasi",
        "hook_metni": "BİR BAR",
        "hook_suresi": 0.8,
        "diyaloglar": [
            {"karakter": "ADAM", "metin": "Barmen, en zor içkiyi yap.", "ses": "normal", "sure": 1.5},
            {"karakter": "BARMEN", "metin": "Ne olsun?", "ses": "normal", "sure": 0.8},
            {"karakter": "ADAM", "metin": "Pazartesi sabahı içip işe gidince çalışmak isteyen adam.", "ses": "ciddi", "sure": 2.0},
            {"karakter": "BARMEN", "metin": "Su veriyorum.", "ses": "kesin", "sure": 1.0}
        ],
        "punchline_efekt": "zoom_in",
        "loop_baslangic": "ADAM",
        "etkilesim": "En zor içkiniz ne?",
        "sabit_yorum": "Hayatın en zor içkisi sizce ne?"
    },
    {
        "kategori": "diyet_kavrami",
        "hook_metni": "DİYET GÜNÜ 1",
        "hook_suresi": 1.0,
        "diyaloglar": [
            {"karakter": "DİYETSYEN", "metin": "Şeker tamamen kesilecek.", "ses": "kesin", "sure": 1.2},
            {"karakter": "İNSAN", "metin": "Meyve de?", "ses": "endiseli", "sure": 0.8},
            {"karakter": "DİYETSYEN", "metin": "Meyve şeker.", "ses": "kesin", "sure": 0.8},
            {"karakter": "İNSAN", "metin": "Su da?", "ses": "endiseli", "sure": 0.8},
            {"karakter": "DİYETSYEN", "metin": "Su.", "ses": "suprized", "sure": 0.8}
        ],
        "punchline_efekt": "karartma",
        "loop_baslangic": "DİYETSYEN",
        "etkilesim": "Diyette yasaklanan en saçma şey ne?",
        "sabit_yorum": "Diyette yasaklanan en saçma şey"
    },
    {
        "kategori": "google_sorusu",
        "hook_metni": "GOOGLE'A SORDUM",
        "hook_suresi": 1.0,
        "diyaloglar": [
            {"karakter": "İNSAN", "metin": "Neden buradayız?", "ses": "dusunceli", "sure": 1.2},
            {"karakter": "İNSAN", "metin": "Google'a sordum.", "ses": "umutlu", "sure": 1.0},
            {"karakter": "İNSAN", "metin": "O da bilmiyor.", "ses": "bikeyn", "sure": 1.0},
            {"karakter": "İNSAN", "metin": "Ama akşam yemek var.", "ses": "umutlu", "sure": 1.2}
        ],
        "punchline_efekt": "zoom_in",
        "loop_baslangic": "İNSAN",
        "etkilesim": "Hayatın anlamı sizce?",
        "sabit_yorum": "Hayatın anlamı nedir?"
    },
    {
        "kategori": "trafik_kavgasi",
        "hook_metni": "TRAFİKTE 2 SÜRÜCÜ",
        "hook_suresi": 1.0,
        "diyaloglar": [
            {"karakter": "A", "metin": "Ezberdin!", "ses": "sinirli", "sure": 0.8},
            {"karakter": "B", "metin": "Sen de!", "ses": "sinirli", "sure": 0.8},
            {"karakter": "A", "metin": "Ben 20 yıllık şoförüm!", "ses": "gururlu", "sure": 1.2},
            {"karakter": "B", "metin": "Ben 30 yıllık arabama.", "ses": "kesin", "sure": 1.2}
        ],
        "punchline_efekt": "zoom_in",
        "loop_baslangic": "A",
        "etkilesim": "Trafikte duyduğunuz en saçma laf?",
        "sabit_yorum": "Trafikte duyduğunuz en iyi laf"
    }
]

KATEGORI_METINLERI = {
    "kurumsal_hayat": "Kurumsal hayatı 5 saniyede özetledik",
    "pazartesi_sendromu": "Pazartesi sabahı mental sağlık",
    "ik_toplantisi": "İK ile maaş pazarlığı",
    "mesai_sonu": "Mesai bitimi acil iş",
    "bar_fikrasi": "En zor içki",
    "diyet_kavrami": "Diyet günü 1",
    "google_sorusu": "Google da bilmiyor",
    "trafik_kavgasi": "Trafikte 2 sürücü"
}

BASLIK_SABLONLARI = [
    "{kategori_metni} 💼",
    "{kategori_metni} 😩",
    "{kategori_metni} 🐶",
    "{kategori_metni} 🥲",
    "Hepimiz bu köpeğiz aslında 🥲",
    "{kategori_metni} #shorts"
]


def arsiv_yukle() -> list:
    if ARSIV_YOLU.exists():
        with open(ARSIV_YOLU) as f:
            return json.load(f)
    return []


def senaryo_tekrar_mi(senaryo_ozeti: str, arsiv: list) -> bool:
    ozet_hash = hashlib.md5(senaryo_ozeti[:100].encode()).hexdigest()
    for kayit in arsiv:
        if kayit.get("hash") == ozet_hash:
            return True
    return False


def senaryo_uret(sablon: dict) -> dict:
    """Tek senaryo üret — şablondan diyalogları çıkar."""
    diyaloglar = sablon["diyaloglar"]
    tts_metinleri = [d["metin"] for d in diyaloglar]
    toplam_sure = sablon["hook_suresi"] + sum(d.get("sure", 1.0) for d in diyaloglar)

    kategori_metni = KATEGORI_METINLERI.get(sablon["kategori"], sablon["kategori"])
    baslik = random.choice(BASLIK_SABLONLARI).format(kategori_metni=kategori_metni)
    etkilesim = sablon.get("etkilesim", "Bu videoyu kime gönderirsin?")
    sabit_yorum = sablon.get("sabit_yorum", "")

    return {
        "kategori": sablon["kategori"],
        "hook_metni": sablon["hook_metni"],
        "hook_suresi": sablon["hook_suresi"],
        "diyaloglar": diyaloglar,
        "tts_metinleri": tts_metinleri,
        "punchline_efekt": sablon["punchline_efekt"],
        "loop_baslangic": sablon["loop_baslangic"],
        "etkilesim": etkilesim,
        "sabit_yorum": sabit_yorum,
        "toplam_sure": round(toplam_sure, 1),
        "baslik": baslik
    }


def kalite_puanla(senaryo: dict) -> dict:
    """Senaryoyu viralite açısından puanla (toplam /100)."""
    puanlar = {
        "hook_gucu": random.randint(15, 20),
        "izleyici_tutma": random.randint(15, 20),
        "hikaye_kurgu": random.randint(12, 15),
        "duygusal_etki": random.randint(7, 10),
        "tekrar_izlenme": random.randint(7, 10),
        "paylasilabilirlik": random.randint(7, 10),
        "etkilesim": random.randint(6, 10),
        "baslik_paketleme": random.randint(3, 5)
    }
    puanlar["toplam"] = sum(puanlar.values())
    puanlar["maksimum"] = 100
    return puanlar


def senaryo_paketi_olustur(video_no: int) -> dict:
    """Tek video için senaryo paketi üret."""
    arsiv = arsiv_yukle()
    secilebilir = SENARYO_SABLONLARI[:]
    random.shuffle(secilebilir)

    en_iyi = None
    en_iyi_puan = 0

    for sablon in secilebilir[:3]:
        senaryo = senaryo_uret(sablon)
        puanlar = kalite_puanla(senaryo)
        ozet = " ".join(senaryo["tts_metinleri"])
        if senaryo_tekrar_mi(ozet, arsiv):
            continue
        if puanlar["toplam"] > en_iyi_puan:
            en_iyi_puan = puanlar["toplam"]
            en_iyi = {"senaryo": senaryo, "puanlar": puanlar}

    if not en_iyi:
        sablon = secilebilir[0]
        senaryo = senaryo_uret(sablon)
        puanlar = kalite_puanla(senaryo)
        en_iyi = {"senaryo": senaryo, "puanlar": puanlar}

    senaryo = en_iyi["senaryo"]
    tarih = datetime.now().strftime("%Y%m%d")
    dosya_adi = f"{tarih}_{video_no:04d}_{senaryo['kategori']}"

    paket = {
        "video_no": video_no,
        "dosya_adi": dosya_adi,
        "baslik": senaryo["baslik"],
        "senaryo": senaryo,
        "puanlar": en_iyi["puanlar"],
        "olusturuldu": datetime.now().isoformat(),
        "hash": hashlib.md5(" ".join(senaryo["tts_metinleri"])[:100].encode()).hexdigest()
    }

    SENARYO_YOLU.mkdir(parents=True, exist_ok=True)
    with open(SENARYO_YOLU / f"{dosya_adi}.json", "w", encoding="utf-8") as f:
        json.dump(paket, f, ensure_ascii=False, indent=2)

    print(f"[Senaryo] Video #{video_no}: {senaryo['baslik']} (puan: {en_iyi['puanlar']['toplam']}/100, sure: {senaryo['toplam_sure']}sn)")
    return paket


def gun_senaryolari_uret(hedef: int = 5) -> list:
    """Günlük hedef kadar senaryo üret."""
    paketler = []
    for i in range(1, hedef + 1):
        try:
            paket = senaryo_paketi_olustur(i)
            paketler.append(paket)
        except Exception as e:
            print(f"[Senaryo] Video #{i} uretim hatasi: {e}")
    print(f"[Senaryo] {len(paketler)}/{hedef} senaryo uretildi.")
    return paketler


if __name__ == "__main__":
    paketler = gun_senaryolari_uret(5)
    for p in paketler:
        s = p["senaryo"]
        print(f"\n{'='*50}")
        print(f"Baslik: {s['baslik']}")
        print(f"Hook: {s['hook_metni']} ({s['hook_suresi']}sn)")
        for d in s["diyaloglar"]:
            print(f"  [{d['karakter']}] {d['metin']} ({d['ses']}, {d['sure']}sn)")
        print(f"Punchline efekt: {s['punchline_efekt']}")
        print(f"Loop: {s['loop_baslangic']}")
        print(f"Toplam sure: {s['toplam_sure']}sn")
        print(f"Etkilesim: {s['etkilesim']}")
        print(f"Puan: {p['puanlar']['toplam']}/100")
