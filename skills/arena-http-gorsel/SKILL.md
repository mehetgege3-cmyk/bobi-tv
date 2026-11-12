---
name: arena-http-gorsel
description: >
  Arena.ai'den TARAYICISIZ (HTTP) cevap ve GÖRSEL alma; görseli videonun
  1. karesine yerleştirme. reCAPTCHA'lı gönderim, create-chat yanıtından
  chat_id yakalama, SSE akışından görsel hash'i çıkarma ve indirme.
  Arena entegrasyonuyla ilgili her işte bu skill'i oku.
---

# Arena HTTP Görsel Skill'i

**Sürüm:** 1.0 (2026-11-13)
**Durum:** CANLI KANITLI — koşu `43323638730` success, `43320057811` success.
**Sahip dosyalar:** `modules/arena_http.py`, `modules/arena_api.py`,
`modules/kapak_gorsel.py`, `modules/kapak_arena.py`,
`tools/arena_http_gorsel.py`, `tools/kosu_bekle.sh`

---

## 1. Ne zaman kullanılır

- Arena'ya istem gönderip **cevabı** almak gerektiğinde
- Arena'nın **görsel üretmesini** isteyip dosyayı indirmek gerektiğinde
- Üretilen görseli **videonun 1. karesine** yerleştirmek gerektiğinde
- "Arena cevap vermiyor / görsel gelmiyor" hatasını teşhis ederken

## 2. Temel mimari (tek doğru yol)

```
TARAYICI (Playwright)        →  SADECE gönderir (recaptchaV3Token tarayıcıda üretilir)
   POST /nextjs-api/stream/create-chat   →  yanıt: {"id": "<chat_id>"}
HTTP (urllib, tarayıcı YOK)  →  her şeyi okur
   GET /api/chat/{chat_id}/events           → SSE: text-delta + tool-output-available
   GET /api/chat/workspace/cas/user/{hash}  → image/png (GERÇEK GÖRSEL)
   GET /api/history/unified?limit=N         → sohbet listesi (yedek yol)
   GET /api/chat/{id}/preview               → sandbox durumu (görselle ilgisiz)
   GET /api/me/pulse                        → oturum canlılık testi
```

**Altın kural:** Cevabı **DOM'dan okuma**, ekran görüntüsüyle doğrulama yapma.
Cevap ve görsel HTTP'den okunur; tarayıcı yalnızca gönderim içindir.

## 3. Zorunlu bilgiler (pazarlıksız)

| Konu | Gerçek |
|---|---|
| `recaptchaV3Token` | **ZORUNLU**. Jeton olmadan `create-chat` → `HTTP 400 ZodError path:["recaptchaV3Token"]`. Dışarıdan üretilemez; **tarayıcı şart**. |
| Çerez | `arena-auth-prod-v1.0` (+ `-v1.1`, `cf_clearance`, `__cf_bm`) gerekli. Ölü çerezde `GET /api/me/pulse` → **401**. |
| Görsel indirme URL'i | `/api/chat/workspace/cas/user/{hash}?w=1024` → `image/png` |
| Görsel hash kaynağı | SSE `tool-output-available` → `output.hash` (yedek: `output.file_path`) |
| Görsel yolu kaynağı | `tool-input-available` (`toolName: "generate_image"`) → `input.file_path` |

## 4. Adım adım akış (kopyala-uygula)

```python
from modules import arena_api, arena_http

# 0) Oturum canlı mı?
cerez = arena_http._cerez_basligi()          # ARENA_COOKIES_JSON → Cookie başlığı
#   401 alırsan: çerez ölmüş → kullanıcı tarayıcısından yeni çerez gerekir

# 1) TARAYICI ile gönder (recaptcha burada üretilir)
#    arena_api.create_chat_dinleyici_ekle(page) MUTLAKA çağrılmalı:
#    chat_id'yi create-chat YANITINDAN yakalar.
cevap_dom = arena_api.arena_kisa_cevap_al(prompt)   # ya da kapak_gorsel yolu

# 2) chat_id
chat_id = arena_api.son_chat_id()

# 3) HTTP: görsel hash'ini bekle (Arena 2. deneme yapabilir → döngü şart)
akis = arena_http.hash_bekle(chat_id, cerez, azami_sn=240, aralik=10)

# 4) HTTP: görseli indir
yol = arena_http.gorsel_indir(akis["hash"], "kanit/kapak.png", cerez)
```

