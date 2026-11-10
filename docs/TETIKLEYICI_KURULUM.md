# Üretim Tetikleyici Kurulumu (dış dağıtıcı)

## Neden gerekli?

GitHub Actions `schedule` (cron) **garantili bir zamanlayıcı değildir**: yüksek yüklü
dönemlerde koşuları kuyruğa alır, geciktirir ve atlar. `*/10 * * * *` ayarlandığında
fiilen günde 1-2 koşuya düştüğü gözlemlendi (bkz. `docs/OTOMASYON_TESHIS_2026-11-10.md`).

Bu yüzden `hourly_production.yml` artık **iki dış tetikleyici** kabul eder:

| Tetikleyici | Uç nokta | Kullanım |
|---|---|---|
| `workflow_dispatch` | `POST /repos/{owner}/{repo}/actions/workflows/hourly_production.yml/dispatches` | Tek seferlik / Telegram "Üret" butonu |
| `repository_dispatch` (tip: `bobi-tv-produce`) | `POST /repos/{owner}/{repo}/dispatches` | Dış dağıtıcının düzenli tetiklemesi |

Saatlik `cron: '0 * * * *'` yalnızca **yedektir**: dış dağıtıcı ölürse üretim saat
başı devam eder.

## Gerekli token yetkisi

- **Fine-grained PAT:** `Actions: write` izni yeterlidir (repo erişimi: yalnızca bu repo).
- **Classic PAT:** `repo` scope gerekir.

**Güvenlik kuralları (istisnasız):**

1. Token değeri **asla** bu belgeye, koda, loga veya commit'e yazılmaz.
2. Token yalnızca dağıtıcının (cron-job.org vb.) **secret alanında** saklanır.
3. Bu belgedeki `$GITHUB_TOKEN` bir **yer tutucudur**; gerçek değer secret'tan okunur.
4. Minimum yetki ilkesi: token yalnızca `Actions: write` verir; `contents: write` gerekmez.

## Kurulum — cron-job.org (ücretsiz, 15 dakikalık interval)

1. cron-job.org'da yeni job oluştur; interval: **15 dakika** (kadans: `modules/kadans.py` → `KADANS_DK=15`).
2. Ayarlar:

   - **URL:** `https://api.github.com/repos/mehetgege3-cmyk/bobi-tv/dispatches`
   - **Method:** `POST`
   - **Headers:**
     - `Accept: application/vnd.github+json`
     - `X-GitHub-Api-Version: 2022-11-28`
     - `Authorization: Bearer <secret'tan okunan token>` (değer cron-job.org'un
       "Bearer Token" / header secret alanına girilir, URL'ye veya body'ye asla)
   - **Body:**

     ```json
     { "event_type": "bobi-tv-produce", "client_payload": { "force": "false" } }
     ```

3. Kaydet ve "Test run" ile doğrula: GitHub → Actions →
   "BOBİ TV v6.4 PRO — Saatlik Üretim" koşusu başlamalı.

### Alternatif: workflow_dispatch uç noktası

```bash
curl -s -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/repos/mehetgege3-cmyk/bobi-tv/actions/workflows/hourly_production.yml/dispatches \
  -d '{"ref":"main","inputs":{"force":"false"}}'
```

Başarı yanıtı **HTTP 204 (içerik yok)** — gövde bekleme. `$GITHUB_TOKEN` ortam
değişkeni secret'tan okunur; komut satırına açık değer yazılmaz (shell history'ye
düşmesin diye).

## Gözlemlenebilirlik

Workflow her koşunun başında **"Son koşudan bu yana geçen süreyi logla"** adımıyla
önceki koşudan bu yana geçen dakikayı yazdırır. Dış dağıtıcının gerçek sıklığını
Actions loglarından bu adımla denetleyebilirsin: 15 dakikalık ayarda bu değer
yaklaşık 15-20 dakika olmalı; saatlik cron'a düştüğünde 55-65 dakika görürsün —
o zaman dağıtıcı bozuk demektir.

## Kota kapısı notu

Dış tetikleyici sıklığı artsa da üretim `GUNLUK_MAKS` ve kota state dosyası
(`bobi_tv/state/youtube_quota.json`) ile sınırlandırılır; dağıtıcı çok sık çağırsa
bile günlük tavan aşılmaz. `force: true` payload'ı bu kapıyı atlar — yalnızca
elle, bilinçli kullanım içindir.
