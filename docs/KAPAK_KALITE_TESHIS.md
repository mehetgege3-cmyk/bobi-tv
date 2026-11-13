# KAPAK NEDEN AMATÖR GÖRÜNÜYOR — teşhis

**Kullanıcı (2026-11-13):** *"Gerizekalı çok amatörce görünüyor, sana verdiğim
promtu incele."*

Bu doküman tahmin değil **ölçüm** içerir. Kanıt görselleri `kanit/2026-11/`.

---

## 1. Ölçülen sorun #1 — kapağın %68'i YouTube'un blur dolgusuydu ✅ ÇÖZÜLDÜ

YouTube kapak alanı **16:9** (1280×720). Ben motorda kapağı **1080×1920 (9:16)**
zorluyordum. YouTube 9:16 görseli 16:9 alana oturturken yanlara kendi bulanık
dolgusunu ekliyor.

`maxresdefault.jpg` indirilip piksel analizi yapıldı:

| | Önce | Sonra |
|---|---|---|
| Net (gerçek görsel) alan | **405 px / 1280 (%32)** | **1275 px / 1280 (%100)** |
| Blur dolgu | 875 px | 5 px |

`720 × 9/16 = 405` — yani 9:16 gönderdiğim matematiksel olarak doğrulandı.

**Düzeltme:** `kapak_olcekle()` → 1280×720. Doğrulama artık 16:9 olmayan kapağı
reddediyor (`tools/motor_dogrula.py`).

Kanıt: `kanit/2026-11/kapak_oncesi_9x16.jpg` → `kapak_sonrasi_16x9.jpg`

---

## 2. Ölçülen sorun #2 — video karesi ile kapak ALÂKASIZ ❗ AÇIK

Aynı video (`rpeNeu67VTk`) için:

| | İçerik |
|---|---|
| **Video karesi** (3. saniye) | Gece komodini, bir bardak su, eller — sakin, sıcak ışık |
| **Kapak** | Patlayan kristal mağara + dehşet içinde elini yüzüne götürmüş adam |

İkisi **aynı videoya ait değil gibi** duruyor. Sebep: kapak Gemini'ye AYRI bir
istekle üretiliyor, video arka planı ise BAŞKA bir istekle. İki çağrı birbirini
görmüyor.

### Neden bu "amatör" hissi veriyor
1. **Tutarsızlık** — izleyici küçük resme tıklıyor, bambaşka bir şey buluyor.
   Bu, "kapağı izlenme için tıklat, içeriği umursama" görüntüsü veriyor.
2. **Jenerik AI kalıbı** — açık ağız, el yüzde, patlayan ışıklar: 2026'da
   milyonlarca kanalın kullandığı şablon. Kanal kimliği yok.
3. **Yazı yok** — kapakta hiç metin yok. Shorts rafında küçük görünüyor,
   okunacak bir kanca yok.

---

## 3. Kullanıcının istemi ne diyor, ben ne yaptım

Kullanıcının şablonu (K8 — **birebir** kullanılmalı):

```
<başlık> İsimli short video için kapak fotoğrafı istiyorum; etkileşim ve
izlenme rekorları kırması için profesyonel şekilde tasarla. Kapak fotoğrafını
gören merak edip tıklasın.
```

| İstem parçası | Yaptığım | Doğru mu |
|---|---|---|
| "etkileşim ve izlenme rekorları kırması için" | tutuldu | ✅ |
| "profesyonel şekilde tasarla" | Gemini'nin yorumuna bırakıldı | ⚠️ denetlenmedi |
| "gören merak edip tıklasın" | tutuldu | ⚠️ merak = clickbait'e kaydı |
| (yazılı mı yazısız mı?) | istemde yok — ben "yazı yazma" EKLEDİM | ❌ **ben ekledim, istemde yok** |

**Hata:** İsteme "Yazı yazma, sadece görsel olsun" satırını ben ekledim.
Kullanıcı bunu istemedi. Kapakta kanca metni olmaması doğrudan bunun sonucu.

---

## 4. Yapılması gerekenler (karar bekliyor)

1. **Yazı geri gelsin mi?** Kapakta 3-5 kelimelik kanca metni (ör. "BU SU 200
   MİLYON YIL YAŞINDA"). Shorts rafında okunabilirlik için kritik.
   → İstemden "yazı yazma" satırı çıkarılmalı.
2. **Kapak ile video aynı sahne olsun mu?** İki seçenek:
   - a) Kapak = videonun ilk karesinin büyütülmüş hâli + yazı → **tutarlı**
   - b) Ayrı kapak kalsın ama aynı konuyu somut göstersin (dehşet yüzü değil)
3. **Jenerik "AI şoku" yüzü yasaklansın mı?** Açık ağız/el yüzde kalıbı.

**Bu üç karar kullanıcının. Ben tek başıma seçmiyorum** — çünkü 2. maddede
zaten yanlış varsayım yapıp isteme kendi kuralımı ekledim.
