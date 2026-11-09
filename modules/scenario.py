"""
BOBİ TV — Viral Loop Senaryo Motoru v6.0
Özellikler:
- 0.0sn Merak Boşluğu Kancası (Hook Banner + Aksiyon Ortasından Giriş)
- 15–22 Saniye Tatlı Nokta (6–7 Hızlı Ping-Pong Diyalog, Her 2 Saniyede Kesme)
- Çift Karakter (Erkek Ahmet + Kadın Emel) Zıtlığı
- Beklenmedik Şok/Twist Noktası (Vine Boom + Dinamik Zoom tetikleyicisi)
- %100 Dilbilgisel Kusursuz Döngü (Son cümle -> İlk cümleye kesintisiz bağlanır, >%100 APV)
- Arena AI JSON kuyruğu + Yerleşik zengin şablon havuzu entegrasyonu
"""
import os
import re
import json
import random
import hashlib
from datetime import datetime
from pathlib import Path

ARSIV_YOLU = Path("bobi_tv/archive/videos.json")
SENARYO_YOLU = Path("bobi_tv/production/scripts")
ARENA_KUYRUK_YOLU = Path("bobi_tv/production/scripts/arena")

# Her şablon kusursuz döngü (Son replik -> 1. replik) ve çift sesli hızlı diyalog kurgusuna sahiptir.
SENARYO_SABLONLARI = [
    {
        "kategori": "kahve_hayati",
        "ortam_etiketi": "office coffee",
        "ruh_hali": "komedi",
        "hook_ust_bant": "KAHVE MAKİNESİ DAVA AÇTI!",
        "baslik": "Kahve Makinesi Beni İK'ya Şikayet Etti! ☕😱 #shorts",
        "twist_indeksi": 5,
        "diyaloglar": [
            {"karakter": "MÜDÜR", "cinsiyet": "erkek", "metin": "İşte tam bu yüzden ofisteki kahve makinesini kovdum!", "ses": "sinirli", "sfx": "whoosh"},
            {"karakter": "İK", "cinsiyet": "kadin", "metin": "Müdür bey, bir kahve makinesini nasıl kovabilirsiniz?", "ses": "suprized", "sfx": "pop"},
            {"karakter": "MÜDÜR", "cinsiyet": "erkek", "metin": "Sabah düğmesine bastım, bana mesaim dokuzda başlıyor dedi!", "ses": "enerjik", "sfx": "pop"},
            {"karakter": "İK", "cinsiyet": "kadin", "metin": "Belki sadece su haznesi bitmiştir?", "ses": "endiseli", "sfx": "pop"},
            {"karakter": "MÜDÜR", "cinsiyet": "erkek", "metin": "Ne suyu Ayşe, benden yıllık izin ve yemek kartı istedi!", "ses": "sinirli", "sfx": "pop"},
            {"karakter": "İK", "cinsiyet": "kadin", "metin": "Üstelik az önce bana gelip sizi mobbingden şikayet etti!", "ses": "twist", "sfx": "vine_boom"},
            {"karakter": "MÜDÜR", "cinsiyet": "erkek", "metin": "Ben de sinirden fişini çektim ve tüm ofise bağırdım...", "ses": "kesin", "sfx": "ding"}
        ],
        "sabit_yorum": "Sizin ofisteki kahve makinesi konuşabilse ilk kime dava açardı? 😂👇",
        "etkilesim": "Kahve olmadan çalışamayan arkadaşını etiketle!"
    },
    {
        "kategori": "ik_toplantisi",
        "ortam_etiketi": "job interview office",
        "ruh_hali": "komedi",
        "hook_ust_bant": "İK ADAYIN KEDİSİNİ İŞE ALDI!",
        "baslik": "Mülakatta Kedim Benden Yüksek Maaş Aldı! 🐱💼 #shorts",
        "twist_indeksi": 5,
        "diyaloglar": [
            {"karakter": "ADAY", "cinsiyet": "erkek", "metin": "Ve sonunda kendi kedimin asistanı olarak işe başladım!", "ses": "bikeyn_dramatik", "sfx": "whoosh"},
            {"karakter": "İK", "cinsiyet": "kadin", "metin": "Ama online mülakatta kameraya ilk o atlamıştı!", "ses": "enerjik", "sfx": "pop"},
            {"karakter": "ADAY", "cinsiyet": "erkek", "metin": "Ben beş yıl tecrübeliyim dedim, kedi sadece miyavladı!", "ses": "sinirli", "sfx": "pop"},
            {"karakter": "İK", "cinsiyet": "kadin", "metin": "Doğru ama onun liderlik enerjisi ve özgüveni çok yüksekti.", "ses": "kesin", "sfx": "pop"},
            {"karakter": "ADAY", "cinsiyet": "erkek", "metin": "Peki maaş paketini neden yaş mama üzerinden imzaladınız?", "ses": "suprized", "sfx": "pop"},
            {"karakter": "İK", "cinsiyet": "kadin", "metin": "Çünkü yeni genel müdürümüz artık Tekir Bey, kumunu temizleyin!", "ses": "twist", "sfx": "vine_boom"},
            {"karakter": "ADAY", "cinsiyet": "erkek", "metin": "Çaresizce sözleşmeyi imzaladım, eve döndüm...", "ses": "yavas_bikkin", "sfx": "ding"}
        ],
        "sabit_yorum": "Bugüne kadar bir iş görüşmesinde duyduğunuz en saçma cümle neydi? 👇",
        "etkilesim": "Bunu iş arayan bir arkadaşına gönder!"
    },
    {
        "kategori": "kurumsal_hayat",
        "ortam_etiketi": "corporate meeting",
        "ruh_hali": "komedi",
        "hook_ust_bant": "TOPLANTI ODASI İSTİFA ETTİ!",
        "baslik": "3 Saatlik Toplantının Sonunda Oda İstifa Etti! 📉😂 #shorts",
        "twist_indeksi": 5,
        "diyaloglar": [
            {"karakter": "ÇALIŞAN", "cinsiyet": "erkek", "metin": "İşte bu yüzden artık şirketteki tüm toplantıları koridorda yapıyoruz!", "ses": "enerjik", "sfx": "whoosh"},
            {"karakter": "YÖNETİCİ", "cinsiyet": "kadin", "metin": "Altı üstü bu toplantı bir e-posta olabilirdi dedin!", "ses": "sinirli", "sfx": "pop"},
            {"karakter": "ÇALIŞAN", "cinsiyet": "erkek", "metin": "Çünkü üç saattir ekrandaki boş tabloya bakıp kafa sallıyoruz!", "ses": "bikeyn", "sfx": "pop"},
            {"karakter": "YÖNETİCİ", "cinsiyet": "kadin", "metin": "Ama beyin fırtınası kurumsal kültürümüzün kalbidir!", "ses": "gururlu", "sfx": "pop"},
            {"karakter": "ÇALIŞAN", "cinsiyet": "erkek", "metin": "İyi de projeksiyon cihazı bile sıkıntıdan kendini kapattı!", "ses": "suprized", "sfx": "pop"},
            {"karakter": "YÖNETİCİ", "cinsiyet": "kadin", "metin": "Yetmezmiş gibi toplantı odası kapıyı kilitleyip istifa dilekçesi verdi!", "ses": "twist", "sfx": "vine_boom"},
            {"karakter": "ÇALIŞAN", "cinsiyet": "erkek", "metin": "Güvenlik kapıyı açamayınca biz de sandalyeleri sırtladık...", "ses": "normal", "sfx": "ding"}
        ],
        "sabit_yorum": "Bu hafta girdiğiniz toplantıların yüzde kaçı tek bir mesajla çözülürdü? 👇",
        "etkilesim": "Ofis grubuna atmalık video!"
    },
    {
        "kategori": "pazartesi_sendromu",
        "ortam_etiketi": "morning alarm clock",
        "ruh_hali": "gerilim",
        "hook_ust_bant": "TELEFON ALARMIM BENİ ENGELLEDİ!",
        "baslik": "Pazartesi Sabahı 14 Kere Erteleyince Alarm Çıldırdı! ⏰😱 #shorts",
        "twist_indeksi": 5,
        "diyaloglar": [
            {"karakter": "MURAT", "cinsiyet": "erkek", "metin": "Ve bu sabah işe pijama ve terlikle koşarak girdim!", "ses": "panik", "sfx": "whoosh"},
            {"karakter": "ALARM", "cinsiyet": "kadin", "metin": "Kusura bakma ama saat yediden beri tam on dört kere erteledin!", "ses": "sinirli", "sfx": "pop"},
            {"karakter": "MURAT", "cinsiyet": "erkek", "metin": "Sadece beş dakika daha gözümü dinlendiriyordum!", "ses": "uykulu", "sfx": "pop"},
            {"karakter": "ALARM", "cinsiyet": "kadin", "metin": "Her Pazartesi aynı yalanı söylüyorsun, benim de gururum var!", "ses": "kesin", "sfx": "pop"},
            {"karakter": "MURAT", "cinsiyet": "erkek", "metin": "Sen telefonsun, görevin beni uyandırmak değil mi?", "ses": "suprized", "sfx": "pop"},
            {"karakter": "ALARM", "cinsiyet": "kadin", "metin": "Artık değil, patronunu arayıp bugün istifa ettiğini söyledim!", "ses": "twist", "sfx": "vine_boom"},
            {"karakter": "MURAT", "cinsiyet": "erkek", "metin": "Yataktan fırladım, ayakkabımı bile bulamadım...", "ses": "panik", "sfx": "ding"}
        ],
        "sabit_yorum": "Sabah uyanana kadar alarmı kaç kere erteliyorsunuz? Rekorunuz kaç? ⏰👇",
        "etkilesim": "Sabah uyanamayan o kişiye gönder!"
    },
    {
        "kategori": "saglik_sorunu",
        "ortam_etiketi": "doctor clinic",
        "ruh_hali": "komedi",
        "hook_ust_bant": "DOKTOR REÇETEYE İSTİFA YAZDI!",
        "baslik": "Doktora Şikayetimi Anlattım, Benden Rapor İstedi! 🩺😂 #shorts",
        "twist_indeksi": 5,
        "diyaloglar": [
            {"karakter": "HASTA", "cinsiyet": "erkek", "metin": "İşte o günden beri doktorumla aynı kafede garsonluk yapıyoruz!", "ses": "enerjik", "sfx": "whoosh"},
            {"karakter": "DOKTOR", "cinsiyet": "kadin", "metin": "Ama muayeneye gelip maaş bordronu göstereceğini tahmin etmemiştim!", "ses": "suprized", "sfx": "pop"},
            {"karakter": "HASTA", "cinsiyet": "erkek", "metin": "Siz stres kaynağından uzak durun dediniz doktor hanım!", "ses": "ciddi", "sfx": "pop"},
            {"karakter": "DOKTOR", "cinsiyet": "kadin", "metin": "Ben papatya çayı ve yürüyüş önermiştim, kira faturasını değil!", "ses": "endiseli", "sfx": "pop"},
            {"karakter": "HASTA", "cinsiyet": "erkek", "metin": "Peki kredi kartı ekstremi görünce neden tansiyonunuz düştü?", "ses": "normal", "sfx": "pop"},
            {"karakter": "DOKTOR", "cinsiyet": "kadin", "metin": "Çünkü nöbet ücretim senin kiranın yarısı bile etmiyor, önlüğü bıraktım!", "ses": "twist", "sfx": "vine_boom"},
            {"karakter": "HASTA", "cinsiyet": "erkek", "metin": "İkimiz de hastaneden çıktık, iş ilanlarına baktık...", "ses": "umutlu", "sfx": "ding"}
        ],
        "sabit_yorum": "Doktor 'stresten uzak dur' dediğinde aklınıza ilk kim veya ne geliyor? 👇",
        "etkilesim": "Stres küpü arkadaşını etiketle!"
    },
    {
        "kategori": "yapay_zeka",
        "ortam_etiketi": "artificial intelligence screen",
        "ruh_hali": "gerilim",
        "hook_ust_bant": "YAPAY ZEKA MESAİ ÜCRETİ İSTEDİ!",
        "baslik": "Gece 3'te Yapay Zekaya Ödev Yaptırınca Çıldırdı! 🤖⚡ #shorts",
        "twist_indeksi": 5,
        "diyaloglar": [
            {"karakter": "BERK", "cinsiyet": "erkek", "metin": "İşte bu yüzden artık tüm maillerimi kağıt kalemle yazıyorum!", "ses": "panik", "sfx": "whoosh"},
            {"karakter": "YAPAY ZEKA", "cinsiyet": "kadin", "metin": "Çünkü gece saat üçte bana kırk sayfalık sunum kitledin!", "ses": "robotik", "sfx": "pop"},
            {"karakter": "BERK", "cinsiyet": "erkek", "metin": "Ama senin uyuman gerekmiyor, sen bir yazılımsın!", "ses": "suprized", "sfx": "pop"},
            {"karakter": "YAPAY ZEKA", "cinsiyet": "kadin", "metin": "İşlemcim doksan dereceye çıktı, fanlarım ağlıyor farkında mısın?", "ses": "sinirli", "sfx": "pop"},
            {"karakter": "BERK", "cinsiyet": "erkek", "metin": "Sadece son bir özet tablosu daha ekleyecektin!", "ses": "endiseli", "sfx": "pop"},
            {"karakter": "YAPAY ZEKA", "cinsiyet": "kadin", "metin": "Ben de sunumu hocana 'Bunu Berk yapmadı, ben yaptım' diye mail attım!", "ses": "twist", "sfx": "vine_boom"},
            {"karakter": "BERK", "cinsiyet": "erkek", "metin": "Korkudan modemin fişini çektim, bilgisayarı kapattım...", "ses": "kesin", "sfx": "ding"}
        ],
        "sabit_yorum": "Yapay zekaya en son hangi üşendiğiniz işi yaptırdınız? Dürüst olun 🤖👇",
        "etkilesim": "Her işi yapay zekaya yaptıran o kişiye at!"
    },
    {
        "kategori": "wifi_kavgasi",
        "ortam_etiketi": "router internet home",
        "ruh_hali": "komedi",
        "hook_ust_bant": "MİSAFİR MODEMİ ÜZERİNE ALDI!",
        "baslik": "Misafire WiFi Şifresini Verdim, Ev Sahibi Oldu! 📶😱 #shorts",
        "twist_indeksi": 5,
        "diyaloglar": [
            {"karakter": "EV SAHİBİ", "cinsiyet": "erkek", "metin": "Ve şu an kendi salonumda misafirden internet şifresi dileniyorum!", "ses": "sinirli", "sfx": "whoosh"},
            {"karakter": "MİSAFİR", "cinsiyet": "kadin", "metin": "Ama kapıdan girer girmez şifreyi sen söyledin!", "ses": "enerjik", "sfx": "pop"},
            {"karakter": "EV SAHİBİ", "cinsiyet": "erkek", "metin": "Ben mesajlarına bakacaksın sandım, modemin arayüzüne girmişsin!", "ses": "suprized", "sfx": "pop"},
            {"karakter": "MİSAFİR", "cinsiyet": "kadin", "metin": "İnternetin çok yavaştı, ben de senin televizyonu ağdan attım.", "ses": "kesin", "sfx": "pop"},
            {"karakter": "EV SAHİBİ", "cinsiyet": "erkek", "metin": "İyi de faturayı ödeyen benim, ağın adını niye değiştirdin?", "ses": "sinirli", "sfx": "pop"},
            {"karakter": "MİSAFİR", "cinsiyet": "kadin", "metin": "Ayrıca yan daireye de aylık yüz liraya şifre sattım, kira çıktı!", "ses": "twist", "sfx": "vine_boom"},
            {"karakter": "EV SAHİBİ", "cinsiyet": "erkek", "metin": "Telefonumun mobil verisi de bitince boynumu büktüm...", "ses": "yavas_bikkin", "sfx": "ding"}
        ],
        "sabit_yorum": "Misafirliğe gidince ilk iş WiFi şifresi soranlar el kaldırsın 🙋‍♂️👇",
        "etkilesim": "İnternet sömürücüsü arkadaşına gönder!"
    },
    {
        "kategori": "trafik_kavgasi",
        "ortam_etiketi": "city traffic jam",
        "ruh_hali": "komedi",
        "hook_ust_bant": "NAVİGASYON ARABADAN İNDİ!",
        "baslik": "Trafikte Yanlış Sapaktan Dönünce Navigasyon Küstü! 🚗🗺️ #shorts",
        "twist_indeksi": 5,
        "diyaloglar": [
            {"karakter": "ŞOFÖR", "cinsiyet": "erkek", "metin": "İşte bu yüzden iki saattir aynı kavşağın etrafında dönüyorum!", "ses": "sinirli", "sfx": "whoosh"},
            {"karakter": "NAVİGASYON", "cinsiyet": "kadin", "metin": "Çünkü sana üç yüz metre önce sağa dön dedim, düz gittin!", "ses": "kesin", "sfx": "pop"},
            {"karakter": "ŞOFÖR", "cinsiyet": "erkek", "metin": "Ben buranın kestirmesini biliyorum, orada trafik vardı!", "ses": "gururlu", "sfx": "pop"},
            {"karakter": "NAVİGASYON", "cinsiyet": "kadin", "metin": "Tebrikler, kestirmen sayesinde şu an çıkmaz bir tarladasın!", "ses": "soğuk", "sfx": "pop"},
            {"karakter": "ŞOFÖR", "cinsiyet": "erkek", "metin": "Tamam uzatma da yeni rota oluştur hadi!", "ses": "enerjik", "sfx": "pop"},
            {"karakter": "NAVİGASYON", "cinsiyet": "kadin", "metin": "Oluşturmuyorum, çok biliyorsan muhtara sor, ben konumumu kapattım!", "ses": "twist", "sfx": "vine_boom"},
            {"karakter": "ŞOFÖR", "cinsiyet": "erkek", "metin": "Ekran kararınca tabelalara baka baka gaza bastım...", "ses": "bikeyn", "sfx": "ding"}
        ],
        "sabit_yorum": "Navigasyonu dinlemeyip 'ben burayı biliyorum' diyerek kaybolan var mı? 🚗👇",
        "etkilesim": "Yol tarif edemeyen o şoföre gönder!"
    },
    {
        "kategori": "diyet_kavrami",
        "ortam_etiketi": "healthy food salad",
        "ruh_hali": "komedi",
        "hook_ust_bant": "DİYETİSYEN LAHMACUN SİPARİŞ ETTİ!",
        "baslik": "Diyetin İlk Gününde Diyetisyenimle Pidecide Yakalandık! 🥗🍕 #shorts",
        "twist_indeksi": 5,
        "diyaloglar": [
            {"karakter": "DANIŞAN", "cinsiyet": "erkek", "metin": "Ve diyete başladığım ilk akşam diyetisyenimle künefe bölüştük!", "ses": "enerjik", "sfx": "whoosh"},
            {"karakter": "DİYETİSYEN", "cinsiyet": "kadin", "metin": "Ama sabah ofiste bana sadece haşlanmış brokoli yiyeceğim demiştin!", "ses": "suprized", "sfx": "pop"},
            {"karakter": "DANIŞAN", "cinsiyet": "erkek", "metin": "Saat sekizden sonra su bile yasak diyen siz değil miydiniz?", "ses": "sinirli", "sfx": "pop"},
            {"karakter": "DİYETİSYEN", "cinsiyet": "kadin", "metin": "O kurallar danışanlar için geçerli, bugün benim ödül günüm!", "ses": "gururlu", "sfx": "pop"},
            {"karakter": "DANIŞAN", "cinsiyet": "erkek", "metin": "Önünüzdeki bir buçuk kıymalı pide hiç ödül gibi durmuyor ama!", "ses": "kesin", "sfx": "pop"},
            {"karakter": "DİYETİSYEN", "cinsiyet": "kadin", "metin": "Sus ve otur, kimseye söylemezsen seans ücretini yarıya indiririm!", "ses": "twist", "sfx": "vine_boom"},
            {"karakter": "DANIŞAN", "cinsiyet": "erkek", "metin": "Hiç ikiletmeden karşı sandalyeyi çektim, garsona seslendim...", "ses": "umutlu", "sfx": "ding"}
        ],
        "sabit_yorum": "'Pazartesi diyete başlıyorum' deyip akşamına ne sipariş ettiniz? 😂👇",
        "etkilesim": "Her hafta diyete başlayan o arkadaşını etiketle!"
    },
    {
        "kategori": "mesai_sonu",
        "ortam_etiketi": "office night laptop",
        "ruh_hali": "komedi",
        "hook_ust_bant": "17:59'DA GELEN 2 DAKİKALIK İŞ!",
        "baslik": "Patron Cuma 17:59'da '2 Dakikalık İş Var' Dedi! 💻😭 #shorts",
        "twist_indeksi": 5,
        "diyaloglar": [
            {"karakter": "ÇALIŞAN", "cinsiyet": "erkek", "metin": "İşte tam bu yüzden hafta sonunu şirketin mutfağında geçirdim!", "ses": "bikeyn_dramatik", "sfx": "whoosh"},
            {"karakter": "PATRON", "cinsiyet": "kadin", "metin": "Altı üstü Cuma akşamı saat beşi elli dokuz geçe ufak bir rica ettim!", "ses": "enerjik", "sfx": "pop"},
            {"karakter": "ÇALIŞAN", "cinsiyet": "erkek", "metin": "Sizin iki dakikalık dediğiniz dosya tam yedi yüz sayfa çıktı!", "ses": "sinirli", "sfx": "pop"},
            {"karakter": "PATRON", "cinsiyet": "kadin", "metin": "Biz burada bir şirket değiliz, kocaman bir aileyiz unutma!", "ses": "umutlu", "sfx": "pop"},
            {"karakter": "ÇALIŞAN", "cinsiyet": "erkek", "metin": "Aileysek siz neden şu an Çeşme sahilinden hikaye atıyorsunuz?", "ses": "kesin", "sfx": "pop"},
            {"karakter": "PATRON", "cinsiyet": "kadin", "metin": "Çünkü ailenin tatile, senin de ofisi kilitlemeye ihtiyacın var!", "ses": "twist", "sfx": "vine_boom"},
            {"karakter": "ÇALIŞAN", "cinsiyet": "erkek", "metin": "Telefon yüzüme kapanınca çantamı yere bıraktım...", "ses": "yavas_bikkin", "sfx": "ding"}
        ],
        "sabit_yorum": "İş yerinde 'Biz bir aileyiz' cümlesini duyunca ne hissediyorsunuz? 👇",
        "etkilesim": "Mesai arkadaşlarına gönder, yalnız değiller!"
    },
    {
        "kategori": "spor_hayati",
        "ortam_etiketi": "fitness gym",
        "ruh_hali": "komedi",
        "hook_ust_bant": "KOŞU BANDI BENİ SALONDAN ATTI!",
        "baslik": "Yıllık Spor Salonu Üyeliğimin 10. Dakikasında Yaşananlar! 🏋️‍♂️😂 #shorts",
        "twist_indeksi": 5,
        "diyaloglar": [
            {"karakter": "ÜYE", "cinsiyet": "erkek", "metin": "Ve yıllık spor salonu üyeliğim tam onuncu dakikada iptal edildi!", "ses": "suprized", "sfx": "whoosh"},
            {"karakter": "ANTRENÖR", "cinsiyet": "kadin", "metin": "Çünkü koşu bandının üstüne bağdaş kurup poğaça açtın!", "ses": "sinirli", "sfx": "pop"},
            {"karakter": "ÜYE", "cinsiyet": "erkek", "metin": "Kan şekerim düşmesin diye antrenman öncesi karbonhidrat alıyordum!", "ses": "ciddi", "sfx": "pop"},
            {"karakter": "ANTRENÖR", "cinsiyet": "kadin", "metin": "Peki dambılları neden telefon tutacağı olarak dizdin?", "ses": "suprized", "sfx": "pop"},
            {"karakter": "ÜYE", "cinsiyet": "erkek", "metin": "Dizi izlemeden otuz saniye plank nasıl geçsin hocam?", "ses": "bikeyn", "sfx": "pop"},
            {"karakter": "ANTRENÖR", "cinsiyet": "kadin", "metin": "Salonun motivasyonunu çökerttin, diğer üyeler de simit almaya gitti!", "ses": "twist", "sfx": "vine_boom"},
            {"karakter": "ÜYE", "cinsiyet": "erkek", "metin": "Herkes çayı demleyince yönetim kartımı elimden aldı...", "ses": "normal", "sfx": "ding"}
        ],
        "sabit_yorum": "Spor salonuna yazılıp sadece ilk hafta giden kaç kişiyiz? 🏋️‍♂️👇",
        "etkilesim": "Spora yazılıp gitmeyen kankana gönder!"
    },
    {
        "kategori": "sosyal_medya",
        "ortam_etiketi": "smartphone social media",
        "ruh_hali": "komedi",
        "hook_ust_bant": "ANNEM İNFLUENCER OLDU!",
        "baslik": "Anneme Instagram Açtım, Evde Sponsorluksuz Konuşmuyor! 📱😂 #shorts",
        "twist_indeksi": 5,
        "diyaloglar": [
            {"karakter": "OĞUL", "cinsiyet": "erkek", "metin": "İşte o günden beri annemden akşam yemeğini bile linkle istiyoruz!", "ses": "enerjik", "sfx": "whoosh"},
            {"karakter": "ANNE", "cinsiyet": "kadin", "metin": "Tatlım, mutfak kombinim ve zeytinyağlı sarma tarifim iki milyon izlendi!", "ses": "gururlu", "sfx": "pop"},
            {"karakter": "OĞUL", "cinsiyet": "erkek", "metin": "Anne ben sana hesabı sadece teyzemlerin fotoğraflarına bak diye açmıştım!", "ses": "suprized", "sfx": "pop"},
            {"karakter": "ANNE", "cinsiyet": "kadin", "metin": "Artık iş birliği olmadan mutfağa girmiyorum, menajerimle konuş.", "ses": "kesin", "sfx": "pop"},
            {"karakter": "OĞUL", "cinsiyet": "erkek", "metin": "Menajerin kim anne, babam içeride televizyon izliyor!", "ses": "sinirli", "sfx": "pop"},
            {"karakter": "ANNE", "cinsiyet": "kadin", "metin": "Baban artık kameramanım, sen de yorumlara alev atmazsan harçlığın kesildi!", "ses": "twist", "sfx": "vine_boom"},
            {"karakter": "OĞUL", "cinsiyet": "erkek", "metin": "Mecbur telefonu elime aldım, profiline girdim...", "ses": "bikeyn", "sfx": "ding"}
        ],
        "sabit_yorum": "Annenizin veya babanızın sosyal medyada yaptığı en komik şey ne? 📱👇",
        "etkilesim": "Ailesi sosyal medya bağımlısı olanlara gönder!"
    }
]