## 5. Bilinen tuzaklar (hepsi canlı koşuyla kanıtlı)

| Tuzak | Kanıt | Çözüm |
|---|---|---|
| **Eski sohbet tuzağı** | koşu `43316348923`: çerezle açılınca son sohbet açılıyor, mesaj ORAYA gidiyor ("Kendi kendini tanıt" sohbetine gitti) | `/agent/00000000-0000-0000-0000-000000000000` adresine geç; `create-chat` yanıtını dinle |
| **URL'den chat_id okumak** | koşu `43315259344`: URL `/agent/` kalıyor | URL değil, `create-chat` **yanıtı** (`page.on("response")`) |
| **Geçmiş listesinden chat_id** | koşu `43313640773`: yeni sohbet listede yok | Yalnız yedek; 60 sn bekle, sonra vazgeç |
| **Tek seferlik akış okuma** | koşu `43311322015`: Arena "İlk deneme tüm modellerde başarısız oldu... yeniden deneyeceğim" | `hash_bekle()` ile 10-15 sn aralıkla tekrar oku |
| **"Which image do you prefer?"** | kullanıcı gözlemi: Arena 2 aday üretip seçim soruyor, akış kilitleniyor | İstem sonuna **`Soru sorma, yap. Tek bir görsel üret; aday sunma.`** |
| **401 spam** | koşu `43318433306`: 15 tur 401 | `oturum_doldu_mu()` ise döngüden çık |
| **Ölü çerez** | koşu `43318433306`: HTTP 401 | Çerezi secret'a yeniden yaz (`tools/secret_duzelt.py`) |
| **reCAPTCHA duvarı** | koşu `4329...`: "Security Verification / Protected by reCAPTCHA" | Çok sık koşu yapma; 30-60 dk ara ver. Geçmeye çalışma, kaçın. |

## 6. Çerez yönetimi

```bash
# Çerez canlı mı? (401 = ölü)
curl -s -H "cookie: <çerez>" https://arena.ai/api/me/pulse

# Secret'a yaz (SealedBox)
GH_PAT=... python3 tools/secret_duzelt.py \
  --ad ARENA_COOKIES_JSON --dosya /tmp/arena_cerez_secret.json --dosya-icerik
```

Çerez formatı: Cookie-Editor JSON (`[{"name":...,"value":...}]`) **veya** ham
`base64-...` değeri. `_cerez_basligi()` ikisini de kabul eder.

## 7. Kanıt dosyaları

| Dosya | Ne kanıtlıyor |
|---|---|
| `kanit/arena_gercek_gorsel.png` | Arena'nın ürettiği ilk gerçek görsel (3,1 MB, 1408×768) |
| `kanit/kapak_kanit/arena_kapak.png` | Süreç içinde üretilen kapak (720×1280) |
| `kanit/uctan_uca/kapakli_ilk_kare.jpg` | Kapaklı videonun 1. karesi (Arena görseli) |
| `kanit/uctan_uca/kapak_sakiz_test_kapak.jpg` | Üretilen kapak JPG (202 KB) |
| `kanit/uctan_uca/test_kapakli.mp4` | Kapak yerleştirilmiş video (617 KB) |

## 8. Hızlı teşhis tablosu

| Belirti | İlk bakılacak |
|---|---|
| `HTTP 400 ZodError recaptchaV3Token` | İstem tarayıcıdan gitmiyor |
| `HTTP 401` | Çerez ölü → `pulse` ile doğrula, secret'ı yenile |
| `chat_id=None` | `create_chat_dinleyici_ekle` bağlı mı? Eski sohbet tuzağı? |
| Akışta `hash` yok | Arena görsel üretmemiş/başarısız → `hash_bekle` + istemde "soru sorma" |
| `görsel 0 bayt / <5000 bayt` | İndirme yanlış hash ya da oturum düştü |
| "Anlaşıldı, daha ayrıntılı yanıt vereceğim" | Mesaj eski sohbete gitti |
