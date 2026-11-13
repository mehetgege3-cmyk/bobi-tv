# SİSTEM NASIL ÇALIŞIYOR — 2026-11-13 Durumu

Bu doküman **koda bakılarak** yazıldı, ezberden değil. Her iddianın dosya/satır
karşılığı var. Şüphe edersen `docs/` altındaki ilgili dokümana bak.

---

## 1. Tek cümlelik özet

> GitHub Actions, günde 3 kez (8 saatte bir) uyanır → Gemini web çerezinden konu
> ve senaryo alır → Türkçe seslendirir → 1080×1920 video render eder → Gemini'den
> kapak görseli üretip 1. kareye 1.5 sn gömer → YouTube Shorts'a yükler →
> 6 saat sonra 100 izlenme almadıysa siler → hepsini Telegram'dan bildirir.

İnsan müdahalesi yok. Tek dış bağımlılık: **Gemini web çerezi** (düzenli yenilenir).

---

## 2. Zaman çizelgesi — bir gün

```
00:00 UTC ─┬─ ÜRETİM TURU 1
08:00 UTC ─┼─ ÜRETİM TURU 2
16:00 UTC ─┴─ ÜRETİM TURU 3

her 5 dk   ── Telegram botu (panel komutlarını dinler)
her saat   ── Yorum cevaplama (yeni yorumlara Gemini cevabı)
06:43      ── Cron kadans ölçümü
07:23      ── Kanal sağlığı ölçümü
09:15      ── Kapak yenileme (eski videolardan 3 tanesi)
pazartesi 07:00 ── Haftalık rapor
pazar     04:17 ── Arşiv ↔ kanal eşitleme
```

**Cron çakışması yok** — 7 farklı saat dilimi, hiçbiri üst üste binmiyor.

---

## 3. Bir videonun 12 adımı

### Adım 1 — Uyanma (tetikleyici)
`hourly_production.yml` → cron `0 */8 * * *`

GitHub cron'u **güvenilmez** (ölçüm: `*/10` fiilen günde 1-2 koşuya düştü).
Bu yüzden **birincil tetikleyici zincirleme**: koşu bitince ayrı bir job
8 saat uyur, sonra `workflow_dispatch` ile sonrakini açar. Cron sadece yedek.

### Adım 2 — Kota kapısı
`modules/kota_kapisi.py` — YouTube günlük kotası dolduysa (403 `quotaExceeded`)
tur **başarısız sayılmaz**, `exit 0` ile sessiz durur (`KOTA_DOLU_DAVRANIS=sessiz_dur`).

### Adım 3 — Eski video temizliği
`main_pipeline.py` satır 227 → `dusuk_izlenmeli_videolari_temizle()`

- `IZLENME_KONTROL_DK = 360` (6 saat) — **bu süreden eski**
- `MIN_IZLENME_ESIGI = 100` — **bu eşiğin altında**
- İkisi birden → `videos.delete` ile silinir, arşivde `silindi_dusuk_izlenme`

> ⚠️ `CANLI_TEST=1` ise bu adım **atlanır** — test kanalda video silmez.

### Adım 4 — Konu seçimi (8 kategori, rotasyonlu)
`modules/ilginc_bilgi/kategoriler.py`

```
bilim_teknoloji · tarih_medeniyet · doga_evren · hayvanlar
insan_vucudu · yiyecekler · kulturler · gunluk_yasam
```

Son 6 videonun kategorisi **geriye atılır** → aynı kategori tekrar etmez.
Her videonun kategorisi `bobi_tv/state/ilginc_bilgi_gecmisi.json`'a yazılır
(tekrar önleme: MD5 + anahtar).

### Adım 5 — Senaryo üretimi (Gemini web)
`modules/ilginc_bilgi/uretici.py` → `modules.gemini_web.metin_uret()`

- Etkileşim taktiği seçilir (merak / şok / soru / itiraz)
- Gemini'ye kategori + taktik + "kaçırılacaklar" listesi verilir
- Dönen metin **temizlenir**: `sablon_yankisi_mi()`, `_sablon_izini_sil()`,
  `_prompt_kuyrugunu_sil()`, `_ingilizce_onyuzu_at()`, `_arayuz_kirliligini_sil()`
  → Gemini'nin "İşte senaryonuz:" gibi ön yüzleri atılır
- `dogruluk.py` ile doğruluk kontrolü

**Gemini erişilemezse** → `yedek_bilgiler.py` / `yedek_bilgiler_2.py` havuzundan
gerçek bilgi kullanılır. **Uydurma yok** — yedek havuz da gerçek bilgilerden oluşur.

### Adım 6 — Kanca (hook) motoru
`modules/senaryo_v7/kanca_motoru.py` + `hook_engineer.py`

