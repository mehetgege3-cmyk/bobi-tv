# NotebookLM Video Üretimi — HAR İncelemesi

Kaynak: `1.md` (aslında ZIP) → içinden `1.har` çıktı.
**337 kayıt · 2026-11-15 16:32:35 → 16:46:18 (13 dk 43 sn) · 65 `batchexecute`**

Eski küçük HAR (`notebook.google.com_...20_03_28.har`, 76 kayıt) ile aynı oturumun
devamı — ama **video üretimi sadece bu büyük HAR'da var**.

---

## 1. Video gerçekten var

| | |
|---|---|
| Dosya | `Suda_Buruşan_Parmakların_Sırrı.mp4` |
| Boyut | **8.770.224 bayt** (8.4 MB) |
| Süre | **75,23 saniye** (1 dk 15 sn) |
| Format | `video/mp4`, `itag=22` = **H.264 720p + AAC ses** |
| Kaynak | `source=contrib_service_notebooklm` |

`itag=22` olması iyi haber: tek dosya, video+ses muxlanmış. Ayrı ses indirmeye gerek yok.

---

## 2. İndirme zinciri — 5 adım, hepsi 302

```
lh3.googleusercontent.com/notebooklm/ABzcPv1H0yGSLggiLYxS0...
  → 302 → lh3.google.com/rd-notebooklm/ABzcPv0yPhVUywjj9ZM7...
  → 302 → lh3.googleusercontent.com/rd-notebooklm/ABzcPv0lTaooqEQoM...
  → 302 → rr4---sn-nv47lnsy.googlevideo.com/videoplayback?itag=22...
  → 302 → rr3---sn-4g5ednrz.googlevideo.com/videoplayback   ← 206, video/mp4
```

İkinci zincir (indirme düğmesi):
```
.../rd-notebooklm/ABzcPv0fAotAlSOV5IDTMsSDfJsOp...
  → 302 → drum.usercontent.google.com/download/AP4vrRGrF-USqLvIIKyzzKd...
```

`drum` yanıtı doğrudan indirme veriyor, `Content-Disposition` header'ı ile:
```
attachment; filename="Suda_Buruşan_Parmakların_Sırrı.mp4"
```

**Önemli:** `googlevideo` URL'leri **IP'ye kilitli** (`ip=195.174.125.175`) ve
`expire=1794768345` (≈ 2 saat) süreli. GitHub runner'ın IP'si farklı olacağı için
**HAR'daki URL'ler doğrudan kullanılamaz**. Ama `lh3.googleusercontent.com/...`
URL'i **imzalı token** taşıyor ve IP'ye kilitli değil — her seferinde yeni 302
zinciri üretiyor. **Kalıcı yol bu.**

---

## 3. Video'yu başlatan RPC: `R7cb6c`

**16:34:42.962Z** — defter açıldıktan 2 dakika sonra, tek çağrı.

```
f.req = [[["R7cb6c","[[2,null,null,[1,null,null,null,null,null,null,null,null,null,[1]],
        [[1,25,4,8,10,14,2,3,6]]],\"<DEFTER_ID>\",
        [null,null,3,[[null,null,null,null,null,null,[\"<ARTIFACT_ID>\",2]]],
        null,null,null,null,[null,null,[[[\"<ARTIFACT_ID>\"]],\"tr\",\"\",null,4,null,null,1]]]]",
        null,"generic"]]]
```

Yanıt — yeni **artifact id** üretiyor:
```
["0187d808-2d86-4f8b-8233-cfbde5d1a6be", "Parmaklarımız Neden Buruşur?", 3, ..., 2, ...]
```
Bu id sonraki tüm yoklamalarda kullanılıyor. **Bu yüzden `R7cb6c` = "Video Overview üret".**

---

## 4. İlerleme takibi: `gArtLc` yoklaması

Video üretimi asenkron. `gArtLc` (artifact durum sorgusu) periyodik atılıyor:

