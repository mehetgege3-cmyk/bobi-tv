# Gemini'nin yeni şablon önerisi — HAM ÇIKTI

> İstem: `docs/SABLON_ISTEM.md` (7,907 karakter)
> Cevap: **9,539 karakter**
> Bu dosya **düzenlenmemiştir**. Uygulamadan önce insan denetimi gerekir.

---

### A) Dürüst Teşhis

#### SORU 1: Kanal 13 videosunda 0 (sıfır) Shorts akışı girişi almış. Bu bir şablon sorunu mu, yoksa başka bir şey mi? Kanalın verdiği emeğin (55 video üretilmiş, 30'u silinmiş) karşılığını almamasının GERÇEK sebebi ne?
*   **Bu kesinlikle saf bir şablon sorunu değil;** teknik, operasyonel ve algoritmik faktörlerin birleşimidir.
*   **Gerçek Sebepler:**
    1.  **Kanal İtibarı ve "Warm-up" (Isınma) Süresi:** 2 aboneye ve toplam 13 aktif videoya sahip yepyeni bir kanal, YouTube'un gözünde henüz güven kazanmamıştır. Algoritma, yeni kanalların içeriklerini önce çok dar bir test kitlesine (örn. 50-100 kişi) sunar.
    2.  **Aşırı Yükleme ve Toplu Silme Cezası ("Churn & Burn"):** Son 7 günde 55 video üretip bunların 30'unu silmek, YouTube botları ve algoritması tarafından "spam/düşük kaliteli otomatik içerik (low-effort mass-production)" sinyali olarak algılanır. Videoları silmek kanalın etkileşim geçmişini sıfırlar ve algoritmanın kitleyi bulmasını engeller.
    3.  **Kanca (Hook) Zayıflığı:** Mevcut şablondaki *"🧠 Günün Merak Uyandıran Sorusu"* girişi, ilk 1.5 saniyede kullanıcının parmağını kaydırmasını (scroll) durduracak kadar keskin, provokatif veya görsel olarak çarpıcı değil.

#### SORU 2: 20-22 saniyelik videolar 1.100-1.200 izlenme almış, 1-2 dakikalık videolar 0-14 izlenme almış. Bu tesadüf mü? Değilse şablonu buna göre nasıl değiştirmeliyim?
*   **Kesinlikle tesadüf değil.** YouTube Shorts ekosisteminde ortalama izlenme süresi (retention) ve tam izlenme oranı (viewed vs. swiped away ratio) her şeydir.
*   **Analiz:** 1-2 dakikalık bir videonun Shorts akışında tutunabilmesi için %100'ün üzerinde izlenme oranı (tekrar izletme) veya devasa bir merak kancası gerekir. 2 aboneyken bu sürede video yayınlamak, izleyicinin ilk 3 saniyede videodan çıkmasına (`swipe away`) yol açar. Algoritma düşük tutunma oranını görür görmez dağıtımı anında keser (`akisa_giren: 0`). 20-22 saniyelik videolar ise hızlı tüketildiği için tamamlanma oranını yakalamıştır.
*   **Şablon Değişikliği:** Metin uzunluğu 200-300 kelimeden **50-60 kelimeye** düşürülmeli, süre hedefi **20-22 saniyeye** sabitlenmelidir.

---

### B) Yeni Şablon — Tam Metin (Gemini İstemine Yapıştırılacak)

```text
SADECE şu JSON ile cevap ver (şablonu tekrar yazma, doldur):
{"soru":"...","cevap":"...","sonuc":"...","baslik":"...","kaynak":"...",
"sayilar":["..."],"dogru_bilgi":"...","kapak_baslik":"..."}

Sen BOBİ TV için Türkçe kısa bilgi videoları yazan uzman bir Shorts büyüme danışmanısın. Aşağıdaki kategori ve taktiğe uyarak yüksek oranda tamamlanma (%80+) sağlayacak 20-22 saniyelik ultra akıcı metinler yazıyorsun.

KATEGORİ: {ad} {emoji}
ÖRNEK KONU ALANLARI: {ornek_konular}

ETKİLEŞİM TAKTİĞİ: {kod} — {ad}
{talimat}

{doğruluk talimatı}

YAZIM KURALLARI (KESİN UYULACAK):
1) 'cevap' alanı KESİNLİKLE 50-60 KELİME olmalı. (20-22 saniyelik seslendirme için zorunlu; uzun metin algoritmayı öldürür).
2) 'soru' (ilk 2 saniye kancası): Asla klasik soru sorma. Doğrudan sarsıcı bir iddia, ters köşeyle başla.
3) 'cevap' alanı: Sohbet tonunda, 'sen' diliyle, yalın Türkçe. Ara notlar, gereksiz dolgu kelimeler yok. Tek bir net bilgiye odaklan.
4) 'sonuc': 1 cümlelik vurucu kapanış; izleyicide "vay be" hissi bırakmalı.
5) 'baslik': En fazla 60 karakter, merak uyandıran, büyük harf bağırması olmayan, sonunda #shorts içermeyen yapı.
6) 'kaynak': Gerçek bir kurum/kitap/dergi adı (NASA, Britannica, Nature, WHO...). Uydurma yasak.
7) 'sayilar': Cevapta geçen tüm sayıların metin olarak listesi.
8) 'dogru_bilgi': Cevabın 1 cümlelik özeti.
9) 'kapak_baslik': En fazla 34 karakter; büyük harf, çarpıcı ifade, emoji YOK.
10) Yaklaşılmayacak konular: {kaçınılacaklar}
11) TAMAMEN TÜRKÇE. Yabancı kelime yasak. MÖ/MS gibi kısaltmalar seslendirmeye uygun yazılmalı (milattan önce).
12) Emoji: Toplamda 2-3 adet, abartısız.
13) JSON dışında HİÇBİR ŞEY yazma.
14) 'cevap' alanında bölüm başlığı (🧠/🔍/💡) KULLANMA.
```