İlk 1.5 saniyede izleyiciyi tutacak form seçilir. `kalite_kapisi.py` ve
`loop_validator.py` senaryoyu denetler (seamless loop: son cümle başa bağlanır).

### Adım 7 — Seslendirme (TTS)
`modules/tts_engine.py` satır 419 → `senaryo_seslendir(paket)`

- `tr-TR-AhmetNeural` (erkek) + `tr-TR-EmelNeural` (kadın) çift ses
- `WordBoundary` zaman damgaları alınır (karaoke altyazı için)
- `silenceremove` ile cümle başı/sonu ölü sessizlik kırpılır
- Zaman damgaları 0 ms kaymayla yeniden kalibre edilir

### Adım 8 — Render
`modules/video_render.py` satır 251 → `video_render(paket)`

```
1080×1920 · 30 FPS · H.264 + AAC
```

`modules/animasyon.py` (satır 24-25: `W, H = 1080, 1920`, `FPS = 30`):
- Vektörel karakter portreleri (emoji kutusu `□` çıkmasın diye)
- Kutulu karaoke altyazı (Türkçe `i→İ`, `ı→I` kuralına uygun)
- SFX: `whoosh`, `pop`, `vine_boom`, `riser`, `ding`
- Sidechain BGM → konuşma sırasında `-20 dB`, çıkış `-14 LUFS`
- Twist darbesi: zoom %118 + shake + kırmızı bant

Sonra `video_kalite_kontrol()` (ffprobe): çözünürlük/süre/ses akışı doğrulanır.

### Adım 9 — KAPAK (en kritik, bugünkü düzeltme)
`modules/kapak_hatti.py` → `kapak_uret_ve_yerlestir(paket)`

```
Gemini web çerezi (GEMINI_COOKIES)
   ↓ gorsel_uret(istem)
1080×1920 görsel indir
   ↓ gorseli_karesine_oturt()
kapak_gorsel.py — pikseli 9:16'ya oturt
   ↓ kapak_arena.ilk_kareye_yerlestir()
ffmpeg: trim=end_frame=45 → 1.5 saniye 1. kare
   ↓
paket["final_video"] = ..._kapakli.mp4   ← 2026-11-13 DÜZELTMESİ
```

**İstem (K8 — kullanıcının tek cümlesi, ek kural yok):**
```
<video başlığı> İsimli short video için kapak fotoğrafı istiyorum; etkileşim ve
izlenme rekorları kırması için profesyonel şekilde tasarla. Kapak fotoğrafını
gören merak edip tıklasın.
```

**Neden kritik:** 2026-11-13'e kadar `paket["final_video"]` güncellenmiyordu →
kapak `_kapakli.mp4`'e gömülüyor, YouTube'a **kapaksız orijinal** gidiyordu.
Log "gömüldü: EVET" diyordu. Artık güncelleniyor.

**Gemini erişilemezse** → videonun kendi karesi kapak olur
(`kaynak=video_karesi`). Üretim durmaz, uydurma yok.

### Adım 10 — YouTube yükleme
`modules/youtube_upload.py` satır 443 → `video_yukle(paket)`

- `paket["final_video"]` okunur (artık kapaklı dosya)
- Resumable upload (`uploadType=resumable`)
- `snippet` + `status` (privacy, category, madeForKids)
- **`thumbnails.set`** → kapak JPG ayrıca yüklenir (`_kapak_yukle`, satır 406)
- **İlk yorum** otomatik atılır (`_ilk_yorum_at`, satır 373):
  *"Siz olsanız ne yapardınız? Yorumlara yazın 👇"*

### Adım 11 — Arşiv
`bobi_tv/archive/videos.json` — tek gerçek kayıt defteri

Her video için: `video_id`, `baslik`, `durum`, `hash`, `kategori`,
`kanca_formu`, `kanca_puan`, `kapak_dosyasi`, `kapak_yuklendi`, `izlenme_snapshots`

**Kayıtlar asla silinmez** — `durum` alanıyla işaretlenir:
`yayinda` · `silindi_dusuk_izlenme` · `kaldirildi`

### Adım 12 — Telegram bildirimi
`modules/telegram_notify.py` → `send_message()`

Yayın linki + kapak kaynağı + süre bilgisi gönderilir.

---

## 4. Telegram kontrol paneli

`modules/telegram_bot.py` (132 KB — en büyük modül) · `telegram_bot.yml` her 5 dk

Kalıcı alt klavye (6 düğme):

| Düğme | Ne yapar |
|---|---|
| 📊 **Durum** | Canlı sistem durumu |
| 🎬 **Üret** | Elle üretim menüsü |
| 📈 **Rapor** | Performans raporu |
| ⚙️ **Ayarlar** | Ayar kataloğu (kadans, eşikler) |
| 📦 **Stok** | Kota kuyruğundaki bekleyen videolar |
| ❓ **Yardım** | Komut listesi |

