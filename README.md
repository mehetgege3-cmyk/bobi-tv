# BOBİ TV — Otonom YouTube Shorts Üretim Sistemi

Türkçe absürt/ironik animasyon Shorts videoları üreten otonom sistem.

## Yapı

```
bobi-tv/
├── .github/workflows/
│   ├── daily_production.yml   # Günlük otomatik üretim (2x gün)
│   ├── weekly_report.yml      # Haftalık performans raporu
│   └── test_pipeline.yml      # Manuel test tetikleyici
├── modules/
│   ├── telegram_notify.py     # Telegram bildirim modülü
│   ├── youtube_token.py       # YouTube OAuth token yönetimi
│   ├── scenario.py            # Senaryo üretim modülü
│   ├── tts_engine.py          # TTS ses üretim modülü
│   ├── video_render.py        # Video kurgu ve render modülü
│   └── youtube_upload.py      # YouTube yükleme modülü
├── bobi_tv/
│   ├── archive/videos.json    # Yayınlanan video arşivi
│   ├── production/             # Üretim çalışma dosyaları
│   ├── output/                 # Final videolar
│   └── logs/                   # İşlem kayıtları
├── main_pipeline.py            # Ana üretim pipeline
├── requirements.txt             # Python bağımlılıkları
└── SKILL.md                    # Ajan davranış tanımı
```

## Çalıştırma

### Manuel test (GitHub Actions)
Repo → Actions → "BOBİ TV — İlk Kurulum Testi" → Run workflow

### Otomatik
Günde 2 kez (09:00 ve 15:00 Türkiye saati) otomatik çalışır.

## Secrets
| Secret | Açıklama |
|--------|----------|
| YOUTUBE_TOKEN | OAuth token JSON |
| YOUTUBE_CLIENT_SECRET | Google client secret JSON |
| TELEGRAM_BOT_TOKEN | Telegram bot token |
| TELEGRAM_CHAT_ID | Telegram chat ID |

## Kanal
- YouTube: [@BOBİTİVİ](https://www.youtube.com/@BOBİTİVİ)
- Discord: —
