Sen YouTube Shorts algoritması ve Türkçe içerik üretimi konusunda uzman bir
büyüme danışmanısın. Sana bir kanalın MEVCUT senaryo şablonunu, gerçek performans
verilerini ve kısıtlarını veriyorum.

GÖREVİN: Mevcut şablonu **yeniden yaz**. Daha kaliteli ve etkileşimi yüksek
olması için ne gerekiyorsa yap. Ama önce şu iki soruyu dürüstçe cevapla:

**SORU 1:** Kanal 13 videosunda 0 (sıfır) Shorts akışı girişi almış. Bu bir
şablon sorunu mu, yoksa başka bir şey mi? Kanalın verdiği emeğin (55 video
üretilmiş, 30'u silinmiş) karşılığını almamasının GERÇEK sebebi ne?

**SORU 2:** 20-22 saniyelik videolar 1.100-1.200 izlenme almış, 1-2 dakikalık
videolar 0-14 izlenme almış. Bu tesadüf mü? Değilse şablonu buna göre nasıl
değiştirmeliyim?

---

## MEVCUT DURUM (ölçülmüş, uydurma değil)

### Kanal
- **BOBİ TV** (UCJzCURUGVP3-baKe7N9FNjw)
- 13 video · 2 abone · 6.136 toplam izlenme
- Son 7 gün: 55 video üretildi, **30'u silindi**, ortalama izlenme **6.88**, medyan **0**
- **`akisa_giren: 0` — Shorts akışına giriş oranı %0**
- Kanalın kendi ölçüm yorumu: *"🔴 akışa giriş yok — algoritma hâlâ dağıtmıyor;
  içerik/kanca gözden geçir"*

### Ne işe yarıyor, ne yaramıyor (gerçek veri)

| Video | Süre | İzlenme | Format |
|---|---:|---:|---|
| iWf-rI1cTBk | 22 sn | **1.125** | kısa, tek bilgi |
| nl0yxVYcffs | 20 sn | **1.201** | kısa, tek bilgi |
| Q9JPOPtLsc8 | 22 sn | **1.194** | kısa, tek bilgi |
| uJfHjbpQOOE | 22 sn | **1.187** | kısa, tek bilgi |
| 0BX3r9hbRc8 | 21 sn | **1.163** | kısa, tek bilgi |
| pjUkuq4dPEo | 5 sn | 257 | çok kısa |
| eaIy0nXb7mI | 1 dk 21 sn | **14** | uzun anlatım |
| 5JmkCDxndVM | 1 dk 27 sn | **12** | uzun anlatım |
| NjywOjPzLE0 | 1 dk 42 sn | **2** | uzun anlatım |
| MO1QOKxr4NQ | 1 dk 42 sn | **1** | uzun anlatım |
| pQOvBWcegNc | 1 dk 31 sn | **0** | uzun anlatım |
| EQPd1GlVCMw | 2 dk 14 sn | **0** | uzun anlatım |

**Desen:** 20-22 sn = 1.100+ izlenme. 1-2 dk = 0-14 izlenme. **Ters orantı.**

### Mevcut üretim hattı
- 1080×1920 · 30 fps · H.264 + AAC
- Çift ses: `tr-TR-AhmetNeural` (erkek) + `tr-TR-EmelNeural` (kadın)
- Kutulu karaoke altyazı (kelime kelime vurgu)
- SFX: whoosh, pop, vine_boom, riser, ding
- Sidechain BGM, çıkış −14 LUFS
- Kapak: Gemini'den üretilen görsel, ilk kareye 1.5 sn gömülü
- Yayın: günde 3 (8 saatte bir)

### 8 kategori (rotasyonlu, son 6 geriye atılır)
`bilim_teknoloji` · `tarih_medeniyet` · `doga_evren` · `hayvanlar` ·
`insan_vucudu` · `yiyecekler` · `kulturler` · `gunluk_yasam`

### 7 etkileşim taktiği (kod rotasyonu: video_no mod 10)
- **T1** yaygın yanlış inanış (çürütme)
- **T2** cevabı boşluk bırak, sonda kapat
- **T3** sürçme + aynı videoda düzeltme *(sağlık/para/güvenlik kategorilerinde YASAK)*
- **T4** ters psikoloji *(sağlık/para/güvenlik kategorilerinde YASAK)*
- **T5** paradoksal gerçek
- **T6** iki cevap / hangisi doğru
- **T7** düzeltme videosu / sabitlenmiş yorum

---

## MEVCUT ŞABLON (Gemini'ye giden istem, birebir)

```
SADECE şu JSON ile cevap ver (şablonu tekrar yazma, doldur):
{"soru":"...","cevap":"...","sonuc":"...","baslik":"...","kaynak":"...",
"sayilar":["..."],"dogru_bilgi":"...","kapak_baslik":"..."}

Sen BOBİ TV için Türkçe kısa bilgi videoları yazan bir editörsün. YouTube
Shorts için 'ilginç bilgi' içeriği üretiyorsun. Aşağıdaki kategori ve taktiğe uy.

KATEGORİ: {ad} {emoji}
ÖRNEK KONU ALANLARI: {ornek_konular}

ETKİLEŞİM TAKTİĞİ: {kod} — {ad}
{talimat}

{doğruluk talimatı}

YAZIM KURALLARI:
1) 'cevap' alanı 200-300 KELİME olmalı (ne az ne çok).
2) 'soru' merak uyandıran, tek cümlelik bir soru; cevabı içermez.
3) 'cevap' sohbet tonunda, 'sen' diliyle, sade Türkçe. İçinde günlük hayattan
   somut bir örnek/karşılaştırma olsun.
4) 'sonuc' 1-2 cümlelik şaşırtıcı kapanış; cevabı özetler.
5) 'baslik' en fazla 70 karakter, merak uyandıran, TÜMÜ BÜYÜK HARF DEĞİL,
   sonunda '#shorts' yok.
6) 'kaynak' gerçek bir kurum/kitap/dergi adı (NASA, Britannica, Nature, WHO,
   National Geographic...). Uydurma.
7) 'sayilar' cevapta geçen tüm sayıların listesi (metin olarak).
8) 'dogru_bilgi' cevabın 1-2 cümlelik ÖZETİ (yorum cevaplarında kullanılacak).
9) 'kapak_baslik' en fazla 34 karakter; çarpıcı ifade; EMOJI YOK.
10) Şu konulara YAKLAŞMA (daha önce yapıldı): {kaçınılacaklar}
11) TAMAMEN TÜRKÇE. İngilizce kelime yok.
12) Emoji kullan ama abartma (2-5 arası).
13) JSON dışında HİÇBİR ŞEY yazma; şablonu yankılama.
14) 'cevap' alanında bölüm başlığı (🧠/🔍/💡) KULLANMA; sadece metin yaz.
```

### Mevcut şablonun dayattığı zorunlu yapı

Video tam olarak bu 3 başlıkla bölünmek zorunda (kod denetliyor, eksikse yayınlanmaz):

```
🧠 Günün Merak Uyandıran Sorusu
🔍 Cevabı Biliyor Muydun?      ← 200-300 kelime (ZORUNLU)
💡 Şaşırtıcı Sonuç
```

### Mevcut şablonun 12 kuralı (kod seviyesinde denetleniyor)

| Kod | Kural | Ağırlık |
|---|---|---|
| R1 | Soru ile başla, '?' olmalı | 3 = yayınlanmaz |
| R2 | Cevabı hemen verme | 3 |
| R3 | Sohbet tonu, 'sen' dili | 2 |
| R4 | Az bilinen bilgi (klişe yok) | 1 |
| R5 | Doğruluk (kaynak + sayı doğrulama) | 3 |
| R6 | Önceki konuları tekrar etme (%55 örtüşme) | 3 |
| R7 | Kategori geçişi (son 4'te olmasın) | 2 |
| R8 | **200-300 kelime** | 3 |
| R9 | Günlük hayat örneği | 2 |
| R10 | Sade Türkçe (cümle ort. <26 kelime) | 2 |
| R11 | Emoji (2-12 arası) | 1 |
| R12 | Tamamen Türkçe | 3 |

---

## KISITLAR — bunlara UYMAK ZORUNDASIN

1. **Çıktı JSON olmalı.** Kod `json` ile ayrıştırıyor. Serbest metin verirsen
   üretim çöker.

2. **Mevcut JSON alan adlarını koru** ya da yeni alan eklersen hangisinin
   zorunlu olduğunu açıkça söyle:
   `soru`, `cevap`, `sonuc`, `baslik`, `kaynak`, `sayilar`, `dogru_bilgi`,
   `kapak_baslik`

3. **Doğruluk kuralı pazarlık dışı.** Uydurma bilgi, uydurma kaynak, abartılı
   sayı YASAK. Kanalın güvenilirliği buna bağlı. Emin olmadığın bir iddiayı
   şablona koyma.

4. **Türkçe olmalı.** İngilizce kelime geçemez.

5. **Seslendirme ile okunacak.** Yazdığın metin TTS ile sese çevrilecek.
   Telaffuz edilemeyen kısaltma, sembol, tarih formatı kullanma.
   (Örn: "MÖ 3000" → "milattan önce üç bin")

6. **Karaoke altyazı ile senkron olacak.** Çok uzun cümle görsel olarak sığmaz.
   Cümle başına azami ~20 kelime.

7. **Tek video = tek bilgi.** Mevcut şablon 200-300 kelime istiyor ama veri
   20-22 saniyenin (yaklaşık 50-60 kelime) 100 kat daha iyi performans
   gösterdiğini söylüyor. Bu çelişkiyi çöz.

8. **Sağlık/para/güvenlik kategorilerinde** T3 (sürçme) ve T4 (ters psikoloji)
   yasak — YouTube "deceptive practices" riski. Şablon bunu kodda denetliyor.

---

## SENDEN İSTEDİĞİM ÇIKTI

Şu sırayla yaz:

### A) Dürüst teşhis
Soru 1 ve Soru 2'ye net cevap. Şablonu suçlamadan önce, şablon dışındaki
sebepleri de söyle (yeni kanal, 2 abone, yükleme-silme geçmişi, kanal itibarı,
algoritma ısınma süresi). **Abartma, gerçekçi ol.**

### B) Yeni şablon — tam metin
Gemini'ye gönderilecek istemin **tam yeni halini** yaz. Kopyala-yapıştır
kullanılabilir olsun. Değişikliklerin nedenini her satırın yanına kısa not
olarak ekle.

### C) Yeni JSON şeması
Alanlar, tipler, karakter/kelime sınırları, hangisi zorunlu.

### D) Süre kararı
Kaç saniye hedeflemeliyim? Kaç kelime? Gerekçesiyle.

### E) Yapı kararı
3 bölümlü yapı (soru/cevap/sonuç) kalsın mı, değişsin mi? Yeni yapıyı yaz.

### F) Kanca (hook) formülü
İlk 1.5 saniyede ne olmalı? Somut formül + 3 örnek (Türkçe).

### G) Kapak başlığı formülü
`kapak_baslik` alanı 34 karakterle sınırlı. Yeni kural ne olmalı? 5 örnek.

### H) Riskler
Yeni şablonun neyi bozabileceğini söyle. Neyi ölçerek doğrulamalıyım?
Kaç video sonra karar vermeliyim?

### I) İlk 3 video için tam örnek
Yeni şablonla üretilmiş, **gerçek ve doğrulanabilir** 3 bilgi. Her biri
JSON formatında, yeni şemaya tam uygun. (Bunlar şablonun testi olacak.)

---

**ÖNEMLİ:** Bana genel geçer tavsiye verme ("ilgi çekici ol", "merak uyandır"
gibi). Somut, ölçülebilir, kodlanabilir kurallar ver. Kanalın gerçek verisine
dayan. Emin olmadığın yerde "bilmiyorum" de.
