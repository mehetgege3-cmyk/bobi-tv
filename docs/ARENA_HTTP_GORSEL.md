# Arena.ai HTTP Görsel Hattı — Teknik Doküman

**Tarih:** 2026-11-13
**Durum:** CANLI KANITLI (koşular `43320057811`, `43323638730`)
**Skill özeti:** `skills/arena-http-gorsel/SKILL.md`
**HAR çözümlemesi:** `docs/ARENA_HAR_COZUMLEME.md`
**Dersler/hatalar:** `docs/ARENA_DERSLER.md`

---

## 1. Neden bu mimari

Tarayıcıyla Arena'ya istem göndermek zorunlu (reCAPTCHA v3 jetonu tarayıcıda
üretiliyor). Ama cevabı **DOM'dan okumak** kırılgandı:

- Ekran görüntüsü/DOM beklemesi 8 dakikaya kadar sürüyordu.
- Görsel `<img>` öğeleri sayfada geç yükleniyor, "görsel gelmedi" yanlış
  sonuçları üretiyordu.
- "Gönderildi (doğrulandı)" logu yanlış pozitif verebiliyordu (koşu
  `43292738267`: log gönderildi dedi, ekranda istem hâlâ kutuda).

Çözüm: **tarayıcı yalnızca gönderir**, cevap ve görsel HTTP'den okunur.
Sonuç: 8 dakika → **144 saniye** (koşu `43323638730`).

## 2. Uç noktalar (HAR ile doğrulandı)

| Uç | Yöntem | Ne verir | Tarayıcı gerekir mi |
|---|---|---|---|
| `/nextjs-api/stream/create-chat` | POST | `{"id": "<chat_id>"}` | **EVET** (recaptchaV3Token) |
| `/api/chat/{id}/events` | GET | SSE: `text-delta`, `tool-output-available` | hayır |
| `/api/chat/workspace/cas/user/{hash}` | GET | `image/png` | hayır |
| `/api/history/unified?limit=N` | GET | `entries[]` (id, title) | hayır |
| `/api/chat/{id}/preview` | GET | sandbox durumu (görselle ilgisiz) | hayır |
| `/api/chat/{id}/run-status` | GET | `status`, `retryAfterMs` | hayır |
| `/api/me/pulse` | GET | oturum canlılık göstergesi | hayır |

### create-chat gövdesi (HAR'dan)

```json
{
  "message": {
    "id": "<uuid>",
    "role": "user",
    "parts": [{"type": "text", "text": "<istem>"}]
  },
  "recaptchaV3Token": "<tarayıcıda üretilir>"
}
```

`recaptchaV3Token` olmadan denendi → **HTTP 400**:
`{"success":false,"error":{"issues":[{"code":"invalid_type","expected":"string","received":"undefined","path":["recaptchaV3Token"],"message":"Required"}],"name":"ZodError"}}`

### SSE kayıt biçimi

```
event: batch
id: 3,4,600
data: {"records":[{"seq_num":1,"timestamp":...,"body":"{\"data\":{\"type\":\"start\",...}}"}],...}
```

`body` alanı **JSON string**'dir; iki kez `json.loads` gerekir.

Olay tipleri (görülen): `data-agent-dispatch`, `start`, `reasoning-start`,
`reasoning-delta`, `reasoning-end`, `text-start`, `text-delta`, `text-end`,
`tool-input-start`, `tool-input-available`, `tool-output-available`, `finish`.

### Görsel referansı

```json
// üretim isteği
{"type":"tool-input-available","toolName":"generate_image",
 "input":{"file_path":"/home/user/kus_yesil_orman.png","prompt":"..."}}

// üretim sonucu
{"type":"tool-output-available","toolCallId":"tc_...",
 "output":{"status":"success","hash":"ncoCtMLfdc358Ey9wglM-B3UUTRNnmagcXr4BxtSZx8",
           "file_path":"/home/user/kus_yesil_orman.png"}}
```