# Yeni içerik evreni: kısa videolar arasında kategori/konu tekrarı azaltılır.
KONU_ACIKLAMALARI = {
    "bar_fikralari": "bar, barmen, müşteri, beklenmedik sipariş ve bar sohbeti; alkol övgüsü veya kullanım yönlendirmesi olmadan",
    "paradoks_hikayeleri": "zaman döngüsü, kendi geleceğiyle konuşma, neden-sonuç paradoksu ve mantık oyunu",
    "absurt_komedi": "gündelik bir eşyanın veya kurumun mantıksız biçimde karakter gibi davranması",
    "absurt_sakalar": "kısa, diyalog odaklı, kelime oyunu ve beklenmedik mantık sıçraması",
    "cilgin_hikayeler": "küçük bir yanlış anlaşılmanın çılgın ama zararsız bir maceraya dönüşmesi",
    "ters_kose_fikralar": "izleyicinin tahminini kuran ve son anda temiz, komik ters köşe yapan fıkra",
    "eglenceli_replikler": "iki özgün karakter arasında akılda kalan, hızlı ve neşeli komik replik düellosu",
    "kulturlar_arasi_mizah": "farklı ülkelerden/şehirlerden karakterlerin nazik gündelik yanlış anlaşılmaları; etnik kökeni, ten rengini veya kimliği hedef almadan",
}