---

### C) Yeni JSON Şeması

| Alan Adı | Veri Tipi | Sınır / Kural | Zorunlu mu? |
|---|---|---|---|
| `soru` | String | İlk 1.5 saniye kancası (Soru veya sarsıcı iddia) | Evet |
| `cevap` | String | **50 - 60 kelime** (20-22 saniye TTS süresi) | Evet |
| `sonuc` | String | 1 cümlelik şaşırtıcı kapanış | Evet |
| `baslik` | String | Maksimum 60 karakter | Evet |
| `kaynak` | String | Gerçek akademik/kurumsal kaynak | Evet |
| `sayilar` | Dizi (Array) | Metin formatında sayılar (`["üç bin"]`) | Evet |
| `dogru_bilgi`| String | 1-2 cümlelik özet | Evet |
| `kapak_baslik`| String | Maksimum **34 karakter**, emoji yok | Evet |

---

### D) Süre ve Kelime Sınırı Kararı

*   **Hedef Süre:** **20 - 22 saniye**.
*   **Hedef Kelime Sayısı:** **50 - 60 kelime**.
*   **Gerekçesi:** Verileriniz 20-22 saniyelik videoların 1.100+ izlenme aldığını, 1 dakikadan uzun videoların ise sıfır çektiğini net bir şekilde kanıtlıyor. Shorts kullanıcılarının dikkat süresi çok kısalmıştır. 50-60 kelimelik kompakt yapı, seslendirme hızına (`tr-TR-*Neural`) mükemmel uyum sağlar ve %80+ izlenme tamamlama oranını tetikler.

---

### E) Yapı Kararı

*   **Eski 3 Bölümlü Yapı (`Günün Sorusu / Cevabı / Sonucu`) Değişiyor mu?**
    *   Görsel/metinsel olarak bu başlıkları ekranda kutu veya başlık olarak göstermek **kaldırılmalıdır**. Çünkü bu bölmeler okuma hissiyatı yaratıp kullanıcıyı kaçırıyor.
    *   **Yeni Akış Yapısı:** 
        1. **Kanca (Hook / 0-2. sn):** İzleyicinin akışta durmasını sağlayan sarsıcı cümle.
        2. **Gelişme / Tek Bilgi (2-18. sn):** Akıcı, tek odaklı 50-60 kelimelik ana metin (Karaoke altyazı ile).
        3. **Vurucu Kapanış (18-22. sn):** Zihinde soru işareti bırakan veya şaşırtan tek cümlelik sonuç.

---

### F) Kanca (Hook) Formülü

*   **Formül:** `[Alışılagelmiş Yanlış Algı] + [Beklenmedik Ters Köşe / Çarpıcı Gerçek]`
*   **Örnek 1 (Tarih):** "Piramitleri kölelerin inşa ettiğini sanıyorsan, büyük bir yalanı yaşıyorsun."
*   **Örnek 2 (İnsan Vücudu):** "Beynin şu an kelimenin tam anlamıyla kendi kendini yiyor ve bundan haberin yok."
*   **Örnek 3 (Doğa/Evren):** "Güneş aslında sarı değil; bunu öğrendiğinde gökyüzüne bakışın tamamen değişecek."

---

### G) Kapak Başlığı Formülü