| Saat | Yanıt boyutu | Durum |
|---|---|---|
| 16:32:45 | 107 krkt | `[]` — henüz artifact yok |
| 16:32:46 | 107 krkt | `[]` |
| 16:34:42 | — | **`R7cb6c` → video üretimi başladı** |
| 16:34:43–16:35:23 | 608–610 krkt | kayıt var, **video URL'i yok** |
| 16:37:20 | 606 krkt | hâlâ yok |
| 16:41:48 | 611 krkt | hâlâ yok |
| **16:42:55** | **1962 krkt** | ✅ **video hazır — 4 URL + süre 75 sn** |
| 16:43:13 | 1962 krkt | hazır |
| 16:44:06 | 1964 krkt | hazır |
| 16:46:08 | — | **indirme başladı** |

**Üretim süresi: 16:34:42 → 16:42:55 = 8 dakika 13 saniye.**

Yanıt 107 krkt'tan 1962 krkt'a sıçradığı anda video hazır — yani yoklama
`wrb.fr` yükünün **boyutuna** bakarak durumu anlayabilir, ayrı bir durum kodu yok.

---

## 5. Hazır yanıtındaki yapı (indeksler)

`gArtLc` yükü = `[[id, baslik, 3, [...artifact_refs...], DURUM, ..., medya_bilgisi, ...]]`

| İndeks | İçerik |
|---|---|
| 0 | artifact id (video) `0187d808-...` |
| 1 | başlık `Suda Buruşan Parmakların Sırrı` |
| 4 | **durum: 2 = üretiliyor, 3 = hazır** |
| 8 | medya dizisi |
| 8[1] | `lh3.../ABzc...mm,22` — **ana video URL** |
| 8[2] | `...,m22-dv` — alternatif |
| 8[3] | 4 alternatif: `,22` `,hls` `,dash` `,m22-dv` |
| 9 | `[75, 167000000]` → **süre 75 sn** |
| 12 | `[1794760975, ...]` üretim bitiş zamanı |
| 14 | `[1794760483, ...]` üretim başlangıç zamanı |
| 18 | base64 zaman damgası |

Durum alanı **4** net: `2` = üretiliyor, `3` = hazır. Bu doğrudan okunabilir,
boyut tahminine gerek yok.

---

## 6. Ne YOK — ve bu önemli

HAR'da **video üretim ayarları** (stil, dil, uzunluk, "Cinematic"/"Explainer" seçimi)
için hiçbir çağrı yok. `R7cb6c`'nin yükünde `3` var (muhtemelen format tipi) ve
`"tr"` (dil). Yani:

- **Dil kontrol edilebiliyor:** `"tr"` alanı var.
- **Stil/uzunluk:** HAR'da kanıt yok. Arayüzde seçim yapılmamış olabilir, ya da
  varsayılan kullanılmış.

Ayrıca **`sqTeoe` yanıtı bu hesapta Video Overview seçeneğini listelemiyor** —
sadece "Ayrıntılı inceleme, Özet, Eleştiri, Tartışma", "Açıklayıcı, Özet, Kısa",
"Ayrıntılı Sunu, Sunucu Slaytları" ve "Özet Belgesi, Çalışma Kılavuzu, Blog Yayını"
var. Yani **video yeteneği bu hesap için açık görünmüyor** ama video üretilmiş.

Bu çelişkiyi çözemedim. Muhtemelen video özelliği kademeli açılıyor ve menü listesi
geriden geliyor.

---

## 7. Özet tablo — kullanılacak RPC'ler

| RPC | İş | Kanıt |
|---|---|---|
| `R7cb6c` | **Video Overview üret (başlat)** | artifact id döndü |
| `gArtLc` | **Üretim durumu yokla + video URL al** | 107 → 1962 krkt sıçraması |
| `rLM1Ne` | Defter başlığı, emoji, kaynak listesi | ✅ |
| `cFji9` | Metin artifact'ını oku | 2.262 krkt Türkçe metin |
| `otmP3b` | Başlıktan alt konu üret | 3 alt konu |
| `VfAZjd` | Sohbet özeti + önerilen sorular | ✅ |
| `hPTbtc` | Kaynak kimlikleri | ✅ |
| `EylDcb` | Kota / kullanım | ✅ |

---

## 8. Açık kalan sorular

1. **`R7cb6c` yükündeki `3` ne?** Video format tipi mi, uzunluk mu? Değiştirilirse
   ne olur — denenmeden bilinmez.
2. **Video neden menüde yok ama üretildi?** Kademeli açılış mı, yoksa HAR'daki
   `sqTeoe` başka bir bağlamdan mı geldi?
