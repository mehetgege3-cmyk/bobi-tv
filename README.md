# 🎬 BOBİ TV — Otonom YouTube Shorts Üretim Hattı

Türkçe ilginç bilgi videolarını **sıfır insan müdahalesiyle** üretip YouTube
Shorts'a yükleyen otonom hat.

**Son güncelleme: 2026-11-13** · 679 test · 16 workflow · 38 modül

---

## ⚡ Tek sağlayıcı: Gemini web çerezi

Arena AI ve Gemini API **2026-11-13'te tamamen çöpe atıldı** (kullanıcı kararı).
Tek çalışan sağlayıcı **Gemini web çerezi**dir: kapak görseli, senaryo ve yorum
cevabı hepsi buradan gelir.

| Doküman | İçerik |
|---|---|
| `docs/GEMINI_WEB.md` | **Tek sağlayıcı** — çerezle görsel/metin üretimi, çalışan yol |
| `docs/GEMINI_ENTEGRASYON.md` | Neden Arena/Gemini API çöpe atıldı — ölçümler |
| `docs/KAPAK_TESHIS.md` | Kapak neden görünmüyordu — 4 kök neden + düzeltmeler |
| `docs/KURALLAR.md` | **Bağlayıcı çalışma kuralları K1–K9** — önce bunu oku |

**Kapak istemi (K8 — kullanıcının tek cümlesi, ek kural yok):**

```
<video başlığı> İsimli short video için kapak fotoğrafı istiyorum; etkileşim ve
izlenme rekorları kırması için profesyonel şekilde tasarla. Kapak fotoğrafını
gören merak edip tıklasın.
```

---

## 🔄 Üretim akışı

```
video metni
   ↓
Gemini web  →  kapak görseli (1080×1920)
   ↓
kapak_arena.ilk_kareye_yerlestir()  →  videonun 1. karesine 1.5 sn göm
   ↓
paket["final_video"] GÜNCELLENİR   ← 2026-11-13 DÜZELTMESİ
   ↓
youtube_upload.video_yukle()  →  YouTube + thumbnails.set
```

> ⚠️ **2026-11-13 düzeltmesi:** `paket["final_video"]` güncellenmediği için
> YouTube'a **kapaksız** video gidiyordu. Log "gömüldü: EVET" diyordu ama
> yükleme orijinal dosyayı okuyordu. Ayrıntı: `docs/KAPAK_TESHIS.md`.

---

## ⏱️ Üretim kadansı — 8 saatte bir (günde 3)

| Parametre | Değer | Yeri |
|---|---|---|
| `KADANS_DK` | **480** (8 saat) | `modules/kadans.py` |
| `KADANS_CRON` | **`0 */8 * * *`** (00/08/16 UTC) | `modules/kadans.py` |
| `IZLENME_KONTROL_DK` | **360** (6 saat) | `main_pipeline.py` |
| `MIN_IZLENME_ESIGI` | **100** | `main_pipeline.py` |
| Günlük yükleme tavanı | **YOK** | — |

Bağlayıcı kural: `docs/KADANS.md` Bölüm 5. Önceki "15 dakikada bir" rejimi
kanalı yaktı (1 saatte 21 silinen video, ortalama 0.8 izlenme) — iptal edildi.

---

## 📁 Yapı

```text
bobi-tv/
├── .github/workflows/            16 workflow
│   ├── hourly_production.yml     üretim (8 saatte bir) + zincirleme
│   ├── daily_production.yml      manuel toplu üretim
│   ├── canli_test.yml            tek video üret + yükle (canlı test)
│   ├── kapak_yenile.yml          mevcut videoların kapağını Gemini ile yenile
│   ├── kanal_envanteri.yml       kanal videolarını API'den listele
│   ├── kanal_sagligi.yml         günlük kanal ölçümü
│   ├── cadans_olcum.yml          kadans gerçekleşme ölçümü
│   ├── cleanup_low_views.yml     düşük izlenme temizliği
│   ├── yorum_cevap.yml           yorum cevaplama (Gemini)
│   ├── telegram_bot.yml          Telegram kontrol paneli (poller)
│   ├── arsiv_esitleme.yml        arşiv senkronizasyonu
│   ├── kanal_temizle.yml         kanal temizliği
│   ├── weekly_report.yml         haftalık rapor
│   ├── mini_app_pages.yml        Mini App yayını (GitHub Pages)
│   ├── mini_app_veri.yml         Mini App verisi
│   └── test_pipeline.yml         uçtan uca test
├── modules/                      38 modül
│   ├── gemini_web.py             ★ TEK SAĞLAYICI (web çerezi)
│   ├── gemini_api.py             ⛔ kullanılmıyor (kota 0)
│   ├── kapak_hatti.py            kapak üretimi + 1. kareye gömme hattı
│   ├── kapak_arena.py            ffmpeg: 45 kare = 1.5 sn gömme
│   ├── kapak_gorsel.py           görseli 1080×1920 kareye oturtma
│   ├── youtube_upload.py         yükleme + thumbnails.set + otomatik silme
│   ├── uretim_hatti.py           TTS → render → kapak → paket
│   ├── tts_engine.py             tr-TR Ahmet/Emel çift ses
│   ├── animasyon.py              1080×1920 30fps vektör + karaoke altyazı
│   ├── video_render.py           ffmpeg miksaj + ffprobe QC
│   ├── telegram_bot.py           Telegram paneli (132K, en büyük modül)
│   ├── ilginc_bilgi/             içerik hattı v8.0
│   └── senaryo_v7/               senaryo motoru v7 (sablonlar/doğrulama/...)
├── tools/                        5 canlı araç
│   ├── disk_bekci.py             workspace bütçe denetimi (K7)
│   ├── gemini_cerez_kur.py       Gemini çerezini doğrula + secret'a yaz
│   ├── kanal_envanteri.py        kanal videolarını API'den listele
│   ├── kapak_yenile.py           mevcut videoların kapağını yenile
│   └── workflow_dizini_uret.py   docs/WORKFLOW_DIZINI.md üretir
├── docs/                         18 doküman (aşağıda)
├── tests/                        679 test
├── arsiv/arena_olu_kod/          ÖLÜ Arena kodu — çalışmıyor, tarihsel
├── kanit/2026-11/                tarihli kanıtlar (gemini/ = canlı sağlayıcı)
├── bobi_tv/                      VERİ
│   ├── assets/                   fontlar (Montserrat) + SFX
│   ├── archive/                  yayın geçmişi + tekrar önleme (MD5)
│   ├── state/                    kalıcı durum JSON'ları
│   └── queue/                    kota kuyruğu
├── webapp/                       Mini App (GitHub Pages)
├── main_pipeline.py              ana orkestrasyon
└── SKILL.md                      ajan anayasası
```

