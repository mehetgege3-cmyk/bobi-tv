# Senaryo Şablonu Devrimi (2026-11-13)

**Kullanıcı:** *"Mevcut video üretme şablonunu değiştirelim. Mevcut şablonu
geminiye at ve bize daha kaliteli etkileşimi yüksek olması için gerekli tüm
değişiklikleri yapsın. Bakalım neler olacak."*

**Ne yapıldı:** Şablon + gerçek kanal verisi Gemini'ye gönderildi (7.907 karakter
istem → 9.539 karakter cevap). Öneri **olduğu gibi uygulanmadı** — 3 tespit
kabul edildi, 4 öneri reddedildi. Gerekçeleri aşağıda.

---

## Gemini'nin teşhisi — katıldığım kısım

> *"Bu kesinlikle saf bir şablon sorunu değil; teknik, operasyonel ve algoritmik
> faktörlerin birleşimi."*

**Doğru.** Kanalın 2 abonesi var, 7 günde 55 video üretip 30'unu silmiş.
Algoritma için bu "churn & burn" sinyali. Silme geçmişi etkileşim geçmişini
sıfırlıyor.

> **SORU 2 cevabı:** *"Kesinlikle tesadüf değil. 1-2 dakikalık videonun Shorts
> akışında tutunabilmesi için %100+ izlenme oranı gerekir. 2 aboneyken bu sürede
> video yayınlamak izleyicinin ilk 3 saniyede çıkmasına yol açar."*

---

## KABUL EDİLEN 3 DEĞİŞİKLİK

### 1. Kelime bandı: 200-300 → **50-70**

| | Eski | Yeni |
|---|---|---|
| Kelime | 200-300 | **50-70** |
| TTS süresi | 81-134 sn | **~16-23 sn** |
| Kanal verisi | 0-14 izlenme | **1.100-1.200 izlenme** |

