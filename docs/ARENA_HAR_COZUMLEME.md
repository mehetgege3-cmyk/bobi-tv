# Arena.ai HAR Çözümlemesi (Drive'daki md dosyası)

**Kaynak:** Google Drive → `patates/arena.ai_2026_11_13_00_17_02.md`
**Boyut:** 8.225.741 bayt · **Kayıt:** 124 istek · **Araç:** Reqable 3.3.11
**Çözümleme tarihi:** 2026-11-13

---

## 1. Dosya nedir

Dosya adı `.md` ama içerik **HAR** (HTTP Archive): Reqable'ın kaydettiği
arena.ai ağ trafiği. JSON yapısı:

```
{"log": {"version": "1.2", "creator": {...}, "entries": [ ... 124 kayıt ... ]}}
```

Her kayıt: `startedDateTime`, `time`, `request` (method, url, headers,
cookies, postData), `response` (status, headers, content).

> **Uyarı:** İçinde **canlı oturum jetonları** var (`arena-auth-prod-v1.0`,
> `provider_refresh_token`, Google `ya29.` token). Bu dosya **asla** herkese
> açık paylaşılmamalı. Okumak için gerekiyorsa link-only aç, indirdikten
> hemen sonra `make_private` ile kapat.

## 2. Hostname dağılımı

| Host | İstek |
|---|---|
| `arena.ai` | 72 |
| `browser-intake-us3-datadoghq.com` | 45 (izleme, işe yaramaz) |
| `beacons.gcp.gvt2.com` | 7 (Chrome telemetrisi) |

## 3. İşe yarayan uçlar

| Yöntem | Yol | Durum | MIME | Not |
|---|---|---|---|---|
| POST | `/nextjs-api/stream/create-chat` | 200 | JSON | **Mesaj gönderme**; `recaptchaV3Token` zorunlu |
| GET | `/api/chat/{id}/events` | 200 | `text/event-stream` | Cevap akışı (SSE) |
| GET | `/api/chat/workspace/cas/user/{hash}` | 200 | `image/png` | **Üretilen görsel** |
| GET | `/api/chat/workspace/cas/user/{hash}?w=256` | 200 | `image/webp` | Küçük önizleme |
| GET | `/api/history/unified?limit=20&includeArchived=false` | 200 | JSON | Sohbet listesi |
| GET | `/api/chat/{id}/preview` | 200 | JSON | Sandbox durumu (görselle ilgisiz) |
| GET | `/api/chat/{id}/run-status?inputId=...` | 200 | JSON | `status: cooldown`, `retryAfterMs: 39000` |
| GET | `/api/connectors`, `/api/connectors/status` | 200 | JSON | Bağlayıcı listesi |
| GET | `/api/me/pulse` | 200 | JSON | Oturum canlılığı (`pulse`, `refreshedAt`) |
| POST | `/api/chat/{id}/review-feedback` | 200 | JSON | Değerlendirme |

## 4. `create-chat` isteği (ayrıntı)

**Gövde:**
```json
{
  "message": {"id":"01a1d193-841d-7993-8cec-41425d5a2c04",
              "role":"user",
              "parts":[{"type":"text","text":"Kuşlar uçuyor mu"}]},
  "recaptchaV3Token":"0cAFcWeA4Je4JACg...<çok uzun>"
}
```

**Yanıt:** `{"id":"01a1d193-8b4a-7b3c-8e18-3d1baac3829a"}`

Bu `id` = **chat_id**. Cevap ve görsel bununla okunur.

**Önemli başlıklar (çerez dışında):**

| Başlık | Değer |
|---|---|
| `content-type` | `application/json` |
| `origin` / `referer` | `https://arena.ai` / `https://arena.ai/agent` |
| `x-agent-browser-attempt-id` | uuid v7 |
| `x-arena-web-deployment` | `dpl_55LUqJyJadX8SdSzULyHRjK5V6VA` |
| `user-agent` | Chrome 157 mobil (Android) |
| `accept-language` | `tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7` |