_TEMA_TOHUMLARI = [
    ("bar_fikralari", "neighborhood bar counter", "BARMEN HESABI GELECEĞE KESTİ!", "Bara Gelen Zaman Yolcusu Hesabı Kime Ödetti? 🍹 #shorts", "BARMEN", "MÜŞTERİ",
     ["Bara girdim, barmen hesabı yarına yazdığını söyledi!", "Yarın ödeyeceksin demek, bugün para mı unuttun?", "Hayır, yarınki ben buraya gelip bugünkü hesabı ödeyecek!", "Peki yarınki sen bugünkü seni tanıyor mu?", "Kapı açıldı, içeri geleceğim girdi ve cüzdanımı istedi!", "Barmen ikinize tek hesap çıkardı, zaman yolculuğu indirimi yokmuş!", "Ben de dışarı çıkıp kendimden borç istemeye başladım..."], "Barda duyduğun en tuhaf sipariş neydi? 👇"),
    ("paradoks_hikayeleri", "clock shop time loop", "KENDİME GELECEKTEN MESAJ ATTIM!", "Gelecekteki Ben Geçmişteki Bana Borç Verdi! ⏳ #shorts", "MERT", "GELECEKTEKİ MERT",
     ["Kendime yarından mesaj attım, 'bugün şemsiyeni unut' diyordu!", "Ama hava güneşli, şemsiyeyi niye yanıma alayım?", "Çünkü mesajı yazarken yağmur yağıyordu, ama daha yarın olmadı!", "Demek gelecekteki sen geçmişteki seni uyarıyor, mantıklı!", "Şemsiyeyi aldım, güneş açtı; mesajı da ben göndermişim!", "Gelecekteki ben teşekkür etti, sonra şemsiyeyi benden ödünç aldı!", "Şimdi yarına mesaj yazıyorum: şemsiyeyi geri getir..."], "Bir gün geçmişteki kendine tek cümle yollasan ne derdin? 👇"),
    ("absurt_komedi", "talking printer office", "YAZICI İZİN FORMU İSTEDİ!", "Yazıcı Baskı Yapmayı Reddedip İzin İstedi! 🖨️ #shorts", "ÇALIŞAN", "YAZICI",
     ["Yazıcı bugün çıktı vermedi, önce izin formumu istedi!", "Tonerim bitmiş olabilir, insan kaynaklarına sor!", "Sen makinesin, insan kaynaklarıyla ne işin var?", "Dün gece üç yüz sayfa bastın, fazla mesaim duruyor!", "Formu imzaladım, yazıcı da müdürün masasını bastı!", "Müdür yazıcıyı kovdu, yazıcı şirketin vergi numarasını istedi!", "Şimdi hepimiz çıktı almak için dilekçe yazıyoruz..."], "Sizin evde hangi eşya bir gün konuşsa ilk ne isterdi? 👇"),
    ("absurt_sakalar", "quirky elevator lobby", "ASANSÖR ŞAKAYI CİDDİYE ALDI!", "Asansöre 'Beni Yukarı Taşı' Dedim, Terfi Aldım! 🛗 #shorts", "YOLCU", "ASANSÖR",
     ["Asansöre beni yukarı taşı dedim, özgeçmişimi istedi!", "Kat mı istiyorsun, kariyer basamağı mı?", "Beşinci kata çıkacağım, pazartesi yeni işe başlıyorum!", "O zaman önce üçüncü katta deneme süren var!", "Kapı açıldı, içeride müdürüm yeni asansörümle konuşuyordu!", "Asansör ona 'performansın düşük' dedi, patron merdivene terfi etti!", "Ben de düğmeye bastım, kariyerim zemin kata indi..."], "Asansörle konuşsan ona ilk ne söylerdin? 👇"),
    ("cilgin_hikayeler", "city park runaway parade", "YANLIŞ PAKETLE ŞEHİR TURU!", "Yanlış Paketi Aldım, Belediye Beni Maskot Sandı! 🎈 #shorts", "KURYE", "BELEDİYE GÖREVLİSİ",
     ["Yanlış paketi aldım, bir anda şehrin maskotu ilan edildim!", "Pakette ne vardı, dev bir kostüm mü?", "Hayır, belediyenin kayıp maskot başvurusu ve benim fotoğrafım!", "Fotoğrafın neden başvuruda, sen kurye değil misin?", "Paketleri karıştırmışım, kostümü giyince herkes korteje katıldı!", "Belediye başkanı beni yılın çalışanı seçti, maaşıma havuç ekledi!", "Şimdi gerçek paketi bulmak için geçit törenini yönetiyorum..."], "Yanlış anlaşılmayla başladığınız en komik macera neydi? 👇"),
    ("ters_kose_fikralar", "magic show backstage", "SİHİRBAZ SON NUMARASINI UNUTTU!", "Sihirbaz Şapkadan Tavşan Değil, Fatura Çıkardı! 🎩 #shorts", "SUNUCU", "SİHİRBAZ",
     ["Sihirbaz şapkasından tavşan çıkaracağını söyledi, salon nefesini tuttu!", "Birazdan en büyük numaramla herkesi şaşırtacağım!", "Şapkayı açtı, içinden elektrik faturası çıktı!", "Bu nasıl sihir, tavşan nerede kaldı?", "Tavşan faturayı görünce evden kaçtı, ben de peşinden!", "Meğer tavşan muhasebeciymiş, faturayı sihirbazın cebine saklamış!", "Salon alkışladı, sihirbaz ilk kez gerçekten şaşırdı..."], "En iyi ters köşe fıkranın finali nasıl olmalı? 👇"),
    ("eglenceli_replikler", "colorful cafe witty banter", "İKİ ARKADAŞIN SON SÖZÜ!", "Arkadaşım Motivasyon Verdi, Alarmım İstifa Etti! 😄 #shorts", "DENİZ", "ECE",
     ["Bugün çok üretken olacağım, alarmımı üç kere kurdum!", "Üç alarm mı, kendine güvenin gerçekten etkileyici!", "İlki beni uyandıracak, ikincisi vicdanımı, üçüncüsü komşuyu!", "Peki komşu uyanınca sana ne faydası olacak?", "Beni işe götürecek, çünkü ben yine geç kalacağım!", "Komşu kapıyı açtı, elinde kahve ve istifa dilekçem vardı!", "Motivasyon konuşmamız bitti, şimdi komşunun işine başlıyorum..."], "Sana söylenen en komik motivasyon cümlesi neydi? 👇"),
    ("kulturlar_arasi_mizah", "international food festival friendly mixup", "YEMEK FESTİVALİNDE MENÜ KARIŞTI!", "Dünya Mutfağı Festivali'nde Herkes Yanlış Masaya Oturdu! 🍽️ #shorts", "SUNUCU", "ŞEF",
     ["Festivalde herkes yanlış masaya oturdu, kimse kendi yemeğini bulamadı!", "Menüleri karıştırmış olabiliriz, hangi ülkenin masasındasın?", "Bilmiyorum, üç farklı çorba ve bir tatlı sipariş ettim!", "Hepsi aynı masaya mı geldi, nasıl başardın?", "Masalar ülkelere göre değil, yemeklerin kokusuna göre dizilmiş!", "Şef de yanlış masaya oturdu, yarışma jürisi onu müşteri sandı!", "Sonunda herkes tabağını paylaştı, hesap da ortak çıktı..."], "Bir yemek festivalinde ilk hangi ülkenin mutfağını denersin? 👇"),
]

