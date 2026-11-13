# Workflow Dizini (otomatik üretildi)

**Elle düzenlemeyin.** Yenilemek için: `python3 tools/workflow_dizini_uret.py`

| Dosya | Ad | Manuel | Cron |
|---|---|---|---|
| `arsiv_esitleme.yml` | Arşiv ↔ Kanal Eşitleme (haftalık) | ✅ | 17 4 * * 0 |
| `cadans_olcum.yml` | Cron Cadans Ölçümü (günlük) | ✅ | 43 6 * * * |
| `canli_test.yml` | Canlı Test — 1 video üret + yükle (tek seferlik) | ✅ | — |
| `cleanup_low_views.yml` | 🧹 BOBİ TV Otomatik Temizleme — <100 İzlenme Videoları Sil | ✅ | 0 * * * * |
| `daily_production.yml` | BOBİ TV — Toplu Manuel Üretim Pipeline | ✅ | — |
| `hourly_production.yml` | BOBİ TV — Üretim (8 saatte bir) + Kota Takibi | ✅ | 0 */8 * * * |
| `kanal_envanteri.yml` | 📊 Kanal Envanteri (gerçek video sayısı) | ✅ | — |
| `kanal_sagligi.yml` | Kanal Sağlığı Ölçümü (günlük) | ✅ | 23 7 * * * |
| `kanal_temizle.yml` | BOBİ TV — Kanal Temizle | ✅ | — |
| `kapak_yenile.yml` | 🖼️ Mevcut Kapakları Yenile (Gemini) | ✅ | 15 9 * * * |
| `mini_app_pages.yml` | Mini App yayını (GitHub Pages) | ✅ | — |
| `mini_app_veri.yml` | Mini App verisi (salt okunur özet) | ✅ | 0 */8 * * * |
| `telegram_bot.yml` | BOBİ TV Telegram Bot Poller (güvenlik düzeltmeli) | ✅ | */5 * * * * |
| `test_pipeline.yml` | BOBİ TV v6.0 — Uçtan Uca Kalite Testi | ✅ | — |
| `weekly_report.yml` | BOBİ TV — Haftalık Performans Raporu | ✅ | 0 7 * * 1 |
| `yorum_cevap.yml` | Yorum Cevaplama — Gemini (saatlik) | ✅ | 17 * * * * |

## Notlar

- **Manuel ✅** = `workflow_dispatch` var, GitHub API ile tetiklenebilir.
- Yeni workflow: `.github/workflows/` altına `.yml` koy, sonra
  `python3 tools/workflow_dizini_uret.py` çalıştır (bu dosya yenilenir).
- Üretim tetikleme: `canli_test.yml` (bkz. `docs/AYARLAR.md`).
- Kapak hattı: `docs/KAPAK_TESHIS.md` · kurallar: `docs/KURALLAR.md`.
