# BOBİ TV — Ayarlar Sistemi (TODO 1–12 Referansı)

**Tek doğruluk kaynağı:** `bobi_tv/state/ayarlar.json` (bot yazar, commit eder)
**Katalog:** `modules/ayar_katalogu.py` · **Depo:** `modules/ayar_deposu.py`
**Köprü:** `hourly_production.yml` → "Ayarları state'ten yükle" → `$GITHUB_ENV`

```
bobi_tv/state/ayarlar.json   ← tek doğruluk kaynağı (bot yazar, ayrı commit)
        │  (Ayarları state'ten yükle)
        ▼
$GITHUB_ENV ──► main_pipeline.py / modules/*   (os.environ.get — DEĞİŞMEZ)
```

**Öncelik:** `client_payload (koşul bazlı)` > `ayarlar.json (state)` > `env` > katalog varsayılanı.
Panel, her değerin hangi katmandan geldiğini etiketle gösterir: `6 (state)` / `6 (varsayılan)`.

---

## 🚀 Tetikleme (değiştirilebilir)

| Ayar | Env | Tip | Seçenekler | Varsayılan | Risk | Açıklama |
|---|---|---|---|---|---|---|
| Render testi | `YUKLEME_ATLA` | anahtar | — | `0` | düşük | `1` iken videolar yalnız yerelde üretilir, YouTube'a yükleme **yapılmaz**. 🧪 Render testi düğmesi bunu koşul bazlı zorlar. |
| Üretim modu | `MOD` | seçim | `isindirma_saatlik`, `normal` | `isindirma_saatlik` | düşük | Dönen konu havuzu + 15 sn alt sınır / sıradan üretim. |
| Kota kapısını atla | `force` | anahtar | — | `0` | **yüksek** | Kota kapısını bu koşuda devre dışı bırakır. **Tek kullanımlık:** üretim workflow'u tükettikten sonra state'i otomatik 0'a çeker ("Tek kullanımlık force bayrağını tüket" adımı). |

## 🎯 Üretim & Kota (değiştirilebilir)

| Ayar | Env | Tip | Seçenekler | Varsayılan | Risk | Açıklama |
|---|---|---|---|---|---|---|
| Günlük hedef | `GUNLUK_HEDEF` | seçim | `1`, `2`, `4` | `1` | düşük | Her koşuda hedeflenen yükleme sayısı. |
| Günlük üst sınır | `GUNLUK_MAKS` | seçim | `2`, `5`, `6` | `6` | orta | **Kota matematiği: 10000/1600 = 6.** 7+ seçenek bilinçli olarak YOK; kod ayrıca `min(deger, 6)` savunması yapar (`etkin_gunluk_maks`) ve kırparsa log uyarısı basar. |
| Kota dolunca | `KOTA_DOLU_DAVRANIS` | seçim | `sessiz_dur`, `hata` | **`sessiz_dur`** | **yüksek** | `sessiz_dur` → koşu **exit 0** ile biter (C2'deki `exit(1)` self-repair fırtınası — günde ~144 deneme + main'e otonom push — biter). `hata` → **exit 1**, kırmızı tik (eski davranış). |
| Kota rezerv eşiği | `KOTA_REZERV` | sayı | 0–2000 (ön ayarlar) | `500` | düşük | Birim cinsinden rezerv eşiği. Workflow kota birimini henüz rapor etmediği için panelde etkin kullanım `bilinmiyor` görünür. |

## 🧹 Temizlik — SADECE GÖRÜNTÜLE (`etkili=False`)

| Ayar | Env | Mevcut değer | Risk |
|---|---|---|---|
| Otomatik silme | `OTOMATIK_SIL_AKTIF` | `1` | yüksek |
| Minimum izlenme eşiği | `MIN_IZLENME_ESIGI` | `100` | yüksek |
| İzlenme kontrol süresi | `IZLENME_KONTROL_DK` | `1440` | düşük |

> ⚠️ Bu değerleri değiştirmek otomatik temizlemeyi **ETKİLEMEZ**. Temizleme workflow'u kendi sabitini
> kullanıyor (`cleanup_low_views.yml` → `if views < 100`). Bilinen sorun **(H1)**, ayrı görevde çözülecek.
> Bu grupta panel hiçbir değiştirme düğmesi ÜRETMEZ (`sadece_goruntule`); değişiklik denemesi reddedilir
> ve değişiklik geçmişine yazılmaz. Yalan söyleme yasağı: etkisiz olana "etkili" denmez.

## 🔑 Sistem durumu — SADECE GÖRÜNTÜLE (değer asla yazdırılmaz)

`YOUTUBE_TOKEN`, `YOUTUBE_CLIENT_SECRET`, `ARENA_COOKIES_JSON`, `PEXELS_API_KEY`, `GH_TOKEN`,
`TELEGRAM_BOT_TOKEN` → panelde yalnız **✅ tanımlı / ⛔ eksik** + kaynak (GitHub Secrets).
Secret değerleri mesajda, commit'te, logda, state'te ASLA görünmez.

