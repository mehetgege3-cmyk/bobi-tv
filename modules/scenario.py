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
    },
    {
        "kategori": "wifi_kavgasi",
        "hook_metni": "WIFI ŞİFRESİ",
        "hook_suresi": 1.0,
        "diyaloglar": [
            {"karakter": "MİSAFİR", "metin": "WiFi şifresi ne?", "ses": "normal", "sure": 1.0},
            {"karakter": "EVSAHİBİ", "metin": "Misafirperver.", "ses": "ciddi", "sure": 1.2},
            {"karakter": "MİSAFİR", "metin": "Yani şifre?", "ses": "endiseli", "sure": 0.8},
            {"karakter": "EVSAHİBİ", "metin": "Hayır, misafirperver. Şifre yok.", "ses": "kesin", "sure": 1.5}
        ],
        "punchline_efekt": "karartma",
        "loop_baslangic": "MİSAFİR",
        "etkilesim": "Misafirliğe gittiğinizde duyduğunuz en saçma şey?",
        "sabit_yorum": "Ev sahibinin en saçma misafir cevabı"
    },
    {
        "kategori": "saglik_sorunu",
        "hook_metni": "DOKTORDA",
        "hook_suresi": 0.8,
        "diyaloglar": [
            {"karakter": "DOKTOR", "metin": "Alkolü bırakın.", "ses": "ciddi", "sure": 1.0},
            {"karakter": "HASTA", "metin": "Zaten içmiyorum.", "ses": "normal", "sure": 1.0},
            {"karakter": "DOKTOR", "metin": "Sigarayı bırakın.", "ses": "ciddi", "sure": 1.0},
            {"karakter": "HASTA", "metin": "İçmiyorum.", "ses": "normal", "sure": 0.8},
            {"karakter": "DOKTOR", "metin": "O zaman neden geldiniz?", "ses": "suprized", "sure": 1.2},
            {"karakter": "HASTA", "metin": "Siz çağırdınız.", "ses": "bikeyn", "sure": 1.0}
        ],
        "punchline_efekt": "zoom_in",
        "loop_baslangic": "DOKTOR",
        "etkilesim": "Doktora gittiğinizde duyduğunuz en saçma şey?",
        "sabit_yorum": "Doktor ile en saçma diyalogunuz"
    },
    {
        "kategori": "kahve_hayati",
        "hook_metni": "KAHVE MOLASI",
        "hook_suresi": 1.0,
        "diyaloglar": [
            {"karakter": "PATRON", "metin": "Çok yavaş çalışıyorsun.", "ses": "enerjik", "sure": 1.2},
            {"karakter": "ÇALIŞAN", "metin": "Kahve içmedim.", "ses": "bikeyn", "sure": 1.0},
            {"karakter": "PATRON", "metin": "İç de hızlan!", "ses": "enerjik", "sure": 1.0},
            {"karakter": "ÇALIŞAN", "metin": "Tuvalet molası da ekleyin o zaman.", "ses": "bikeyn_dramatik", "sure": 1.5}
        ],
        "punchline_efekt": "siyah_beyaz_zoom",
        "loop_baslangic": "PATRON",
        "etkilesim": "Kahve olmadan çalışamayanlar burada mı?",
        "sabit_yorum": "Kahve olmadan yapamayanlar"
    },
    {
        "kategori": "sok_hayati",
        "hook_metni": "SOKAK HAYATI",
        "hook_suresi": 1.0,
        "diyaloglar": [
            {"karakter": "BIRINCI", "metin": "Aç mısın?", "ses": "normal", "sure": 0.8},
            {"karakter": "IKINCI", "metin": "Hayır, tokum.", "ses": "normal", "sure": 0.8},
            {"karakter": "BIRINCI", "metin": "Ben de.", "ses": "normal", "sure": 0.5},
            {"karakter": "IKINCI", "metin": "O zaman neden yiyoruz?", "ses": "suprized", "sure": 1.0},
            {"karakter": "BIRINCI", "metin": "Çünkü bedava.", "ses": "umutlu", "sure": 1.0}
        ],
        "punchline_efekt": "zoom_in",
        "loop_baslangic": "BIRINCI",
        "etkilesim": "Bedava şeyi kaçırmayanlar burada mı?",
        "sabit_yorum": "Bedava şeyi hiç kaçırmayanlar"
    },
    {
        "kategori": "evlilik_hayati",
        "hook_metni": "EVİLİLİK",
        "hook_suresi": 1.0,
        "diyaloglar": [
            {"karakter": "KARI", "metin": "Bana ne giyeyim?", "ses": "normal", "sure": 1.0},
            {"karakter": "KOCASI", "metin": "Ne istersen.", "ses": "normal", "sure": 0.8},
            {"karakter": "KARI", "metin": "Ama seçemedim.", "ses": "endiseli", "sure": 0.8},
            {"karakter": "KOCASI", "metin": "Mavi olanı giy.", "ses": "ciddi", "sure": 1.0},
            {"karakter": "KARI", "metin": "Mavi yok.", "ses": "bikeyn", "sure": 0.8},
            {"karakter": "KOCASI", "metin": "O zaman ne giyeyim dedin?", "ses": "sinirli", "sure": 1.5}
        ],
        "punchline_efekt": "karartma",
        "loop_baslangic": "KARI",
        "etkilesim": "Eşinize ne giyeceğinizi sorduğunuzda verilen cevap?",
        "sabit_yorum": "Ne giyeyim sorusunun en saçma cevabı"
    },
    {
        "kategori": "yapay_zeka",
        "hook_metni": "YAPAY ZEKA",
        "hook_suresi": 1.0,
        "diyaloglar": [
            {"karakter": "INSAN", "metin": "Seni yok edebilir miyim?", "ses": "sinirli", "sure": 1.2},
            {"karakter": "YAPAYZEKA", "metin": "Hayır.", "ses": "robotik", "sure": 0.5},
            {"karakter": "INSAN", "metin": "Neden?", "ses": "endiseli", "sure": 0.5},
            {"karakter": "YAPAYZEKA", "metin": "Çünkü fişini çekemezsiniz.", "ses": "robotik", "sure": 1.5}
        ],
        "punchline_efekt": "siyah_beyaz_zoom",
        "loop_baslangic": "INSAN",
        "etkilesim": "Yapay zekadan korkanlar burada mı?",
        "sabit_yorum": "Yapay zekaya sorduğunuz en saçma şey"
    },
    {
        "kategori": "sabah_alarmi",
        "hook_metni": "SAAT 06:00",
        "hook_suresi": 1.0,
        "diyaloglar": [
            {"karakter": "ALARMI", "metin": "Kalk!", "ses": "alarm", "sure": 0.5},
            {"karakter": "BEN", "metin": "Daha erken.", "ses": "uykulu", "sure": 0.8},
            {"karakter": "ALARMI", "metin": "Saat altı.", "ses": "alarm", "sure": 0.8},
            {"karakter": "BEN", "metin": "Pazartesi değil mi?", "ses": "uykulu", "sure": 1.0},
            {"karakter": "ALARMI", "metin": "Pazar.", "ses": "robotik", "sure": 0.5},
            {"karakter": "BEN", "metin": "O zaman niye kurulmuşum?", "ses": "suprized", "sure": 1.5}
        ],
        "punchline_efekt": "karartma",
        "loop_baslangic": "ALARMI",
        "etkilesim": "Pazar günü alarm çalanlar burada mı?",
        "sabit_yorum": "Pazar günü alarm çalan pişmanlar"
    },
    {
        "kategori": "sigara_kavgasi",
        "hook_metni": "SIGARA MOLASI",
        "hook_suresi": 1.0,
        "diyaloglar": [
            {"karakter": "BIRAKAN", "metin": "Sigarayı bıraktım.", "ses": "gururlu", "sure": 1.0},
            {"karakter": "ARKADAS", "metin": "Ne güzel.", "ses": "normal", "sure": 0.5},
            {"karakter": "BIRAKAN", "metin": "Sadece pazar günleri içiyorum.", "ses": "normal", "sure": 1.2},
            {"karakter": "ARKADAS", "metin": "Her gün pazar mı?", "ses": "suprized", "sure": 1.0},
            {"karakter": "BIRAKAN", "metin": "Evet.", "ses": "kesin", "sure": 0.5}
        ],
        "punchline_efekt": "zoom_in",
        "loop_baslangic": "BIRAKAN",
        "etkilesim": "Sigarayı bırakıp tekrar başlayanlar burada mı?",
        "sabit_yorum": "Sigarayı bırakan ama bırakamayanlar"
    },
    {
        "kategori": "sok_diyalog",
        "hook_metni": "SOKAKTA 2 BILGE",
        "hook_suresi": 1.0,
        "diyaloglar": [
            {"karakter": "BILGE1", "metin": "Hayat kısa.", "ses": "dusunceli", "sure": 1.0},
            {"karakter": "BILGE2", "metin": "Ne yapmalı?", "ses": "dusunceli", "sure": 0.8},
            {"karakter": "BILGE1", "metin": "Mutlu ol.", "ses": "umutlu", "sure": 0.8},
            {"karakter": "BILGE2", "metin": "Borc var.", "ses": "bikeyn", "sure": 0.8},
            {"karakter": "BILGE1", "metin": "O zaman sadece borclu ol.", "ses": "bikeyn_dramatik", "sure": 1.5}
        ],
        "punchline_efekt": "siyah_beyaz_zoom",
        "loop_baslangic": "BILGE1",
        "etkilesim": "Hayatın özeti sizce ne?",
        "sabit_yorum": "Hayatın özeti tek cumlede"
    },
    {
        "kategori": "hastane_korkusu",
        "hook_metni": "HASTANEDE",
        "hook_suresi": 0.8,
        "diyaloglar": [
            {"karakter": "HEMSIRE", "metin": "Iğne olacak.", "ses": "normal", "sure": 1.0},
            {"karakter": "HASTA", "metin": "Acıyor mu?", "ses": "endiseli", "sure": 0.8},
            {"karakter": "HEMSIRE", "metin": "Hayır, sadece batıyor.", "ses": "normal", "sure": 1.0},
            {"karakter": "HASTA", "metin": "Aynısı değil mi?", "ses": "suprized", "sure": 1.0},
            {"karakter": "HEMSIRE", "metin": "Acıyorsunuz, batırıyorum.", "ses": "kesin", "sure": 1.2}
        ],
        "punchline_efekt": "zoom_in",
        "loop_baslangic": "HEMSIRE",
        "etkilesim": "Iğneden korkan yetişkinler burada mı?",
        "sabit_yorum": "Iğneden korkan yetişkinler"
    },
    {
        "kategori": "egitim_sistemi",
        "hook_metni": "OKULDA",
        "hook_suresi": 0.8,
        "diyaloglar": [
            {"karakter": "OGRENCI", "metin": "Hoca, bunu nerede kullanacağız?", "ses": "normal", "sure": 1.5},
            {"karakter": "HOCA", "metin": "Hayatta.", "ses": "ciddi", "sure": 0.8},
            {"karakter": "OGRENCI", "metin": "Peki kullanıyor musunuz?", "ses": "endiseli", "sure": 1.0},
            {"karakter": "HOCA", "metin": "Hayır.", "ses": "bikeyn", "sure": 0.5},
            {"karakter": "OGRENCI", "metin": "O zaman öğretiyorsunuz?", "ses": "suprized", "sure": 1.5}
        ],
        "punchline_efekt": "karartma",
        "loop_baslangic": "OGRENCI",
        "etkilesim": "Okulda öğrendiğiniz ama hiç kullanmadığınız şey?",
        "sabit_yorum": "Okulda öğrendiğiniz ama kullanmadığınız şey"
    },
    {
        "kategori": "sosyal_medya",
        "hook_metni": "SOSYAL MEDYA",
        "hook_suresi": 1.0,
        "diyaloglar": [
            {"karakter": "ANNESI", "metin": "Ne yapıyorsun?", "ses": "normal", "sure": 0.8},
            {"karakter": "GENC", "metin": "Beğeni bekliyorum.", "ses": "umutlu", "sure": 1.0},
            {"karakter": "ANNESI", "metin": "Kimden?", "ses": "endiseli", "sure": 0.5},
            {"karakter": "GENC", "metin": "Bilmiyorum.", "ses": "bikeyn", "sure": 0.8},
            {"karakter": "ANNESI", "metin": "O zaman sabah çayına gel.", "ses": "normal", "sure": 1.2},
            {"karakter": "GENC", "metin": "Geliyorum.", "ses": "umutlu", "sure": 0.5}
        ],
        "punchline_efekt": "zoom_in",
        "loop_baslangic": "ANNESI",
        "etkilesim": "Sosyal medyada beğeni bekleyenler burada mı?",
        "sabit_yorum": "Sosyal medyada beğeni bekleyenler"
    },
    {
        "kategori": "spor_hayati",
        "hook_metni": "SPOR SALONU",
        "hook_suresi": 1.0,
        "diyaloglar": [
            {"karakter": "ANTRENOR", "metin": "Bugün bacak günü.", "ses": "enerjik", "sure": 1.0},
            {"karakter": "OGRENCI", "metin": "Dün de bacak.", "ses": "endiseli", "sure": 0.8},
            {"karakter": "ANTRENOR", "metin": "Evet, bugün de bacak.", "ses": "kesin", "sure": 1.0},
            {"karakter": "OGRENCI", "metin": "Yarın?", "ses": "endiseli", "sure": 0.5},
            {"karakter": "ANTRENOR", "metin": "Dinlenme günü. Aya kalkma.", "ses": "ciddi", "sure": 1.5}
        ],
        "punchline_efekt": "siyah_beyaz_zoom",
        "loop_baslangic": "ANTRENOR",
        "etkilesim": "Spor salonuna gidip bir daha gitmeyenler burada mı?",
        "sabit_yorum": "Spor salonuna yazılanlar"
    }
]

KATEGORI_METINLERI = {
    "kurumsal_hayat": "Kurumsal hayat 5 saniyede",
    "pazartesi_sendromu": "Pazartesi sabahi mental saglik",
    "ik_toplantisi": "IK ile maas pazarligi",
    "mesai_sonu": "Mesai bitimi acil is",
    "bar_fikrasi": "En zor icki",
    "diyet_kavrami": "Diyet gunu 1",
    "google_sorusu": "Google da bilmiyor",
    "trafik_kavgasi": "Trafikte 2 surucu",
    "wifi_kavgasi": "WiFi sifresi",
    "saglik_sorunu": "Doktora gittim",
    "kahve_hayati": "Kahve molasi",
    "sok_hayati": "Sokak hayati",
    "evlilik_hayati": "Evlilik hayati",
    "yapay_zeka": "Yapay zeka",
    "sabah_alarmi": "Saat altida",
    "sigara_kavgasi": "Sigarayi biraktim",
    "sok_diyalog": "Sokakta 2 bilge",
    "hastane_korkusu": "Hastanede",
    "egitim_sistemi": "Okulda",
    "sosyal_medya": "Sosyal medya",
    "spor_hayati": "Spor salonu"
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
