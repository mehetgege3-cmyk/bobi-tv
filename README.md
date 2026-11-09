# 🎬 BOBİ TV v6.0 PRO — Otonom Viral YouTube Shorts Üretim Sistemi

Türkçe absürt ve ironik komedi diyaloglarını **yüksek tutunmalı (high-retention)** YouTube Shorts videolarına dönüştüren uçtan uca otonom yapay zeka prodüksiyon hattı.

---

## 🚀 v6.0 PRO Mimari Özeti

```text
bobi-tv/
├── .github/workflows/
│   ├── hourly_production.yml   # Pik saat üretimi (09:03, 13:03, 18:03, 21:03 TSİ + Artifact)
│   ├── arena_senaryo.yml       # Günlük Arena AI Master Loop senaryo üretimi
│   ├── daily_production.yml    # Manuel toplu üretim tetikleyicisi
│   ├── test_pipeline.yml       # Uçtan uca v6.0 Render & QC doğrulama testi
│   └── arena-agent.yml         # Arena.ai Playwright çerez & oturum testi
├── modules/
│   ├── arena_api.py            # Arena.ai Headless Playwright Yönetmen + Çerez Yenileyici
│   ├── arena_uretici.py        # Senkron üretim sarmalayıcısı
│   ├── scenario.py             # Kusursuz Döngülü (Seamless Loop) Senaryo Motoru v6.0
│   ├── tts_engine.py           # Çift Sesli (Ahmet+Emel), Sıfır Ölü Boşluklu TTS + WordBoundary
│   ├── audio_fx.py             # Stüdyo SFX (whoosh, pop, vine_boom, riser, ding) + Sidechain BGM (-14 LUFS)
│   ├── animasyon.py            # 1080x1920 30FPS Vektör Karakter Kartları + Kutulu Karaoke Altyazı + Zoom/Shake
│   ├── video_render.py         # Çok kanallı ses miksajı + FFmpeg rawvideo borusu + ffprobe Kalite Kontrolü (QC)
│   ├── kapak_uret.py           # Twist karesi seçimi + Montserrat-ExtraBold 'SONUNU BEKLE!' kapak üretici
│   ├── youtube_upload.py       # YouTube Data API v3 + Otomatik İlk Yorum (commentThreads) + Kota Koruması
│   └── telegram_notify.py      # Telegram anlık yayın, kuyruk ve hata bildirimleri
├── bobi_tv/
│   ├── assets/
│   │   ├── fonts/              # Montserrat-ExtraBold.ttf & Montserrat-Bold.ttf (Türkçe İ/Ş/Ğ tam uyumlu)
│   │   └── sfx/                # Önbellekli stüdyo ses efektleri (.wav)
│   ├── queue/                  # YouTube kotasına (uploadLimitExceeded) takılan hazır işlerin bekleme kuyruğu
│   ├── archive/                # Yayınlanan videoların geçmişi ve tekrar önleme (MD5) kayıtları
│   ├── production/             # Senaryo şablonları (prompt_template.md) ve geçici çalışma alanı
│   └── output/                 # Üretilen nihai MP4 ve kapak görselleri
├── docs/
│   └── BOBI_TV_V6_PRO_MIMARI_VE_KURALLAR.md  # 2026 Shorts Algoritma Rehberi & Teknik Dokümantasyon
├── arena-ask.mjs               # Arena.ai çerez birleştirme (<4KB) ve Tiptap otomasyon CLI aracı
├── arena-senaryo.mjs           # Master Loop JSON senaryo üretici Node betiği
├── main_pipeline.py            # Ana orkestrasyon ve akıllı kuyruk yöneticisi
├── requirements.txt            # Python bağımlılıkları
└── SKILL.md                    # BOBİ Ajan Anayasası ve v6.0 PRO Kalıcı Kuralları
```

---

## 💎 Shorts Hazırlarken Uygulanan 8 Altın Kural (v6.0 Standartları)