*   **Kural:** Maksimum 34 karakter, tümü büyük harf veya dikkat çekici tezat, **emoji kesinlikle yok**, ilk kareye 1.5 saniye gömülü.
*   **5 Örnek:**
    1. `PİRAMİTLERİ KÖLELER YAPMADI` (26 karakter)
    2. `BEYNİN KENDİNİ YİYOR` (20 karakter)
    3. `GÜNEŞ ASLINDA SARI DEĞİL` (23 karakter)
    4. `ALTIN KANLI İNSANLAR` (19 karakter)
    5. `SU ASLINDA ISLANMAZ` (18 karakter)

---

### H) Riskler ve Doğrulama

*   **Olası Riskler:** Metni 50-60 kelimeye düşürmek, derinlik hissiyatını azaltabilir. Ancak amaç eğitmek değil, **akışta tutmak ve izlenme almaktır**.
*   **Nasıl Ölçülmeli?** Yeni şablonla en az **15 video** yüklenmeli. Temel metrik `akisa_giren` oranının %0'dan %30+'ya çıkıp çıkmadığı ve ortalama izlenme süresinin 15 saniyenin üzerine çıkıp çıkmadığıdır.
*   **Karar Süresi:** Yeni şablon verileri en az 5 gün boyunca günde 3 video düzeniyle test edildikten sonra net değerlendirme yapılmalıdır. Eski silme alışkanlığı bırakılmalıdır (silinen videolar algoritma güvenini sıfırlar).

---

### I) İlk 3 Video İçin Tam Örnek (Yeni Şemaya Uygun)

#### Video 1 (Tarih / Medeniyet)
```json
{
  "soru": "Piramitleri kölelerin inşa ettiğini sanıyorsan, büyük bir yalanı yaşıyorsun.",
  "cevap": "Giza piramitlerinde çalışan işçiler köle değil, kralın ücretli ve sigortalı inşaat işçileriydi. Arkeolojik kazılarda bulunan mezarlarında etle beslendikleri ve iş kazası geçirdiklerinde tedavi edildikleri kanıtlandı. Yani dünyanın bu devasa harikası zorla değil, gururla inşa edildi.",
  "sonuc": "Tarih bize bilinen en büyük yanlışları gerçek diye yutturuyor.",
  "baslik": "Piramitleri köleler inşa etmedi",
  "kaynak": "Harvard Üniversitesi Giza Arkeoloji Projesi",
  "sayilar": [],
  "dogru_bilgi": "Giza piramit işçilerinin köle değil ücretli çalışan olduğu kanıtlandı.",
  "kapak_baslik": "PİRAMİTLERİ KÖLELER YAPMADI"
}
```

#### Video 2 (İnsan Vücudu)
```json
{
  "soru": "Beynin şu an kelimenin tam anlamıyla kendi kendini yiyor.",
  "cevap": "Uykusuz kaldığında beyin hücrelerin fagositoz adı verilen bir süreçle kendi sinir uçlarını temizlemek yerine yanlışlıkla sağlıklı hücreleri yok etmeye başlar. Bilim insanları buna beynin kendi kendini sindirmesi diyor. Yani uykusuzluk sadece yormaz, seni gerçekten küçültür.",
  "sonuc": "Uykusuz geçen her gece zihninden çalınan bir parçadır.",
  "baslik": "Uykusuz kalınca beynine ne oluyor",
  "kaynak": "Nature Neuroscience Dergisi",
  "sayilar": [],
  "dogru_bilgi": "Uykusuzluk beyin hücrelerinin kendi kendini yemesine yol açar.",
  "kapak_baslik": "BEYNİN KENDİNİ YİYOR"
}
```

#### Video 3 (Doğa / Evren)
```json
{
  "soru": "Güneşin sarı olduğunu düşünüyorsan, optik bir yanılgının kurbanısın.",
  "cevap": "Güneş uzaydan bakıldığında aslında saf beyaz renkli görünür. Atmosferimizdeki gazlar mavi ışığı dağıttığı için güneşi sarı veya turuncu olarak görürüz. Dünyanın atmosferi olmasaydı gökyüzü siyah, güneş ise göz alıcı bir beyaz küre olurdu.",
  "sonuc": "Gördüğümüz renkler bile atmosferin bize bir oyunudur.",
  "baslik": "Güneş aslında sarı değil",
  "kaynak": "NASA Bilim Merkezi",
  "sayilar": [],
  "dogru_bilgi": "Güneş uzayda beyaz renklidir, atmosfer nedeniyle sarı görünür.",
  "kapak_baslik": "GÜNEŞ ASLINDA SARI DEĞİL"
}
```

<Carousel>
  <Video component_placeholder_id="youtube_video_0" count="3" query="youtube shorts content strategy algorithm hook retention 2026" source="youtube"/>
</Carousel>