İndirme: `GET /api/chat/workspace/cas/user/{hash}?w=1024`
→ canlı ölçüm: `HTTP 200`, `image/png`, **3.165.495 bayt**, **1408×768**.

## 3. Modüller

### `modules/arena_http.py`
| Fonksiyon | Görev |
|---|---|
| `_cerez_basligi(raw=None)` | Cookie-Editor JSON / ham base64 / `base64-` önekli değer → Cookie başlığı |
| `son_sohbetler(cerez, limit)` | `/api/history/unified` → `entries[]`; 401'de `oturum_doldu_isaretle()` |
| `sohbet_id_bekle(cerez, bilinen, azami_sn)` | Yeni sohbet kimliği (yedek yol); oturum dolduysa hemen çıkar |
| `_sse_kayitlari(metin)` | SSE gövdesi → kayıt yineleyicisi (iki kat JSON) |
| `akisi_oku(chat_id, cerez)` | Tek okuma: `metin`, `gorsel_yolu`, `hash`, `durumlar` |
| `hash_bekle(chat_id, cerez, azami_sn, aralik)` | Görsel hash'i gelene kadar akışı tekrar okur |
| `gorsel_indir(hash, hedef, cerez)` | PNG indirir; **<5000 bayt ise reddeder** |
| `prompt_hazirla(prompt)` | Sonuna `"Soru sorma, yap."` ekler (tekrar eklemez) |
| `oturum_doldu_mu()` / `oturum_doldu_isaretle()` | 401 bayrağı (koşu başına) |

### `modules/arena_api.py` (eklenenler)
| Fonksiyon | Görev |
|---|---|
| `create_chat_dinleyici_ekle(page)` | `page.on("response")` → `create-chat` yanıtından **chat_id**; `page.on("request")` → **giden mesajı loglar** |
| `son_chat_id()` | Yakalanan chat_id |
| `_son_sayfa()` | Son Playwright sayfası (teşhis) |

> **Kritik:** `create_chat_dinleyici_ekle` **her** Arena akışında çağrılmalı.
> `_arena_sorgusu_yap` içine gömülü olduğunda kapak hattı chat_id'yi
> yakalayamadı (koşu `43321910940`).

### `modules/kapak_gorsel.py`
- `gorsel_promptu(paket)` — videonun **tam metni** + 7 tasarım kuralı +
  **`"Soru sorma, yap. Tek bir görsel üret; aday sunma."`**
- `video_metni(paket)` — öncelik: `senaryo.tam_metin` → `paket["metin"]` →
  `senaryo.diyaloglar` → `baslik`
- `_http_ile_gorsel_al(arena_api, hedef)` — chat_id → `hash_bekle` →
  `gorsel_indir`; **400×400 altı görseli reddeder**
- DOM yolu (`_gorsel_bekle_ve_indir`) **yedek** olarak korunur

### `modules/kapak_arena.py` (düzeltmeler)
| Fonksiyon | Not |
|---|---|
| `ffmpeg_yolu()` | `shutil.which("ffmpeg")` yoksa `imageio_ffmpeg.get_ffmpeg_exe()` |
| `_video_boyutu(ff, video)` | `ffmpeg -i` çıktısından `WxH` okur; okunamazsa 1080×1920 |
| `ilk_kareye_yerlestir()` | Kapağı **videonun kendi çözünürlüğüne** ölçekler (concat şartı) |

## 4. 1. kareye yerleştirme — ffmpeg incelikleri

**Hata 1:** `shutil.which("ffmpeg")` → `None` (runner'da PATH'te yok).
Kapak sessizce atlanıyordu ("ilk kareye yerleştirme atlandı").

**Hata 2 (asıl):** Kapak 1080×1920'e ölçekleniyordu, video 720×1280 ise:

```
[Parsed_concat_4] Input link in0:v0 parameters (size 720x1280, SAR 1:1)
do not match the corresponding output link in0:v0 parameters (1080x1920, SAR 1:1)
→ rc=234, çıktı 0 bayt
```