Not: repoda `PEXELS_API_KEY` secret'ı şu an tanımlı DEĞİL → panelde ⛔ eksik görünür (dürüst gösterim).

---

## Kataloğa ALINMAYAN ayarlar (gerekçeli)

| Ayar | Neden yok |
|---|---|
| `TETIK_DK` | GitHub cron fiilen güvenilir çalışmıyor. "10 dk" ayarı yalan olurdu; tetikleyici sağlığı Sistem ekranında gözlemlenir. |
| `SESSIZ_SAAT` | Zaman dilimi + cron güvenilmezliği birleşince doğrulanamaz. Dış tetikleyici kurulunca eklenir. |
| `OTOMATIK_URETIM` | `repository_dispatch`'i çağıran dış tetikleyici yok; kapatma düğmesi işlevsiz olurdu. |

## Panel akışı (callback_data şeması)

`callback_data` **asla değer taşımaz, sadece kimlik taşır** — değer sunucuda katalog + state'ten çözülür.

| callback_data | Anlam | Derinlik |
|---|---|---|
| `menu_main` | Ana menü (4 düğme: Durum, Üret, Rapor, Ayarlar) | 0 |
| `ay:kok` | Ayarlar ana ekranı | 1 |
| `ay:g:<grup>` | Grup ekranı | 2 |
| `ay:s:<anahtar>` | Ayar detayı | 3 |
| `ay:v:<anahtar>:<indeks>` | Seçenek uygula (**indeks**, değer değil) | 3 |
| `ay:onay:<anahtar>:<indeks>` | Riskli ayar onayı (indeks ile) | 3 |
| `ay:iptal:<anahtar>` | Vazgeç — state bit bit aynı kalır | 3 |
| `ay:test:<anahtar>` | Dry-run ön izleme (hiçbir yazma yok) | 3 |
| `ay:gecmis` | Son değişiklikler (son 10) | 2 |
| `uret_menu` / `uret_baslat` / `uret_render_test` | Üretim ekranı / tetikleme / **yüklemsiz test** | 1–2 |

**Tek mesaj kuralı:** her etkileşim aynı panel mesajını düzenler (`editMessageText`). Yeni mesaj yalnızca:
`/start`, panel >48 saat, düzenlenecek mesaj bulunamadı. `message is not modified` sessizce yutulur.

## Kalıcılık (ayarlar kaybolmasın)

- `ayarlar.json` offset ile **aynı commit'e konmaz**; bot ayarı değiştirince **anında ayrı** commit+push yapar.
- Push başarısızsa: `bobi_tv/state/ayarlar_bekleyen.json`'a yazılır, panelde
  `⚠️ kaydedilemedi, tekrar denenecek` gösterilir, sonraki bot koşusunda yeniden denenir.
- Push başarısızlığı `|| echo` ile yutulmaz → `exit 1` (kırmızı tik).

## Değişiklik geçmişi

`bobi_tv/state/ayar_gecmisi.jsonl` — append-only, son **200 satır** (taşma `ayar_gecmisi.1.jsonl`'e döner).
Satır şeması: `{"zaman","kullanici_id","anahtar","eski","yeni","kaynak"}`. `sadece_goruntule` ayarlar geçmişe yazılmaz.

## Kota kapısı (workflow + pipeline)

- `hourly_production.yml` → "Kota durumunu kontrol et": `modules/kota_kapisi.kota_kontrol_yap`
  hesabı + `kota_dolu_cikis_kodu(KOTA_DOLU_DAVRANIS)` çıkışı.
- `main_pipeline.py`: `GUNLUK_MAKS = etkin_gunluk_maks(env)` (tavan 6) + kota dolunca
  `sys.exit(kota_dolu_cikis_kodu(...))`.
- Panel kota satırı: `bobi_tv/state/youtube_quota.json`'dan birim bilgisi VARSA
  `Kota: 4800/10000 birim · ~3 yükleme kaldı`; YOKSA **`bilinmiyor`** — sayı uydurulmaz.

## 🧪 Render testi (yüklemsiz test düğmesi)

Panel → 🎬 Üret → **🧪 Render testi**: `repository_dispatch` (`bobi-tv-produce`) +
`client_payload: {"yukleme_atla": "1", "force": "true"}`. Workflow videoları yerel üretir,
YouTube'a **yükleme yapılmaz**; sonuç mesajı süre · çıktı boyutu · QC sonucu +
"yükleme yapılmadı" içerir. Bu düğme "video üretiliyor mu?" sorusunu kotasız cevaplar.
Not: Bu düğme üretim tetiklemez; gerçek üretim için dış tetikleyici
(cron-job.org → `repository_dispatch`) gerekir — bkz. `docs/TETIKLEYICI_KURULUM.md`.
