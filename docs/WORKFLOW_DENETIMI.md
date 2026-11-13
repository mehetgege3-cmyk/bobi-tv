# Workflow Denetimi (2026-11-13)

**Kullanıcı:** *"Tüm workflow'ları sırayla mevcut güncel duruma göre değerlendirme
yap ve gerekli tüm düzeltmeleri yap artık işimize yaramayanları sil."*

**Sonuç: 16 → 13 workflow.** 3 silindi, 4 düzeltildi, 1 kilit eklendi.

---

## Kalan 13 workflow

| # | Workflow | Cron | Görev |
|---:|---|---|---|
| 1 | **Üretim (8 saatte bir) + Kota Takibi** | `0 */8 * * *` | Ana üretim hattı + zincirleme |
| 2 | **Canlı Test — 1 video** | — | Elle tek video testi (yükle/üret seçenekli) |
| 3 | **Toplu Manuel Üretim** | — | Elle çoklu üretim |
| 4 | **Mevcut Kapakları Yenile (Gemini)** | `15 9 * * *` | Geçmiş video kapakları |
| 5 | **Kanal Envanteri** | — | Gerçek video sayısı (API) |
| 6 | **Kanal Sağlığı Ölçümü** | `23 7 * * *` | Günlük ölçüm |
| 7 | **Cron Cadans Ölçümü** | `43 6 * * *` | Kadans gerçekleşme |
| 8 | **Arşiv ↔ Kanal Eşitleme** | `17 4 * * 0` | Haftalık senkron |
| 9 | **Haftalık Performans Raporu** | `0 7 * * 1` | Telegram raporu |
| 10 | **Yorum Cevaplama — Gemini** | `17 * * * *` | Saatlik yorum cevabı |
| 11 | **Telegram Bot Poller** | `*/5 * * * *` | Kontrol paneli |
| 12 | **Mini App verisi** | `0 */8 * * *` | Özet veri |
| 13 | **Mini App yayını** | tetiklemeli | GitHub Pages |

**Cron çakışması yok** — 7 farklı saat dilimi, hiçbiri çakışmıyor.

---

## 🗑️ Silinen 3 workflow

### 1. `cleanup_low_views.yml` — EN TEHLİKELİSİ

```yaml
cron: '0 * * * *'          # SAATLİK
if views < 100:            # YAŞ KONTROLÜ YOK
    youtube.videos().delete(id=video_id)
```

**İki kök sorun:**

1. **Yaş kontrolü yok.** `videos().list` çağrısında `publishedAt` filtresi yok.
   Yüklenmesinden **5 dakika sonra 99 izlenmedeki** bir videoyu siler.
2. **Çift mekanizma.** `main_pipeline.py` zaten silme yapıyor
   (`IZLENME_KONTROL_DK=360`, `MIN_IZLENME_ESIGI=100`). Bu ikinci ve daha
   acımasız olanıydı. `SKILL.md` §24.2 "TEK mekanizma" kuralını ihlal ediyordu.

> Bu, kanalı yakan "1 saatte sil" rejiminin kalıntısıydı. 37 video
> `silindi_dusuk_izlenme` olarak arşivde duruyor — bu workflow'un izi.

### 2. `kanal_temizle.yml` — GERİ DÖNÜŞÜ YOK

Arşivdeki **her** `video_id`'yi YouTube'dan siler. Bugün kanalda 13 video var
→ bu workflow **13'ünü de siler**. Tek tıkla kanal boşaltma aracı.

Geçmişte **0 kez** kullanılmış. Üretimde işlevi yok, riski maksimum.

### 3. `test_pipeline.yml` — KOPYA

`canli_test.yml` ile aynı işi yapıyordu (`main_pipeline.py` + `YUKLEME_ATLA=1`).
`canli_test` artık `yukle=0` girdisiyle onu tamamen kapsıyor.

---

## 🔧 Düzeltilen 4 hata

### 1. `canli_test.yml` — 2 işlevsiz girdi (sessiz yalan)

```yaml
inputs:
  konu_no: ...     # → VIDEO_NO env'i → KODUN HİÇBİR YERİ OKUMUYOR
  force: ...       # → TETIK_FORCE env'i → KODUN HİÇBİR YERİ OKUMUYOR
```

Kullanıcı "Konu numarası: 42" yazıyor, video yine sıradaki konudan üretiliyordu.
Hiçbir uyarı yok.

**Düzeltme:** ikisi kaldırıldı, yerine **gerçek** girdi eklendi:

```yaml
hedef: "Kaç video üretilsin (1-3 önerilir)"   # → GUNLUK_HEDEF + TUR_BASINA_URETIM + URETIM_TAVANI
```

Üçü de `main_pipeline.py`'de gerçekten okunuyor (satır 36, 50, 56).

### 2. `hourly_production.yml` — işlevsiz `force` girdisi

`force` tanımlıydı ama **hiçbir env'e bağlanmamıştı**. Seçmek hiçbir şeyi
değiştirmiyordu (kota kontrolü zaten kaldırılmış). Kaldırıldı.

### 3. Ölü env değişkenleri

| Değişken | Kodda referans | Karar |
|---|---:|---|
| `ARENA_IDLE_DK` | 0 | 🗑️ silindi |
| `ARENA_MAKS_DK` | 0 | 🗑️ silindi |
| `OPENAI_API_KEY` | 0 | 🗑️ silindi |
| **`PEXELS_API_KEY`** | **1** (`modules/animasyon.py:184`) | ✅ **korundu** |

> ⚠️ İlk denemede `PEXELS_API_KEY`'i de sildim — **yanlıştı**, `animasyon.py`
> B-roll arka plan için gerçekten okuyor. Test yakaladı, geri koydum.

### 4. `kapak_yenile.yml` — kilit yoktu

```yaml
# ÖNCE: kilit yok
# SONRA:
concurrency:
  group: kapak-yenile
  cancel-in-progress: false
```

Kilit olmadan: 09:15 cron'u + elle tetikleme aynı anda çalışırsa **iki koşu
aynı videoyu seçip üstüne iki kapak yükler**, YouTube kotası iki kez harcanır.

---

## Ek düzeltme: `daily_production` tutarlılık

`canli_test` ile arasında env farkı vardı. `CANLI_TEST=1` ve `GH_PAT` eklendi.

---

## Doğrulama

| Kontrol | Sonuç |
|---|---|
| Workflow sayısı | **16 → 13** (GitHub'da da 13) |
| Hepsi `active` | ✅ 13/13 |
| YAML geçerliliği | ✅ |
| Testler | **679 passed, 1 skipped** |
| Cron çakışması | ✅ yok |
| Ölü env | ✅ 0 |

`hourly_production` force-cancel sonrası kapanmıştı → **yeniden açıldı** (active).

---

## Değerlendirme notları — DOKUNULMAYANLAR

| Workflow | Neden kaldı |
|---|---|
| `daily_production` | `canli_test`'e benziyor ama **arşivi commit ediyor** ve varsayılan `hedef=2`. Toplu üretim için ayrı işlev. |
| `arsiv_esitleme` | Haftalık senkron. Gerçek iş yapıyor (`modules.arsiv_esitleme`). |
| `mini_app_veri` → `mini_app_pages` | Veri üretince Pages tetikleniyor. Sağlıklı zincir. |
| `yorum_cevap` | Saatlik, `GEMINI_COOKIES` kullanıyor. Kod doğru. |
| `telegram_bot` | 350 dk timeout / 300 dk döngü payı doğru (2026-11-13 düzeltmesi). |