1. **0.0 Saniye Kancası (Sıfır Ölü Boşluk):** Videonun başında sessiz bekleme yoktur (`hook_suresi = 0.0`). İlk karede sarı şok başlık bandı, `whoosh` ses efekti ve olayın sonucundan başlayan ilk replik aynı salisede girer.
2. **Çift Sesli Zıt Diyalog:** Tekdüze anlatım yerine Karakter 1 **`tr-TR-AhmetNeural` (Erkek)** ve Karakter 2 **`tr-TR-EmelNeural` (Kadın)** sesleriyle karşılıklı konuşur.
3. **Nefes Boşluğu Kırpma (`silenceremove`):** TTS motorunun cümle başı ve sonuna eklediği 250–400ms ölü sessizlikler FFmpeg ile kesilir; `WordBoundary` zaman damgaları 0ms kaymayla yeniden kalibre edilir.
4. **Aktif-Kelime Kutulu Karaoke Altyazı:** Mobil izleyicilerin %60–80'i sesi kapalı başladığı için, o an okunan kelimenin arkasına yuvarlatılmış parlak sarı/kırmızı kutu (*pill*) çizilir ve Türkçe büyük harf kurallarına (`i -> İ`, `ı -> I`) tam uyulur.
5. **Vektörel Karakter Portreleri & Yaylanan Balonlar:** Sunucularda kırık emoji kutusu (`□`) oluşmaması için her karaktere özel vektörel portre rozeti ve ses şiddetine (RMS) duyarlı canlı ekolayzır çubukları çizilir.
6. **Twist Darbesi (Zoom + Shake + 808 Vine Boom):** Sondan bir önceki ters köşe cümlesinde `riser` + `vine_boom` çalar, üst bant kırmızıya döner, kamera **%118 zoom** ve hafif sarsıntı (*shake*) yapar.
7. **Sidechain Fon Müziği & `-14 LUFS` Ses Dengelemesi:** 118 BPM telifsiz ritmik fon müziği konuşma sırasında otomatik **`-20 dB`** seviyesine kısılır ve çıkış sesi YouTube Shorts standardı olan **`-14 LUFS`** seviyesine normalize edilir.
8. **%100 Dilbilgisel Kusursuz Döngü (Seamless Loop):** Son cümle yarım kalarak 0.0 saniyedeki ilk cümleye bağlanır; izleyici videonun bittiğini fark etmeden ikinci tura başlar (**>%100 APV**).

---

## ⚙️ GitHub Secrets Yapılandırması

| Secret Adı | Zorunlu | Açıklama |
|------------|:-------:|----------|
| `YOUTUBE_TOKEN` | ✅ | YouTube Data API v3 OAuth JSON (`client_id`, `client_secret`, `refresh_token`) |
| `YOUTUBE_CLIENT_SECRET` | ✅ | Google Cloud OAuth istemci yapılandırması |
| `ARENA_COOKIES_JSON` | ✅ | Cookie-Editor ile alınan Arena.ai oturum çerezleri (otomatik yenilenir) |
| `GH_PAT` | ✅ | Yenilenen Arena çerezini Secret'a geri yazmak ve workflow tetiklemek için PAT |
| `TELEGRAM_BOT_TOKEN` | ➖ | Yayın, kuyruk ve hata bildirimleri için Telegram Bot Token |
| `TELEGRAM_CHAT_ID` | ➖ | Bildirimlerin gönderileceği Telegram Chat ID |
| `PEXELS_API_KEY` | ➖ | Opsiyonel dikey HD B-Roll stok arka plan videosu anahtarı |

---

## 🧪 Çalıştırma Komutları

```bash
# Sadece yerel Pro MP4 + Kapak üretimi ve ffprobe Kalite Kontrolü (YouTube'a yüklemeden test)
YUKLEME_ATLA=1 GUNLUK_HEDEF=1 python3 main_pipeline.py

# Tam otonom üretim + YouTube yükleme + Otomatik ilk yorum + Akıllı kota kuyruğu
GUNLUK_HEDEF=1 python3 main_pipeline.py
```

## 📺 Kanal
- **YouTube:** [@BOBİTİVİ](https://www.youtube.com/@BOBİTİVİ)