**Çözüm:** kapak `scale={gen}:{yuk}:force_original_aspect_ratio=increase,
crop={gen}:{yuk},setsar=1` ile videonun boyutuna getirilir (`_video_boyutu`).

Kanıt (yerel): `KAPAKLI_test.mp4` = **1.032.169 bayt**, ilk kare **720×1280**.

## 5. Kapak istemi (üretimde kullanılan)

```
Sen YouTube Shorts için kapak (thumbnail) tasarlayan bir görsel tasarımcısın.
Aşağıda bir videonun TAM METNİ var. Önce metni baştan sona dikkatlice oku,
konuyu ve en şaşırtıcı noktayı belirle; sonra bu videoya kapak olacak TEK bir
dikey (9:16) görsel ÜRET.

GÖRSELİN AMACI: izleyici akışta kaydırırken durup tıklasın...
TASARIM KURALLARI:
1) Metnin en çarpıcı fikrini tek bir sahneyle anlat...
2) Güçlü görsel hiyerarşi...
3) Duygu ve merak... (korku/kan/şiddet YOK)
4) Renk: sıcak-soğuk kontrastı...
5) Stil: modern, sinematik...
6) GÖRSELİN İÇİNE YAZI KOYMA...
7) 9:16 dikey, küçük boyutta bile anlaşılır...

Şimdi görseli üret. Sadece görsel döndür; açıklama, metin veya kod yazma.
Soru sorma, yap. Tek bir görsel üret; birden fazla aday üretip seçenek sunma,
onay isteme.

=== VİDEO METNİ (TAM) ===
<video metni>
=== VİDEO METNİ SONU ===
```

## 6. Workflow'lar

| Workflow | Ne yapar | Süre |
|---|---|---|
| `.github/workflows/arena_gorsel_http.yml` | Gönder → HTTP oku → görsel indir → PIL doğrula | ~3 dk |
| `.github/workflows/kapak_uctan_uca.yml` | Video metni → Arena → 1. kareye yerleştir → artifact | **144 sn** |
| `.github/workflows/arena_merhaba.yml` | Basit sohbet testi (teşhis) | ~1 dk |

**Not:** Yeni workflow eklendiğinde `arena_self_repair.yml` izleme listesine de
eklenmeli — `tests/test_actions_workflows.py` bunu şart koşuyor.

## 7. Koşu izleme (zaman kaybı yok)

`tools/kosu_bekle.sh <RUN_ID> [AZAMI_TUR] [--log]`

```
⏱  124s  tur 13/60  durum=in_progress  sonuç=-
✅ Koşu bitti: success  (toplam 144s)
```

Sabit `sleep 180` yerine 10 sn'de bir durum sorgular, bitince **anında** döner.

## 8. Ölçüm özeti

| Ölçüm | Değer | Kaynak |
|---|---|---|
| Tam uçtan uca (metin→kapak→1. kare) | **144 sn** | koşu `43323638730` |
| Arena görseli (kapak) | 768×1376, ~200 KB | koşu `43323638730` |
| Arena görseli (ilk kanıt) | 1408×768, 3.165.495 bayt | HAR hash indirmesi |
| Kapaklı video | 617.294 bayt | koşu `43323638730` |
| Çerez canlılık | `pulse: 72` | `/api/me/pulse` |
| Test sayısı | **801 passed, 1 skipped** | `pytest -q` |

## 9. Sınırlar (dürüst)

- `create-chat` için **tarayıcı zorunlu**; tamamen tarayıcısız gönderim YOK.
- reCAPTCHA: çok sık koşuda "Security Verification" duvarı çıkar; geçmeye
  çalışmak boşa. 30-60 dk ara ver.
- Arena bazen 2 aday üretip seçim soruyor; istemle azaltıldı ama **tamamen
  kapatıldığı kanıtlanmadı**.
- Görsel `<hash>` değeri oturuma bağlı; başka oturumda 401/404 olabilir.