3. **Süre kontrolü var mı?** 75 sn çıkmış. Daha uzun/kısa istenebilir mi?
4. **`lh3` URL'i ne kadar yaşıyor?** IP'ye kilitli değil ama token süreli olabilir.
   Üretimden hemen sonra indirilirse sorun yok.

---

# EK — Kullanıcının anlattığı akışla karşılaştırma (2026-11-15)

Kullanıcı akışı:
1. Gemini'ye prompt → genel kültür sorusu + cevabı
2. NotebookLM'de **yeni not defteri** oluştur
3. Gemini metnini **"Not oluştur"** ile ekle (kaynak değil, **not**)
4. Studio → **Video Özeti** → **Kısa video** → Hemen oluştur

## HAR hangisini kapsıyor?

`ogs.google.com_2026_11_15_19_46_29.har` = `1.md` içinden çıkan `1.har`.
SHA256 birebir aynı → **daha önce incelediğim dosya, yeni bilgi yok.**

| Olay | Zaman | HAR'da |
|---|---|---|
| Not defteri oluşturuldu | **16:31:18** | ❌ YOK |
| Not (artifact) eklendi — "Buruşan Parmakların Sırrı" | **16:31:46** | ❌ YOK |
| HAR kaydı başladı | 16:32:35 | — |
| `R7cb6c` — video üretimi başladı | 16:34:42 | ✅ |
| Video hazır (`gArtLc` indeks 4 = 3) | 16:42:55 | ✅ |
| İndirme (`drum.usercontent`) | 16:46:08 | ✅ |

**Kritik boşluk:** HAR kayda başladığında not defteri (16:31:18) ve not (16:31:46)
**zaten oluşturulmuştu**. Yani **defter açma ve not ekleme RPC'leri HAR'da yok.**

HAR'da toplam 23 farklı RPC var, hiçbiri "oluştur" değil:
`EEr8Nb ESY5D EylDcb Fxmvse HpN0Ub I3xc3c JFMDGd R7cb6c VfAZjd VxUbXb
ZwVcOc cFji9 e3bVqc gArtLc hPTbtc khqZz otmP3b ozz5Z rLM1Ne sODAg sqTeoe
ub2Bae vB2zic`

## "Kısa video" seçimi nerede?

`R7cb6c` yükü:
```
[[2,null,null,[1,...]], "<DEFTER_ID>",
 [null, null, 3, [[null,...,["<NOT_ID>", 2]]], null,null,null,null,
  [null,null,[[["<NOT_ID>"]], "tr", "", null, 4, null,null, 1]]]]
```
- **`3`** → arayüzde seçtiğin **"Kısa"** formatı (varsayılan `2` olurdu). *Hipotez — tek çağrı olduğu için karşılaştırma yok.*
- **`"tr"`** → dil
- `"<NOT_ID>", 2` → hangi notun videoya çevrileceği

## İlerleme okuma kuralı (kanıtlı)

`gArtLc` yanıtındaki yük dizisinde:
- **indeks 4 = 2** → üretiliyor (yanıt ~600 krkt)
- **indeks 4 = 3** → hazır (yanıt ~1962 krkt, video URL'leri dolu)
- **indeks 9 = `[75, 167000000]`** → süre 75 sn
- **indeks 8[1..4]** → `,22` / `,hls` / `,dash` / `,m22-dv` URL'leri

## Studio menüsü çelişkisi

`sqTeoe` yanıtı (2 kez, 16:32:43 ve 16:43:10) bu hesapta **Video Özeti ve Sesli
Özet listelemiyor**. Sadece şunlar var:

| Grup | Seçenekler |
|---|---|
| Canlı/sohbet | Ayrıntılı inceleme, Özet, Eleştiri, Tartışma |
| Raporlar | Açıklayıcı, Özet, Kısa |
| Sunumlar | Ayrıntılı Sunu, Sunucu Slaytları |
| Belgeler | Özet Belgesi, Çalışma Kılavuzu, Blog Yayını |

Yani video **menü listesinde yok ama üretildi**. Muhtemel açıklama: video/ses
özetleri bu RPC'nin kapsamı dışında, ayrı bir bayrakla yönetiliyor.
**Bu çelişki çözülmedi — kullanıcıya sorulacak.**
