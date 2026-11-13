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
Toplam: **806 passed, 1 skipped**.
