# Gemini Entegrasyonu — Ölçüm ve Durum (2026-11-13)

**Anahtar:** `GEMINI_API_KEY` secret'ına yazıldı (53 bayt).
**Biçim notu:** `AQ.Ab8RN6...` — klasik `AIza...` biçiminden **farklı**, ama
API kabul ediyor (404 mesajları "model artık yok" diyor, "anahtar geçersiz"
demiyor → kimlik doğrulama **GEÇTİ**).

---

## 1. Model listesi (canlı, 2026-11-13)

`GET /v1beta/models?pageSize=60` → 60 model. İlgili olanlar:

| Model | Tür | Test sonucu |
|---|---|---|
| `gemini-3.8-flash` | metin | 503 (yüksek talep) / timeout |
| `gemini-3.6-flash`, `gemini-3.5-flash` | metin | 503 (yüksek talep) |
| `gemini-pro-latest`, `gemini-flash-latest` | metin | timeout |
| `gemini-3-pro-image` | görsel | **429 kota** |
| `gemini-3.1-flash-image` | görsel | **429 kota** |
| `gemini-3.1-flash-lite-image` | görsel | **429 kota** |
| `gemini-2.5-flash-image` | görsel | **429 kota** |
| `nano-banana-pro-preview` | görsel | **429 kota** |
| `gemini-2.5-flash` | metin | **404** — "no longer available to new users" |

**Önemli:** `gemini-2.5-flash` artık YENİ kullanıcılara kapalı; API'nin kendisi
`gemini-3.8-flash` öneriyor.

## 2. GÖRSEL ÜRETİMİ — KOTA SIFIR (kırmızı)

Tüm görsel modelleri aynı hatayı veriyor:

```json
{"error":{"code":429,"message":"You exceeded your current quota...
 \"Quota exceeded for metric:
  generativelanguage.googleapis.com/generate_content_free_tier_requests,
  limit: 0, model: gemini-3.1-flash-image"}}
```

**`limit: 0`** = bu proje için **ücretsiz katmanda görsel üretimi HİÇ YOK**.
Kota aşımı değil; **kota tanımlı değil**. Çözüm yalnızca:
- Google AI Studio / Cloud projesinde **faturalandırma (billing) açmak**, veya
- görsel yetkisi olan **başka bir anahtar** kullanmak.

**Sonuç:** Gemini şu an **kapak görseli üretemez**. Bu, kodla çözülemez.

## 3. METİN ÜRETİMİ — geçici 503