**Yanıt başlıkları:** `server: cloudflare`, `cf-ray`, `vary: X-Arena-Expected-API-Deployment, ...`

## 5. Çerez listesi (16 adet)

| Çerez | Görev | Gerekli |
|---|---|---|
| `arena-auth-prod-v1.0` | **Oturum jetonu** (base64 önekli JWT — **değeri yazılmaz**) | **ŞART** |
| `arena-auth-prod-v1.1` | Oturum ikinci parça | **ŞART** |
| `cf_clearance` | Cloudflare doğrulaması | ŞART (bot kontrolü) |
| `__cf_bm` | Cloudflare bot yönetimi | ŞART |
| `arena_build_bucket` | `stable` | faydalı |
| `user_country_code` | `TR` | faydalı |
| `arena_visit_id`, `arena_acq_source` | analitik | gereksiz |
| `_ga`, `_ga_*`, `ph_*`, `_dd_s`, `_vcrr_*` | analitik | gereksiz |

`arena-auth-prod-v1.0` çözüldüğünde (base64 → JWT): `access_token`,
`refresh_token`, `expires_at`, `user.email`, `user.id`, `provider: google`,
`provider_token`, `provider_refresh_token`.

> **Not:** `expires_at` süresi dolsa da `/api/me/pulse` 200 dönebildi
> (canlı ölçüm: `pulse: 72/84`). Oturum canlılığını **pulse** ile ölç,
> `expires_at`'e güvenme.

## 6. SSE akışı örneği

```
event: ping
data: {"timestamp":1794517473481,"tail":{"seq_num":0,"timestamp":0}}

event: batch
id: 0,1,305
data: {"records":[{"seq_num":0,"timestamp":1794517475369,
  "body":"{\"data\":{\"type\":\"data-agent-dispatch\",...}}"}],
  "tail":{"seq_num":1,"timestamp":1794517475369}}
```

Görsel üretimi olan sohbette görülen tip sayıları:

```
data-agent-dispatch:1, start:1, reasoning-start:1, reasoning-delta:2,
tool-input-start:2, tool-input-available:2, tool-output-available:2,
text-start:1, text-delta:4, reasoning-end:1, text-end:1, finish:1
```

**Görsel çıktısı (ham):**
```json
{"type":"tool-output-available","toolCallId":"tc_52S4nWntXpFaWdCdvkbslL",
 "output":{"status":"success","hash":"ncoCtMLfdc358Ey9wglM-B3UUTRNnmagcXr4BxtSZx8",
           "file_path":"/home/user/kus_yesil_orman.png"}}
```

**Modelin cevabı (text-delta birleşimi):**
`"Yeşil ormanın içinde bir kuş resmi hazırladım: dalda duran, renkli tüylü bir
kuş ve arkada güneş ışığının süzüldüğü yeşil ağaçlar. Dosya:
/home/user/kus_yesil_orman.png"`

## 7. Canlı doğrulamalar (HAR sonrası, bu oturumda)

| Test | Sonuç |
|---|---|
| `GET /api/me/pulse` (HAR çereziyle) | `200 {"pulse":72,...}` |
| `GET /api/history/unified?limit=3` | `200`, sohbetler geldi |
| `GET /api/chat/{id}/events` | `200`, cevap + hash çıktı |
| `GET /api/chat/workspace/cas/user/{hash}` | `200 image/png`, **3.165.495 bayt**, 1408×768 |
| `GET /api/chat/workspace/cas/user/{hash}?w=1024` | `200 image/png`, **144.252 bayt**, 1024×559 |
| `POST /nextjs-api/stream/create-chat` (jetonsuz) | **400 ZodError** |
| `GET accounts.google.com/v3/signin/identifier` (doğrudan) | **400** |

## 8. Taranmayanlar (bilerek)

- `datadoghq` RUM/log istekleri (45 adet) — izleme, işe yaramaz.
- `/api/connectors*` — bağlayıcı listesi; görsel hattıyla ilgisiz.
- `/api/chat/{id}/review-feedback` — değerlendirme gönderimi.
- `beacons.gcp.gvt2.com` — Chrome telemetrisi.
