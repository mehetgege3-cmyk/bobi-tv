# Workflow Dizini (otomatik üretildi)

**Elle düzenlemeyin.** Yenilemek için: `python3 tools/workflow_dizini_uret.py`

| Dosya | Ad | Manuel | Cron |
|---|---|---|---|
| `arsiv_esitleme.yml` | Arşiv ↔ Kanal Eşitleme (haftalık) | ✅ | 17 4 * * 0 |
| `cadans_olcum.yml` | Cron Cadans Ölçümü (günlük) | ✅ | 43 6 * * * |
| `canli_test.yml` | Canlı Test — 1 video üret + yükle (tek seferlik) | ✅ | — |
| `cleanup_low_views.yml` | 🧹 BOBİ TV Otomatik Temizleme — <100 İzlenme Videoları Sil | ✅ | 0 * * * * |
| `daily_production.yml` | BOBİ TV — Toplu Manuel Üretim Pipeline | ✅ | — |
| `hourly_production.yml` | BOBİ TV v6.4 PRO — Saatlik Üretim + Kota Takibi | ✅ | 0 */8 * * * |
| `kanal_sagligi.yml` | Kanal Sağlığı Ölçümü (günlük) | ✅ | 23 7 * * * |
| `kanal_temizle.yml` | BOBİ TV — Kanal Temizle | ✅ | — |
| `mini_app_pages.yml` | Mini App yayını (GitHub Pages) | ✅ | — |
| `mini_app_veri.yml` | Mini App verisi (salt okunur özet) | ✅ | 0 */8 * * * |
| `telegram_bot.yml` | BOBİ TV Telegram Bot Poller (güvenlik düzeltmeli) | ✅ | */5 * * * * |
| `test_pipeline.yml` | BOBİ TV v6.0 — Uçtan Uca Kalite Testi | ✅ | — |
| `weekly_report.yml` | BOBİ TV — Haftalık Performans Raporu | ✅ | 0 7 * * 1 |
| `yorum_cevap.yml` | Yorum Cevaplama — Arena AI (saatlik) | ✅ | 17 * * * * |

## Notlar

- **Manuel ✅** = `workflow_dispatch` var, GitHub API ile tetiklenebilir.
- Yeni workflow eklendiğinde `arena_self_repair.yml` izleme listesine de
  eklenmeli; `tests/test_actions_workflows.py` bunu şart koşar.
- Üretim tetikleme: `canli_test.yml` (bkz. `docs/ARENA_DERSLER.md` §6).
- Arena görsel hattı: `skills/arena-http-gorsel/SKILL.md`.