`gemini-3.8-flash` bazen 503 ("This model is currently experiencing high
demand. Spikes in demand are usually temporary") ve bazen timeout veriyor.
**Bu geçici**; retry ile çözülür. Anahtar ve kota metin tarafında sorunsuz
görünüyor (404/401 değil, 503 = sunucu tarafı).

## 4. Çağrı biçimi (doğrulanmış)

```http
POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent
x-goog-api-key: <GEMINI_API_KEY>
content-type: application/json
```

**Metin:**
```json
{"contents":[{"parts":[{"text":"..."}]}]}
```

**Görsel:**
```json
{"contents":[{"parts":[{"text":"..."}]}],
 "generationConfig":{"responseModalities":["IMAGE"],
                     "imageConfig":{"aspectRatio":"9:16"}}}
```
Yanıt: `candidates[0].content.parts[].inlineData.data` (base64 PNG).

## 5. Projeye etkisi

| İş | Arena | Gemini |
|---|---|---|
| Senaryo (metin) | çerez ölü (401) | ⚠️ geçici 503, retry ile olur |
| Kapak **görseli** | çerez ölü | ❌ kota `limit: 0` |
| Görsel **indirme/okuma** | ✅ HTTP yolu (tarayıcısız) | — |

**Mevcut en sağlam durum:** üretim, `kaynak=video_karesi` yedeğiyle **çalışıyor**
(kanıt: https://www.youtube.com/shorts/MO1QOKxr4NQ). Arena görseli veya Gemini
görseli gelmediği sürece kapak, videonun 1. karesinden üretilir ve çift başlık
kusuru düzeltilmiştir (`KAPAK_BASLIK_BINDIR=0`).

## 6. Kod

`modules/gemini_api.py`:
- `anahtar()` — env/secret'tan anahtar
- `metin_uret(prompt)` — metin üretimi, 503'te üstel geri çekilme
- `gorsel_uret(prompt, hedef)` — görsel; **429'da net Türkçe hata** döner
  (`kota_yok`), sessizce yedeğe düşmez
- `durum()` — anahtar var mı + son hata

`modules/kapak_gorsel.py` sırası:
1. Arena (çerez canlıysa)
2. Gemini (kota varsa)
3. video karesi (her zaman çalışır)

## 7. Kapak hattına bağlanma (2026-11-13)

`modules/kapak_hatti.kapak_uret_ve_yerlestir` sırası:

1. **Arena** görseli (çerez canlıysa) → `kaynak=arena_gorsel`
2. **Gemini** görseli (kota varsa) → `kaynak=gemini_gorsel`  ← **YENİ**
3. **video karesi** (her zaman çalışır) → `kaynak=video_karesi`

Gemini `429 limit: 0` dönerse log'a şu yazılır ve 3. adıma geçilir:
`[Gemini] ⛔ ... görsel KOTASI TANIMLI DEĞİL (limit: 0). Faturalandırma
açılmalı ya da görsel yetkili anahtar gerekir.`

**Yani:** Gemini'de görsel kotası açıldığı gün **hiçbir kod değişikliği
gerekmeden** kapaklar Gemini'den gelmeye başlar.

## 8. Testler

`tests/test_gemini_api.py` — 5 test (anahtar yok, boş prompt, durum, aday listesi).
Toplam: **679 passed, 1 skipped** (2026-11-13 güncel).

---

# 9. GÜNCEL DOKÜMAN OKUMASI (2026-11-13) — K1 kuralı gereği

Kaynaklar: `ai.google.dev/gemini-api/docs/image-generation`,
`ai.google.dev/gemini-api/docs/rate-limits` (ikisi de okundu), + REST örnekleri.

## 9.1 Doküman DEĞİŞMİŞ: görsel üretim artık "Nano Banana" + Interactions API

| Ürün adı | Model adı | Durum |
|---|---|---|
| **Nano Banana 2.1** | `gemini-nano-banana-2.1` | **önerilen** (iş atı) |
| Nano Banana 2 Lite | `gemini-3.1-flash-lite-image` | en hızlı/ucuz |
| Nano Banana 2 | `gemini-3.1-flash-image` | önceki nesil |
| Nano Banana Pro | `gemini-3-pro-image` | premium, "Thinking" |
| **Nano Banana** | `gemini-2.5-flash-image` | **LEGACY** — doküman "migrate et" diyor |

**Yeni uç nokta:** `POST /v1beta/interactions` (gövde: `{"model","input"}`),
yanıt `interaction.output_image.data`. `generateContent` sayfası artık
**"(Legacy)"** başlıklı: `ai.google.dev/gemini-api/docs/generate-content/image-generation`.

**Tüm üretilen görsellerde SynthID filigranı var.**

## 9.2 KOTA: sebep bulundu — **limit: 0**

Tam hata gövdesi (`gemini-2.5-flash-image`, `x-goog-api-key`):
```
429 RESOURCE_EXHAUSTED
Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests,
  limit: 0, model: gemini-2.5-flash-preview-image,
  description: Generate content requests per day limit exceeded on Free Tier.
Please retry in 2h15m03s.
```
Yeni Interactions API (`gemini-nano-banana-2.1`):
```
429 too_many_requests
Rate limit exceeded for model gemini-nano-banana-2.1
  (limit: 0 input tokens per minute on Free Tier). Please upgrade your tier.
```

**Denenen 7 yol, hepsi 429/limit 0:**
`gemini-2.5-flash-image` (sade gövde, `responseModalities` TEXT+IMAGE, `v1`,
`v1beta?key=`), `gemini-3-pro-image`, `gemini-3.1-flash-image`,
`gemini-3.1-flash-lite-image`, `gemini-nano-banana-2.1` (hem `generateContent`
hem `interactions`), `nano-banana-pro-preview`.

→ **Sorun çağrı biçimi DEĞİL.** Bu projede ücretsiz katmanda **görsel kotası 0**.

## 9.3 Ücretsiz katman gerçekleri (dokümandan, ezber değil)

- **"Rate limits are applied per project, not per API key."**
  → **Aynı projede yeni anahtar almak kotayı DÜZELTMEZ.** Yeni **proje** şart.
- **RPD (günlük) kotası Pasifik gece yarısı sıfırlanır.**
- Görsel modeller için **IPM** (images per minute) ayrı sayılır.
- Faturalandırma (Tier 1) açılana kadar ücretsiz katman geçerli.

**Ölçümle doğrulama:** 2026-11-13 05:45 UTC'de hata "retry in 2h15m03s" dedi
→ 08:00 UTC = Pasifik gece yarısı (12 Kasım 21:45 PST + 2s14d). **Tutarlı.**

## 9.4 Kod güncellendi

`modules/gemini_api.py`:
- `GORSEL_ADAYLARI` artık **güncel doküman sırası** (`gemini-nano-banana-2.1`
  başta, legacy `gemini-2.5-flash-image` sonda).
- `kota_sifirlanma()` — 429'daki `retry in Xh Ym` ayrıştırılır, UTC an döner.
  429 logu artık şunu yazar: `Sıfırlanma: 2026-11-13 08:00 UTC`.

## 9.5 Kullanıcıya net durum

| İddia | Kanıt |
|---|---|
| "Gemini 2.5-flash-image çalışıyor" | **AI Studio arayüzünde** çalışır; **API'de** bu anahtar/proje için `limit: 0` |
| Anahtar geçersiz mi? | **Hayır** — 401 değil, 429; "anahtar geçersiz" demiyor |
| Çağrı biçimi yanlış mı? | **Hayır** — resmî dokümandaki 4 biçim de denendi |

**Kalıcı çözüm (biri şart):**
1. **Yeni bir Google Cloud projesi** + orada API anahtarı (kota proje başına),
2. veya aynı projede **faturalandırma (Billing)** açmak (Tier 1).