Komutlar: `/start` `/menu` `/status` `/stats` `/trigger` `/app` `/mini` `/help`
Web app (Mini App): GitHub Pages'te `/mini`

**Ayar değişikliği** `bobi_tv/state/ayarlar.json`'a yazılır → pipeline okur.
Ama **workflow cron'u ayrı** — kadans değişirse YAML da güncellenmeli.

---

## 5. Mevcut durum (ölçülmüş)

### Kanal
```
BOBİ TV (UCJzCURUGVP3-baKe7N9FNjw)
13 video · 2 abone · 6.136 izlenme
```

### Son ölçüm (2026-11-12 16:03)
`bobi_tv/state/kanal_sagligi.json`:
```
7 günde: 55 üretilen · 30 silinen
ortalama izlenme: 6.88 · medyan: 0.0 · en yüksek: 99
```

> Bu, kanalı yakan rejimin (15 dakikada bir yükle, 1 saatte sil) **fotoğrafı**.
> 8 saatlik rejim 11 Kasım'da başladı — etkisi henüz ölçülmedi (3-5 gün gerek).

### Arşiv (65 kayıt)
| durum | adet |
|---|---:|
| `silindi_dusuk_izlenme` | 37 |
| `yayinda` | 18 |
| `kaldirildi` | 9 |

### GitHub
| | |
|---|---|
| Workflow | **13** (hepsi aktif) |
| Koşu geçmişi | 0 (temizlendi) |
| Test | 679 passed, 1 skipped |
| Aktif secret | GEMINI_COOKIES, YOUTUBE_TOKEN, YOUTUBE_CLIENT_SECRET, TELEGRAM_*, GH_PAT, PEXELS_API_KEY |
| Ölü secret | ARENA_COOKIES_JSON, GEMINI_API_KEY, LMARENA_EMAIL, LMARENA_PASSWORD |

---

## 6. Dış bağımlılıklar

| Servis | Ne için | Kopma etkisi |
|---|---|---|
| **Gemini web çerezi** | Senaryo + kapak + yorum cevabı | 🔴 **Kritik** — ~2-4 haftada düşer, `tools/gemini_cerez_kur.py` ile yenilenir |
| YouTube Data API | Yükleme, kapak, silme, istatistik | 🔴 Kota dolarsa tur `exit 0` ile durur |
| Telegram Bot API | Panel + bildirim | 🟡 Panel çalışmaz, üretim devam eder |
| GitHub Actions | Tüm çalışma | 🔴 Cron gecikir (zincirleme yedek) |
| Pexels API | B-roll arka plan | 🟢 Opsiyonel — yoksa stok video kullanılmaz |

---

## 7. Bilinen açık sorunlar

| # | Sorun | Durum |
|---|---|---|
| 1 | Animasyon şablonunda değişken interpolasyonu bozuk → 1. karede ve video başlığında `{` karakterleri | ⚠️ **AÇIK** |
| 2 | `EQPd1GlVCMw` videosunun başlığı `{ #shorts` | ⚠️ **AÇIK** — `videos.update` ile düzeltilebilir |
| 3 | **Süre ↔ izlenme ters ilişkisi:** 20 sn'lik videolar 1.100+ izlenme, 1-2 dk'lık videolar 0-14 | ⚠️ **AÇIK** — araştırılmadı |
| 4 | YouTube Shorts rafında (`oar2.jpg`) kapak API ile değiştirilemiyor | 🔒 **Sınır** — Studio'da elle |
| 5 | 8 saatlik kadansın izlenmeye etkisi | ⏳ Ölçüm bekliyor |

---

## 8. Doğrulama komutları

```bash
# Test
python3 -m pytest -q                          # 679 passed, 1 skipped

# Gemini çerezi canlı mı
PYTHONPATH=. python3 -c "from modules import gemini_web; print(gemini_web.durum())"

# Kanalın gerçek envanteri (API'den — arşivden DEĞİL)
python3 tools/kanal_envanteri.py

# Kapak gerçekten yüklendi mi (piksel farkı)
python3 atolye/kapak_denetle.py <VIDEO_ID>

# Workspace bütçesi
python3 tools/disk_bekci.py

# Yerel üretim (yüklemeden)
YUKLEME_ATLA=1 GUNLUK_HEDEF=1 python3 main_pipeline.py
```

---

## 9. Bilinçli olarak YAPILMAYANLAR

| Yapılmayan | Neden |
|---|---|
| Arena AI | Çerez 401, tarayıcı duvarı — çöpe atıldı (kullanıcı kararı) |
| Gemini API | Görsel kotası `limit: 0` |
| Otomatik çerez yenileme | Bir kez secret'ı bozdu; elle yenileme daha güvenli |
| Shorts rafı kapağı | API erişimi yok |
| Sesli/görsel AI (Sora, Veo vb.) | Eklenmedi — maliyet/kota belirsiz |