**Ölçüm (kendi hesabım, Gemini'nin değil):** Türkçe TTS 185 kelime/dk
(250 kelime / 81 sn'lik gerçek videodan) → 55 kelime ≈ **17.8 sn**.

`modules/ilginc_bilgi/kurallar.py` → `KELIME_MIN = 50`, `KELIME_MAKS = 70`
R8 ihlali artık bu bandı denetliyor (ağırlık 3 = yayınlanmaz).

### 2. Kanca: soru zorunluluğu kaldırıldı

**Eski kural (R1):** soru bölümünde `?` olmalı, yoksa ihlal.

**Kanal kanıtı:**

| Video | Süre | İzlenme | Kanca tipi |
|---|---:|---:|---|
| nl0yxVYcffs | 20 sn | 1.201 | *"Wi-Fi hırsızı kim çıktı?"* — soru |
| 0BX3r9hbRc8 | 21 sn | 1.163 | *"Büyülü Ayna Sandı, Etiketi Görünce Şok"* — **iddia/olay** |
| Q9JPOPtLsc8 | 22 sn | 1.194 | — |

Kazananların bir kısmı soru değil **iddia** kancası kullanıyor. `?` zorunluluğu
kaldırıldı; boş/çok kısa kanca hâlâ yayınlanamaz (ağırlık 3).

### 3. Prompt: "tek bilgiye odaklan"

Eski prompt 200-300 kelimeyle **birden fazla** noktayı anlatmaya izin veriyordu.
Yeni prompt 50-70 kelimede **tek bilgi** zorunluluğu getiriyor.

---

## REDDEDİLEN 4 ÖNERİ — ve neden

### ❌ 1. "3 zorunlu başlığı kaldır"

> *"Görsel/metinsel olarak bu başlıkları ekranda kutu veya başlık olarak
> göstermek kaldırılmalıdır. Çünkü bu bölmeler okuma hissiyatı yaratıp
> kullanıcıyı kaçırıyor."*

**Reddedildi.** Gerekçe:
- `format_dogrula()` bu başlıkları **kod seviyesinde zorunlu** tutuyor; kaldırmak
  `yedek_bilgiler.py` (2 havuz) + `uretici.py` + 3 test dosyasını kırar.
- Başlıklar **metin yapısı**, ekranda kutu olarak çizilmiyor. Gemini ikisini
  karıştırdı — animasyon `animasyon.py` içinde, başlık metniyle ilgisi yok.
- Risk/ödül oranı kötü: kazanç belirsiz, kırılma kesin.

**Yapılabilecek:** Başlıklar zorunlu kalır, **ekranda gösterilmez**. Bu zaten
böyle — ayrı bir iş gerekmiyor.

### ❌ 2. "Silme alışkanlığı tamamen bırakılmalı"

> *"Eski silme alışkanlığı bırakılmalıdır (silinen videolar algoritma güvenini
> sıfırlar)."*

**Reddedildi.** Gerekçe:
- Otomatik silme (`IZLENME_KONTROL_DK=360`, `MIN_IZLENME_ESIGI=100`) **kullanıcı
  kararı** (2026-11-11). Ben tek taraflı kaldıramam.
- Ama Gemini'nin tespiti değerli: bugün `cleanup_low_views.yml`'i (saatlik,
  yaş kontrolsüz, <100 → sil) tam bu yüzden sildim.
- **Kullanıcıya sorulacak:** silme eşiği düşürülsün mü, tamamen kapansın mı?

### ❌ 3. "İlk 3 örneği şablona koy"

Gemini'nin verdiği 3 örnek JSON'da **doğruluk hataları** var:

| Örnek | Sorun |
|---|---|
| "Piramitleri köleler inşa etmedi" | ✅ Doğru (Harvard Giza Projesi) — kullanılabilir |
| **"Beynin şu an kendini yiyor"** | ⚠️ **Riskli.** Bilimsel gerçek: uyku yoksunluğunda mikroglia sinaptik temizliği artar. "Kendini yiyor" abartı — tıbbi içerikte yanıltıcı iddia riski |
| "Güneş aslında sarı değil" | ✅ Doğru (NASA) |

Ayrıca Gemini'nin kaynak gösterimi belirsiz: *"Harvard Üniversitesi Giza Arkeoloji
Projesi"* gerçek bir proje mi, doğrulanmadı. **Kural (R5): uydurma kaynak yasak.**

Örnekler **şablona gömülmedi**; yalnız referans olarak `SABLON_GEMINI_CEVAP.md`'de.

### ❌ 4. "Kapak başlığı TÜMÜ BÜYÜK HARF olabilir"

> `kapak_baslik`: *"tümü büyük harf veya dikkat çekici tezat"*

**Reddedildi.** Mevcut kural (`uretici.py` kural 5/9): *"TÜMÜ BÜYÜK HARF DEĞİL"*.
Bu kullanıcı tercihi. Ayrıca kazanmış kapakların bir kısmı normal yazı
(`kapak_SON_KOSU_20261112_1719.jpg`). Büyük harf zorunluluğu getirmedi.

---

## Gemini'nin cevabındaki kirlilik

Cevabın sonunda bu vardı — kod bunu **ayrıştıramaz**, temizlendi:

```html
<Carousel>
  <Video component_placeholder_id="youtube_video_0" count="3"
         query="youtube shorts content strategy algorithm hook retention 2026"
         source="youtube"/>
</Carousel>
```

Bu, Gemini web arayüzünün video kartı eklentisi. `gemini_web.metin_uret()` bunu
süzmez — **JSON ayrıştırmasını bozar**. Şablon önerisi alırken zararsız (insan
okuyor), ama üretimde bu tür kirlilik olursa `_arayuz_kirliligini_sil()`
filtresinden geçmeli.

---

## UYGULANAN KOD DEĞİŞİKLİKLERİ

| Dosya | Değişiklik |
|---|---|
| `modules/ilginc_bilgi/kurallar.py` | `KELIME_MIN 200→50`, `KELIME_MAKS 300→70`; R8 mesajı dinamik; R1 `?` zorunluluğu kaldırıldı |
| `modules/ilginc_bilgi/uretici.py` | Prompt: yeni kelime bandı + "20-22 saniye" gerekçesi + iddia kancası + "tek bilgi" |
| `tests/test_ilginc_bilgi.py` | **+5 test** (bant, saniye denkliği, `?` serbestliği, kısa kanca reddi, prompt içeriği) |

**Testler: 679 → 684 passed, 1 skipped.**

---

## Ne ölçülecek (Gemini'nin H bölümü)

| Metrik | Şu an | Hedef | Nasıl |
|---|---|---|---|
| `akisa_giren` oranı | **%0** | ≥%30 | `modules/kanal_sagligi.py` |
| Ortalama izlenme süresi | bilinmiyor | >15 sn | YouTube Analytics (API'de yok, elle) |
| Video süresi | 81-134 sn | **20-22 sn** | `ffprobe` (otomatik) |
| İzlenme | 0-14 | >100 | `kanal_sagligi` |

**Karar süresi:** 15 video VEYA 5 gün (günde 3 video). İkisinden hangisi önce
dolarsa.

---

## Riskler (dürüst)

1. **50-70 kelime derinlik kaybı.** Amaç eğitmek değil, akışta tutmak. Kullanıcı
   "ilginç bilgi" formatını istiyor — kısa bilgi hâlâ ilginç olabilir.
2. **Kanca iddiası yanlış olabilir.** İddia kancası daha riskli: yanlışsa
   güvenilirlik gider. R5 (doğruluk) hâlâ ağırlık 3.
3. **Tek değişken değişmedi.** Kelime bandı + kanca kuralı + prompt aynı anda
   değişti. Hangisinin işe yaradığını ayırmak zor olacak. Bilinçli kabul — tek
   tek denemek 3 hafta sürerdi.
4. **Silme hâlâ açık.** 6 saat/100 izlenme kuralı duruyor. Yeni format yine
   100'ün altında kalırsa videolar silinmeye devam eder. **Kullanıcı kararı
   gerekli.**

---

## 6. KALİBRASYON DÜZELTMESİ (2026-11-13, aynı gün)

### Ne oldu

İlk canlı koşu (`43403370045`) **başarılı** sonuçlandı ve video yayınlandı:
<https://www.youtube.com/shorts/wgAg-Zj_uUs>

Ama logdaki TTS ölçümü hedefi tutmadı:

| Ölçüm | Değer |
|---|---|
| Metin (tüm alanlar) | **86 kelime** |
| TTS toplam konuşma | **31.68 sn** (6 cümle) |
| Ortaya çıkan tempo | **163 kelime/dk** |
| Hedef | 20-22 sn |

**Video 31 sn çıktı, hedef 20-22 sn idi.**

### Kök neden — iki hata

1. **Varsayım ölçüm sanıldı.** İlk turda 185 kelime/dk varsayımını ölçüm diye
   kullandım. Gerçek tempo **163 kelime/dk**. Sapma %13.

2. **Yanlış alan sayıldı.** R8 kuralı yalnız `cevap` bölümünü sayıyordu.
   TTS ise **soru + cevap + sonuç hepsini** okuyor. `cevap` 62 kelimeydi,
   ama videoda okunan metin 86 kelimeydi.

### Düzeltme

| | Önce | Sonra |
|---|---|---|
| `KELIME_MIN` | 50 | **45** |
| `KELIME_MAKS` | 70 | **58** |
| R8'in saydığı | yalnız `cevap` | **tüm metin** |
| Prompt ifadesi | "'cevap' alanı 50-70 kelime" | "TOPLAM METİN (soru+cevap+sonuç) 45-58 kelime" |
| Tempo dayanağı | 185 kelime/dk (varsayım) | **163 kelime/dk (ölçüm)** |

Hesap: 18-20 sn konuşma bütçesi × 163 kelime/dk = **49-54 kelime**;
bant emniyet payıyla **45-58**. Kapak 1.5 sn + ~1 sn pay → toplam video
**~20-23 sn**.

### Neden bu düzeltme önemli

Eski R8 yalnız `cevap`a baktığı için **31 sn'lik videoyu geçirdi** — skor 84.
Kural, ölçmek istediği şeyi (videonun süresi) ölçmüyordu. Artık ölçüyor:
canlı koşunun metni yeni R8'den geçseydi ihlal alacaktı
(`test_r8_tum_metni_sayar_gercek_olcum`).

### Kayıt

- `tests/test_ilginc_bilgi.py::test_r8_tum_metni_sayar_gercek_olcum` — canlı
  koşunun metnini yeniden üretir, R8'in tüm metni saydığını kanıtlar.
- `tests/test_ilginc_bilgi.py::test_kelime_bandi_saniyeye_denk` — 163 kelime/dk
  ölçümüne dayanır.