---

## 🔑 GitHub Secrets

| Secret | Durum | Açıklama |
|---|:---:|---|
| `GEMINI_COOKIES` | ✅ **zorunlu** | Gemini web çerezleri (11 çerez). `tools/gemini_cerez_kur.py` ile kurulur |
| `YOUTUBE_TOKEN` | ✅ zorunlu | OAuth JSON (`client_id`, `client_secret`, `refresh_token`) |
| `YOUTUBE_CLIENT_SECRET` | ✅ zorunlu | Google Cloud OAuth istemci yapılandırması |
| `TELEGRAM_BOT_TOKEN` | ➖ | Telegram paneli |
| `TELEGRAM_CHAT_ID` | ➖ | Bildirim hedefi |
| `GH_PAT` | ➖ | Workflow tetikleme, secret yazma |
| `ARENA_COOKIES_JSON` | ⛔ **ölü** | Arena çöpe atıldı. Silinebilir |
| `GEMINI_API_KEY` | ⛔ **kullanılmıyor** | Görsel kotası `limit: 0`. Silinebilir |
| `LMARENA_EMAIL` / `LMARENA_PASSWORD` | ⛔ **ölü** | Arena girişi. Silinebilir |

> **K6:** API anahtarı/çerez sohbete yazılmaz, yalnız GitHub Secrets'a.

---

## 🧪 Çalıştırma

```bash
# Test
python3 -m pytest -q                          # 679 passed, 1 skipped

# Yerel üretim (YouTube'a yüklemeden)
YUKLEME_ATLA=1 GUNLUK_HEDEF=1 python3 main_pipeline.py

# Tam otonom üretim + yükleme
GUNLUK_HEDEF=1 python3 main_pipeline.py

# Kanal envanteri (GERÇEK video sayısı — API'den)
python3 tools/kanal_envanteri.py

# Mevcut videoların kapağını yenile
python3 tools/kapak_yenile.py --azami 5

# Workspace bütçe denetimi
python3 tools/disk_bekci.py
```

**Kalite kapısı:** `pytest -q`, `mypy --strict`, `ruff check`, `ruff format --check`.
**Kural:** testler yeşil olmadan push yok.

---

## 📚 docs/ — 18 doküman

| Doküman | İçerik |
|---|---|
| `KURALLAR.md` | **K1–K9 bağlayıcı kurallar** — önce bunu oku |
| `KADANS.md` | Üretim kadansı + bağlayıcı Bölüm 5 |
| `KAPAK_TESHIS.md` | Kapak kök nedenleri (2026-11-13) |
| `GEMINI_WEB.md` | Tek sağlayıcı, çalışan yol |
| `GEMINI_ENTEGRASYON.md` | Sağlayıcı karşılaştırması, eski ölçümler |
| `AYARLAR.md` | Ayar kataloğu |
| `KANCA_VE_KAPAK.md` | Kanca + kapak stratejisi |
| `ILGINC_BILGI_HATTI.md` | İçerik hattı v8.0 |
| `ETKILESIM_TAKTIKLERI.md` | Etkileşim taktikleri |
| `OLU_KOD_TEMIZLIGI.md` | Temizlik raporu (2026-11-13) |
| `TETIKLEYICI_KURULUM.md` | Zincirleme tetikleyici |
| `POLLER_GECIKMESI.md` | Telegram poller kararları |
| `MINI_APP.md`, `MINI_APP_KURULUM.md` | Mini App |
| `WORKFLOW_DIZINI.md` | Otomatik üretilen workflow listesi |
| `BOBI_TV_PRO_GELISTIRME_REHBERI.md` | Geliştirme rehberi |
| `TELEGRAM_AYARLAR_TALIMAT.md` | Telegram kurulumu |
| `logs_115683676683_analysis.md` | Log analizi |

---

## 📊 Kanal durumu (2026-11-13, API'den)

```
KANAL: BOBİ TV (UCJzCURUGVP3-baKe7N9FNjw)
abone=2 · video=13 · izlenme=6136
```

> **Ders:** Kanal verisi **her zaman** YouTube Data API'den alınır.
> `bobi_tv/archive/videos.json` kanal envanteri **değildir** — geçmiş kayıt
> defteridir (37 `silindi_dusuk_izlenme`, 9 `kaldirildi`). Bir kez bu dosya
> sayılıp "60 video var" dendi, kanalda 13 vardı.