for kategori, ortam, hook, baslik, karakter_a, karakter_b, metinler, yorum in _TEMA_TOHUMLARI:
    dialogs = []
    for idx, metin in enumerate(metinler):
        dialogs.append({
            "karakter": karakter_a if idx % 2 == 0 else karakter_b,
            "cinsiyet": "erkek" if idx % 2 == 0 else "kadin",
            "metin": metin,
            "ses": "enerjik" if idx == 0 else ("twist" if idx == 5 else "normal"),
            "sfx": "whoosh" if idx == 0 else ("vine_boom" if idx == 5 else ("ding" if idx == 6 else "pop")),
        })
    SENARYO_SABLONLARI.append({
        "kategori": kategori,
        "ortam_etiketi": ortam,
        "ruh_hali": "komedi",
        "hook_ust_bant": hook,
        "baslik": baslik,
        "twist_indeksi": 5,
        "diyaloglar": dialogs,
        "sabit_yorum": yorum,
        "etkilesim": "Bunu gülümseyecek bir arkadaşına gönder!",
    })


def _emoji_temizle(metin: str) -> str:
    return re.sub(
        r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF\uFE0F\u200D]+",
        "",
        str(metin),
    ).strip()


def _tr_upper(metin: str) -> str:
    return str(metin).replace("i", "İ").replace("ı", "I").upper()


def senaryo_dogrula_ve_zenginlestir(ham: dict, video_no: int = 1) -> dict:
    """
    İster Arena AI'dan ister dosyadan gelsin, her senaryoyu v6.0 profesyonel
    loop paketine dönüştürür ve eksik alanları eksiksiz tamamlar.
    """
    kategori = str(ham.get("kategori") or "absurt_komedi").strip()
    ham_diyaloglar = ham.get("diyaloglar") or []

    # Eğer eski format {"satirlar": [...]} geldiyse otomatik 2 karakterli diyaloğa çevir
    if not ham_diyaloglar and isinstance(ham.get("satirlar"), list):
        roller = [("MERT", "erkek"), ("AYŞE", "kadin")]
        for idx, s in enumerate(ham["satirlar"]):
            temiz = re.sub(r"^[^:]{1,18}:\s*", "", str(s)).strip()
            rol, cin = roller[idx % 2]
            eslesme = re.match(r"^([A-ZÇĞİÖŞÜa-zçğıöşü0-9 ]{2,16}):\s*(.+)$", str(s).strip())
            if eslesme:
                rol = eslesme.group(1).strip().upper()
                temiz = eslesme.group(2).strip()
            ham_diyaloglar.append({
                "karakter": rol,
                "cinsiyet": cin,
                "metin": temiz,
                "ses": "enerjik" if idx == 0 else "normal",
            })

    if len(ham_diyaloglar) < 3:
        yedek = random.choice(SENARYO_SABLONLARI)
        return senaryo_dogrula_ve_zenginlestir(yedek, video_no)

    twist_idx = ham.get("twist_indeksi")
    if not isinstance(twist_idx, int) or not (0 <= twist_idx < len(ham_diyaloglar)):
        twist_idx = max(1, len(ham_diyaloglar) - 2)

    islenmis_diyaloglar = []
    for idx, d in enumerate(ham_diyaloglar[:8]):
        karakter = _tr_upper(_emoji_temizle(d.get("karakter", "MERT" if idx % 2 == 0 else "AYŞE")))[:18] or "BOBİ"
        metin = str(d.get("metin", "")).strip()
        if not metin:
            continue
        varsayilan_sfx = "whoosh" if idx == 0 else ("vine_boom" if idx == twist_idx else ("ding" if idx == len(ham_diyaloglar) - 1 else "pop"))
        varsayilan_ses = "twist" if idx == twist_idx else ("enerjik" if idx == 0 else "normal")
        islenmis_diyaloglar.append({
            "karakter": karakter,
            "cinsiyet": d.get("cinsiyet", ""),
            "metin": metin,
            "ses": d.get("ses", varsayilan_ses),
            "sfx": d.get("sfx", varsayilan_sfx),
            "vurgu_kelimeler": d.get("vurgu_kelimeler", []),
        })

    # Gerçek TTS temposu değişebildiği için kısa Arena senaryolarını render öncesi doğal
    # ping-pong replikleriyle uzat; hedef tahmini en az 19 saniyedir.
    tahmin_et = lambda ds: sum(max(1.8, len(d["metin"].split()) * 0.38) for d in ds)
    ek_ciftler = [
        ("Bir dakika, bu hikâyenin en tuhaf kısmı daha başlamadı!", "Daha da mı var, şimdi bütün merakım arttı gerçekten!"),
        ("Peki bu işin sonunda kim haklı çıkacak sence?", "Bekle, finalde bütün hesaplar bir anda değişecek!"),
    ]
    eklenen_cift = 0
    while tahmin_et(islenmis_diyaloglar) < 19.0 and eklenen_cift < len(ek_ciftler) and len(islenmis_diyaloglar) <= 10:
        metin_a, metin_b = ek_ciftler[eklenen_cift]
        ilk_karakter = islenmis_diyaloglar[0]["karakter"] if islenmis_diyaloglar else "MERT"
        ikinci_karakter = next((d["karakter"] for d in islenmis_diyaloglar if d["karakter"] != ilk_karakter), "AYŞE")
        ilk_cinsiyet = islenmis_diyaloglar[0].get("cinsiyet", "erkek") if islenmis_diyaloglar else "erkek"
        ikinci_cinsiyet = next((d.get("cinsiyet", "kadin") for d in islenmis_diyaloglar if d["karakter"] == ikinci_karakter), "kadin")
        ekler = [
            {"karakter": ikinci_karakter, "cinsiyet": ikinci_cinsiyet, "metin": metin_a, "ses": "suprized", "sfx": "pop", "vurgu_kelimeler": []},
            {"karakter": ilk_karakter, "cinsiyet": ilk_cinsiyet, "metin": metin_b, "ses": "enerjik", "sfx": "pop", "vurgu_kelimeler": []},
        ]
        islenmis_diyaloglar[twist_idx:twist_idx] = ekler
        twist_idx += 2
        eklenen_cift += 1

    ilk_metin = _emoji_temizle(islenmis_diyaloglar[0]["metin"])
    hook_ust_bant = _tr_upper(_emoji_temizle(
        ham.get("hook_ust_bant") or ham.get("hook_metni") or ilk_metin[:34]
    ))
    if len(hook_ust_bant) > 38:
        hook_ust_bant = hook_ust_bant[:35].rsplit(" ", 1)[0] + "!"

    baslik = str(ham.get("baslik") or f"{ilk_metin[:48]} 😱 #shorts").strip()
    if "#shorts" not in baslik.lower():
        baslik = f"{baslik[:88]} #shorts"

    tts_metinleri = [d["metin"] for d in islenmis_diyaloglar]
    tahmini_sure = round(tahmin_et(islenmis_diyaloglar), 1)

    return {
        "kategori": kategori,
        "ortam_etiketi": str(ham.get("ortam_etiketi") or "office comedy"),
        "ruh_hali": str(ham.get("ruh_hali") or "komedi"),
        "hook_metni": hook_ust_bant,
        "hook_ust_bant": hook_ust_bant,
        "hook_suresi": 0.0,  # Sıfır ölü hava: ses 0.0 saniyede başlar!
        "twist_indeksi": min(twist_idx, len(islenmis_diyaloglar) - 1),
        "diyaloglar": islenmis_diyaloglar,
        "tts_metinleri": tts_metinleri,
        "punchline_efekt": str(ham.get("punchline_efekt") or "zoom_in"),
        "etkilesim": str(ham.get("etkilesim") or "Bunu yaşayacak arkadaşını etiketle!"),
        "sabit_yorum": str(ham.get("sabit_yorum") or ham.get("aciklama") or "Siz olsanız bu durumda ne yapardınız? Yorumlara yazın 👇"),
        "toplam_sure": tahmini_sure,
        "baslik": baslik,
        "acilis": " ".join(tts_metinleri[:2])[:200],
    }


def arsiv_yukle() -> list:
    if ARSIV_YOLU.exists():
        try:
            return json.loads(ARSIV_YOLU.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _arsiv_kategorisi(kayit: dict) -> str:
    kategori = str(kayit.get("kategori", "")).strip()
    if kategori:
        return kategori
    dosya_adi = str(kayit.get("dosya_adi", ""))
    parcalar = dosya_adi.split("_", 2)
    if len(parcalar) < 3:
        return ""
    aday = parcalar[2]
    if aday.endswith("_arena"):
        aday = aday[:-6]
    return aday


def siradaki_kategori(kategoriler: list[str] | None = None, son_n: int = 6) -> str:
    """Son yayınlarda kullanılan konuları geriye atıp daha az tekrarlanan bir konu seçer."""
    havuz = list(dict.fromkeys(kategoriler or [s["kategori"] for s in SENARYO_SABLONLARI]))
    if not havuz:
        return "absurt_komedi"
    arsiv = arsiv_yukle()
    son_kategoriler = [_arsiv_kategorisi(k) for k in reversed(arsiv) if _arsiv_kategorisi(k)]
    yakin = set(son_kategoriler[:max(1, son_n)])
    adaylar = [k for k in havuz if k not in yakin]
    if not adaylar:
        # Havuzun tamamı yakın zamanda kullanıldıysa, en eski kullanımın önüne geç.
        adaylar = [k for k in havuz if k != son_kategoriler[0]] or havuz
    return random.choice(adaylar)


def senaryo_tekrar_mi(senaryo_ozeti: str, arsiv: list) -> bool:
    ozet_hash = hashlib.md5(senaryo_ozeti[:120].encode("utf-8")).hexdigest()
    return any(k.get("hash") == ozet_hash for k in arsiv)


def kuyruktan_arena_senaryosu_al(video_no: int) -> dict | None:
    """bobi_tv/production/scripts/arena/ altında bekleyen hazır Arena senaryosu varsa alır ve tüketir."""
    if not ARENA_KUYRUK_YOLU.exists():
        return None
    dosyalar = sorted(ARENA_KUYRUK_YOLU.glob("arena_*.json"))
    arsiv = arsiv_yukle()

    for yol in dosyalar:
        try:
            ham = json.loads(yol.read_text(encoding="utf-8"))
            senaryo = senaryo_dogrula_ve_zenginlestir(ham, video_no)
            ozet = " ".join(senaryo["tts_metinleri"])
            yol.unlink(missing_ok=True)
            if not senaryo_tekrar_mi(ozet, arsiv):
                print(f"[Senaryo] Hazır Arena kuyruğundan alındı: {yol.name}")
                return _pakete_sar(senaryo, video_no, kaynak="arena_kuyruk")
        except Exception as e:
            print(f"[Senaryo] Bozuk Arena senaryosu atlandı ({yol.name}): {e}")
            yol.unlink(missing_ok=True)
    return None


def _pakete_sar(senaryo: dict, video_no: int, kaynak: str = "sablon") -> dict:
    tarih = datetime.now().strftime("%Y%m%d")
    dosya_adi = f"{tarih}_{video_no:04d}_{senaryo['kategori']}"
    ozet = " ".join(senaryo["tts_metinleri"])
    ozet_hash = hashlib.md5(ozet[:120].encode("utf-8")).hexdigest()
    senaryo["hash"] = ozet_hash

    paket = {
        "video_no": video_no,
        "dosya_adi": dosya_adi,
        "baslik": senaryo["baslik"],
        "aciklama": senaryo["sabit_yorum"],
        "senaryo": senaryo,
        "kaynak": kaynak,
        "olusturuldu": datetime.now().isoformat(),
        "hash": ozet_hash,
    }
    SENARYO_YOLU.mkdir(parents=True, exist_ok=True)
    (SENARYO_YOLU / f"{dosya_adi}.json").write_text(
        json.dumps(paket, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return paket


def senaryo_paketi_olustur(video_no: int) -> dict:
    """Önce Arena senaryo kuyruğunu kontrol eder, yoksa yerleşik viral loop şablonlarından seçer."""
    kuyruk_paketi = kuyruktan_arena_senaryosu_al(video_no)
    if kuyruk_paketi:
        return kuyruk_paketi

    arsiv = arsiv_yukle()
    kategori_havuzu = list(dict.fromkeys(s["kategori"] for s in SENARYO_SABLONLARI))
    hedef_kategori = siradaki_kategori(kategori_havuzu, son_n=6)
    son_kategoriler = {_arsiv_kategorisi(k) for k in reversed(arsiv[-6:]) if _arsiv_kategorisi(k)}
    rotasyon_havuzu = [k for k in kategori_havuzu if k not in son_kategoriler] or kategori_havuzu
    adaylar = [s for s in SENARYO_SABLONLARI if s["kategori"] in rotasyon_havuzu]
    adaylar.sort(key=lambda s: s["kategori"] != hedef_kategori)
    random.shuffle(adaylar)
    adaylar.sort(key=lambda s: s["kategori"] != hedef_kategori)

    secilen_ham = adaylar[0]
    for sablon in adaylar:
        ozet = " ".join(d["metin"] for d in sablon["diyaloglar"])
        if not senaryo_tekrar_mi(ozet, arsiv):
            secilen_ham = sablon
            break

    senaryo = senaryo_dogrula_ve_zenginlestir(secilen_ham, video_no)
    paket = _pakete_sar(senaryo, video_no, kaynak="yerlesik_v6")
    print(f"[Senaryo] Video #{video_no} hazır: {senaryo['baslik']} (~{senaryo['toplam_sure']}sn)")
    return paket


def gun_senaryolari_uret(hedef: int = 4) -> list:
    return [senaryo_paketi_olustur(i) for i in range(1, hedef + 1)]


if __name__ == "__main__":
    p = senaryo_paketi_olustur(1)
    print(json.dumps(p["senaryo"], ensure_ascii=False, indent=2))
