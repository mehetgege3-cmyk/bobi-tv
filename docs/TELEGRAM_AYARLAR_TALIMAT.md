# BOBİ TV — Telegram Ayarlar Sistemi: Birleşik Uygulama Talimatı

**Sürüm:** 1.0 · **Tarih:** 2026-11-10 · **Hedef dal:** `main` (testler yeşilse doğrudan push)
**Kapsam:** Tetikleme + kota + diğer çalışan ayarlar için hiyerarşik Telegram menüsü.
**Kapsam dışı:** C2–C4, H1–H8, SKILL.md/README düzenlemesi, kanal/arşiv işleri.

---

## 0. BAŞLAMADAN ÖNCE: 4 ÖN KOŞUL

Bunları **önce** ölç, sonucu commit mesajına yaz. Ölçmeden koda dokunma.

| # | Kontrol | Nasıl | Değilse ne yap |
|---|---|---|---|
| **P1** | `trigger_production()` gerçekten çalışıyor mu? | `GH_PAT` secret tanımlı mı? Bot "Üret"e basınca `hourly_production.yml` koşuyor mu? | Çalışmıyorsa "Üret" düğmesi ölü. Paneli buna göre kur, raporda **bildir**. |
| **P2** | State push'u gerçekten gidiyor mu? | `telegram_bot.yml` içindeki `git push origin main \|\| echo "Push atlandı"` | `\|\| echo` **kaldır**, başarısızlıkta `exit 1`. Yoksa panelde değiştirdiğin ayar sessizce kaybolur. |
| **P3** | Baz sayılar | `pytest -q` → **679 passed + 1 skipped** beklenir | Farklıysa gerçek sayıyı ölç, talimattaki 679'u düzelt, raporda yaz. |
| **P4** | Kota matematiği | YouTube 10.000 birim/gün, `videos.insert` ≈1600 → **günde en fazla 6** | Kodda `GUNLUK_MAKS` üst sınırı **6** olacak. |

---

## 1. TEMEL KURALLAR (ihlal edilemez)

1. **Test silme / skip'leme / gevşetme yasak.** Gevşek `>=` assert yazma; tam değer yaz ya da testi hiç yazma. Baz **679 passed + 1 skipped** korunur, üstüne eklenir.
2. **Secret değeri** mesajda, commit'te, logda, hata çıktısında, state'te **görünmeyecek.** Sadece "tanımlı / eksik".
3. **`force-push`, `rm -rf`, `git reset --hard` yasak.**
4. **`|| echo "Push atlandı"` kalıbı yasak** — push başarısızlığı sessizce yutulmaz.
5. Yapılamayan her madde commit mesajına `YAPILMADI: <sebep>` olarak yazılır.
6. Otomatik ToS kabulü yok (`ACCEPT_TOS=1` verilmedikçe basılmaz).
7. `videos.json`'a kota/kuyruk/hata durumu **yazılmaz**; sadece geçerli `video_id` ile yayın kaydı.

---

## 2. MİMARİ KARARI (tek doğruluk kaynağı)

Ayarlar **commit'li bir JSON dosyasında** yaşar, workflow başında `$GITHUB_ENV`'e aktarılır.

```
bobi_tv/state/ayarlar.json   ← tek doğruluk kaynağı (bot yazar, commit eder)
        │
        ▼
hourly_production.yml → "Ayarları yükle" adımı → $GITHUB_ENV
        │
        ▼
main_pipeline.py / modüller → os.environ.get(...)   ← DEĞİŞMEZ
```

**Neden env'e yazmıyoruz:** bot her koşuda temiz klon; env koşuyla ölür.
**Neden `workflow_dispatch` inputs değil:** sadece elle tetiklemede gelir, cron koşusunda payload yok → iki kaynak olur.
**Neden commit:** ayarlar seyrek değişir (günde birkaç kez), offset gibi her koşuda değil → git tarihi çöpü riski yok.

**Öncelik sırası:** `ayarlar.json` > `env` > katalog varsayılanı. Panelde hangi katmandan geldiği gösterilir (`6 (state)` / `24 (varsayılan)`).

---

## 3. TODO 1 — AYAR KATALOĞU (tek kaynak)

`modules/ayar_katalogu.py` oluştur. Her ayarın alanları:
`anahtar, etiket, grup, tip, secenekler, varsayilan, min, max, env_adi, risk, kalici, etkili`

`tip`: `secim` | `sayi` | `anahtar` (aç/kapa) | `sadece_goruntule`
`risk`: `dusuk` | `orta` | `yuksek`
`kalici`: ayarın state'e yazılıp yazılmayacağı
`etkili`: değerin gerçekten pipeline'ı etkileyip etkilemediği (aşağıda Grup 3 = `False`)

### 🚀 Grup 1 — `tetikleme`

| anahtar / env_adi | etiket | tip | seçenekler | varsayılan | risk | kalıcı |
|---|---|---|---|---|---|---|
| `YUKLEME_ATLA` | Render testi (yükleme yok) | anahtar | — | `0` | düşük | ✅ |
| `MOD` | Üretim modu | secim | `isindirma_saatlik`, `normal` | `isindirma_saatlik` | düşük | ✅ |
| `force` | Kota kapısını atla | anahtar | — | `0` | **yüksek** | ✅ |

> `force` tek seferlik bir eylem olduğu için uygulandıktan sonra **otomatik `0`'a döner** (kalıcı değil, tek kullanım).

### 🎯 Grup 2 — `uretim_kota`

| anahtar / env_adi | etiket | tip | seçenekler / aralık | varsayılan | risk |
|---|---|---|---|---|---|
| `GUNLUK_HEDEF` | Günlük hedef | secim | `1`, `2`, `4` | `1` | düşük |
| `GUNLUK_MAKS` | Günlük üst sınır | secim | `2`, `5`, `6` | `6` | orta |
| `KOTA_DOLU_DAVRANIS` | Kota dolunca | secim | `sessiz_dur`, `hata` | **`sessiz_dur`** | **yüksek** |
| `KOTA_REZERV` | Kota rezerv eşiği (birim) | sayi | 0–2000 | `500` | düşük |

> `GUNLUK_MAKS` katalogunda **7 ve üstü seçenek YOK**. Kodda ayrıca savunma: `min(deger, 6)` + log uyarısı. (Kota matematiği: 10000/1600 = 6.)

### 🧹 Grup 3 — `temizlik` (SADECE GÖRÜNTÜLE — `etkili=False`)

| anahtar / env_adi | etiket | tip | mevcut değer | risk |
|---|---|---|---|---|
| `OTOMATIK_SIL_AKTIF` | Otomatik silme | sadece_goruntule | `1` | yüksek |
| `MIN_IZLENME_ESIGI` | Minimum izlenme eşiği | sadece_goruntule | `100` | yüksek |
| `IZLENME_KONTROL_DK` | İzlenme kontrol süresi | sadece_goruntule | `1440` | düşük |

**Zorunlu açıklama metni (pan bu metni gösterecek):**
> ⚠️ Bu değeri değiştirmek otomatik temizlemeyi ETKİLEMEZ. Temizleme workflow'u kendi sabitini kullanıyor (`cleanup_low_views.yml` → `if views < 100`). Bilinen sorun (H1), ayrı görevde çözülecek.

Bu grupta **hiçbir düğme değişiklik yapmaz**; sadece değer gösterir + "neden değiştirilemiyor" açıklar. Yalan söyleme: etkisiz olana "etkili" deme.

### ⚙️ Grup 4 — `sistem` (SADECE GÖRÜNTÜLE, değer asla yazdırılmaz)

`GEMINI_COOKIES`, `YOUTUBE_TOKEN`, `YOUTUBE_CLIENT_SECRET`, `PEXELS_API_KEY`, `GH_TOKEN`, `TELEGRAM_BOT_TOKEN` → panelde yalnız `✅ tanımlı` / `⛔ eksik` + kaynak (`GitHub Secrets`).

### Katalogdan ÇIKARILANLAR (gerekçeli)

| Ayar | Neden çıkarıldı |
|---|---|
| `TETIK_DK` (tetikleme sıklığı) | GitHub cron fiilen çalışmıyor (bugün 16 saat koşu yok). "10 dk" ayarı **yalan** olur. Yerine Grup 4'te tetikleyici sağlık satırı var. |
| `SESSIZ_SAAT` | Zaman dilimi + cron güvenilmezliği birleşince doğrulanamaz. Tetikleyici kurulduktan sonra eklenir. |
| `OTOMATIK_URETIM` | `repository_dispatch`'i çağıran yok; kapatma düğmesi işlevsiz olur. Tetikleyici kurulunca eklenir. |

**Testler (TODO 1):** her ayarın `env_adi` dolu · `sadece_goruntule` tiplerinde `secenekler`/`min`/`max` yok · hiçbir secret'ın varsayılan değeri yok · `GUNLUK_MAKS` seçeneklerinin maksimumu `6` · Grup 3 ayarlarının `etkili is False`.

---

## 4. TODO 2 — STATE DOSYASI (atomik + şema doğrulamalı)

`bobi_tv/state/ayarlar.json`:

```json
{"sur": 1, "guncelleme": "<ISO>", "ayarlar": {"GUNLUK_MAKS": 6}}
```

**Zorunlu davranışlar:**

- **Atomik yazma:** `tmp` dosyaya yaz → `os.replace()`. Yarıda kesilirse eski dosya bozulmaz.
- **Yükleme toleranslı:** bilinmeyen anahtar → yok say + logla. Aralık dışı → varsayılana dön + logla + panelde uyarı. **Asla exception fırlatıp botu düşürme.**
- **C4 dersini tekrarla:** bozuk JSON'da `ayarlar={}` ile **EZME**. Bozuk dosyayı `ayarlar.json.bozuk` olarak sakla, varsayılana dön, panelde kırmızı uyarı ver. (`arsive_ekle`'nin `except: arsiv=[]` hatasını tekrarlama.)
- `sur` (şema sürümü) yaz; okurken farklıysa uyar + varsayılan.

**Testler:** bozuk JSON → çökmez, varsayılan + uyarı · yarıda kesilen yazma eski dosyayı bozmaz · aralık dışı değer reddedilir ve varsayılan döner · yokluk → varsayılan.

---

## 5. TODO 3 — MENÜ HİYERARŞİSİ (callback_data şeması)

**Altın kural:** `callback_data` **asla değer taşımaz, sadece kimlik taşır.** Değer sunucuda katalog + state'ten çözülür. Böylece `a:s:gmax:9999` gibi elle uydurulmuş payload işe yaramaz.

| callback_data | Anlam |
|---|---|
| `menu_main` | Ana menü |
| `ay:kok` | Ayarlar ana ekranı |
| `ay:g:<grup>` | Grup ekranı (`tetikleme` \| `uretim_kota` \| `temizlik` \| `sistem`) |
| `ay:s:<anahtar>` | Ayar detayı |
| `ay:v:<anahtar>:<indeks>` | Seçenek uygula (**indeks**, değer değil) |
| `ay:onay:<anahtar>` | Riskli ayar onay ekranı |
| `ay:gecmis` | Son değişiklikler |
| `ay:test:<anahtar>` | Ayarın ön izlemesi (dry-run) |

**Ana menü 6 düğmeden 4'e iner:**

```
[📊 Durum]  [🎬 Üret]
[📈 Rapor]  [⚙️ Ayarlar]     ← İstatistik + Kalite + Kota "Rapor" altına girer
```

**Ayarlar ana ekranı (3 derinlik sınırı):**

```
⚙️ AYARLAR
🚀 Tetikleme       (3 ayar)
🎯 Üretim & Kota   (4 ayar)
🧹 Temizlik        (görüntüle)
🔑 Sistem durumu   (secret var/yok, son koşu, tetikleyici sağlığı)
[← Geri] [🏠 Menü]
```

**Kurallar:** her ekranda `[← Geri]` + `[🏠 Menü]` · düğme metni ≤20 karakter · derinlik ≤3 · bilinmeyen `callback_data` → "Bilinmeyen komut" + menüye dön, **çökme yok**.

**Testler:** her `callback_data` ≤64 byte · her ekranın geri yolu var · derinlik ≤3 · bilinmeyen payload çökmeden menüye dönüyor · ana menüde tam **4** düğme var.

---

## 6. TODO 4 — TEK MESAJ KURALI (edit-in-place, istisnasız)

Panelde **her** etkileşim aynı mesajı düzenler: `editMessageText` + `reply_markup`.
Yeni mesaj **sadece**: (a) menü mesajı >48 saat (Telegram limiti), (b) kullanıcı `/start` yazdı.

`"message is not modified"` hatası yakalanır ve sessizce yutulur (hata sayılmaz).
Mevcut `editMessageReplyMarkup` yolu (`telegram_bot.py:228-236`) korunur, `editMessageText`'e genişletilir.

**Test:** 10 ardışık tıklama → **tam olarak 1** `sendMessage`, **9** `editMessageText`.
`/start` → yeni mesaj. 48 saatten eski mesaj → yeni mesaj.

---

## 7. TODO 5 — RİSKLİ AYARLAR: onay + dry-run

`risk="yuksek"` ayarlar (`force`, `KOTA_DOLU_DAVRANIS`) tek dokunuşla değişmez:

```
⚠️ "Kota kapısını atla" günlük yükleme sınırını aşar.
   Bu ayar bugünkü ~3 yüklemeyi zorlar. Emin misin?
   [✅ Onayla]  [← Vazgeç]
```

Onay ekranı **gerçek etkiyi hesaplar** (silme simülasyonu yapıyorsa **SİLMEZ**).
`force` için dry-run: "bu ayarla şu an 1 yükleme daha yapılır, kota şu kadar kalır".

**Test:** risk=yuksek ayar onay olmadan uygulanmıyor · "Vazgeç" → state **bit bit aynı** · dry-run hiçbir dosya silmiyor/mü ykleme yapmıyor (mock ile doğrula).

---

## 8. TODO 6 — DEĞİŞİKLİK KAYDI

`bobi_tv/state/ayar_gecmisi.jsonl` — append-only, **son 200 satır** (dönen dosya `ayar_gecmisi.1.jsonl`'e taşınır).

Satır şeması:
```json
{"zaman":"<ISO>","kullanici_id":<id>,"anahtar":"GUNLUK_MAKS","eski":24,"yeni":6,"kaynak":"telegram"}
```

Panelde "🕘 Son değişiklikler" ekranı (son 10): `GUNLUK_MAKS: 24 → 6 · 3 dk önce`.

**Test:** değişiklik yazılıyor · `sadece_goruntule` ayarlar geçmişe **yazılmıyor** · 200 satır sınırı uygulanıyor.

---

## 9. TODO 7 — SECRET SINIRI (ihlal edilemez)

Hiçbir secret'ın değeri mesajda, commit'te, logda, hata çıktısında, state'te görünmez.
Panel yalnız `✅ tanımlı` / `⛔ eksik` gösterir.

**Test:** tüm panel ekranlarını üret (her grup + her ayar detayı + onay + geçmiş) ve çıktıda şu desenleri ara → **0 eşleşme**:
`ghp_`, `github_pat_`, `AIza`, `ya29.`, 40+ karakter base64 blok, `Bearer `.

---

## 10. TODO 8 — KALICILIK (ayarlar kaybolmasın)

- `ayarlar.json` **offset ile aynı commit'e konmaz** (biri kaybolursa diğeri de gider).
- Ayarlar için ayrı, **anında** commit+push (seyrek değiştiği için çöp üretmez).
- Push **başarısız** olursa: `bobi_tv/state/ayarlar_bekleyen.json`'a yaz, panelde `⚠️ kaydedilemedi, tekrar denenecek` göster, sonraki koşuda tekrar dene.
- Push başarısızlığı `|| echo` ile **yutulmaz** → `exit 1`.

**Test:** push mock'u başarısız → bekleyen kuyruğa giriyor, state bozulmuyor · sonraki koşuda tekrar deneniyor ve başarılıysa kuyruk temizleniyor · offset ve ayarlar **ayrı** commit'lerde.

---

## 11. TODO 9 — AYAR → ENV KÖPRÜSÜ (tek yeni adım, en kritik)

`hourly_production.yml`'e pipeline'dan **önce** bir adım ekle:

```yaml
- name: Ayarları state'ten yükle
  run: |
    # bobi_tv/state/ayarlar.json → doğrula → $GITHUB_ENV
    # SADECE secret olmayan ayarlar köprüden geçer
```

Sonra pipeline adımından (`hourly_production.yml:202-206`) şu **5 sabit satırı SİL**:

```yaml
GUNLUK_HEDEF: '1'
GUNLUK_MAKS: '24'
MOD: 'isindirma_saatlik'
OTOMATIK_SIL_AKTIF: '1'
# Silme eşiği TEK KAYNAK: ... (yorum satırı)
```

Secret satırları (`GEMINI_COOKIES`, `YOUTUBE_TOKEN`, `TELEGRAM_BOT_TOKEN`, `PEXELS_API_KEY`) **kalır** — köprü bunlara dokunmaz.

**Testler:** `ayarlar.json`'daki değer pipeline'ın gördüğü env'e yansıyor · workflow'da `GUNLUK_MAKS:`/`GUNLUK_HEDEF:` **sabit yazısı kalmadı** (grep assert) · köprü adımı secret'ları env'e yazmıyor · `ayarlar.json` yoksa varsayılanlar uygulanıyor.

---

## 12. TODO 10 — KOTA KAPISI

- `GUNLUK_MAKS` üst sınırı **6** (10000/1600). Katalogda 7+ yok, kodda `min(deger, 6)` + log.
- `KOTA_DOLU_DAVRANIS`:
  - `sessiz_dur` → **`sys.exit(0)`** (varsayılan). C2'deki `exit(1)` → self-repair fırtınasını (günde ~144 deneme + main'e otonom push) durdurur.
  - `hata` → mevcut `exit(1)` davranışı korunur (kırmızı tik).
- Panelde kota durumu: `Kota: 4800/10000 birim · ~3 yükleme kaldı` — `bobi_tv/state/youtube_quota.json`'dan. Dosya yoksa **"bilinmiyor"** yaz, sayı uydurma.

**Testler:** `GUNLUK_MAKS=24` verilse bile etkin değer **6** · `sessiz_dur` → `exit(0)` · `hata` → `exit(1)` · kota dosyası yokken panel "bilinmiyor" diyor (uydurma sayı yok).

---

## 13. TODO 11 — TEMİZLİK GRUBU: değiştirilemez + dürüst uyarı

Grup 3 ayarları `tip="sadece_goruntule"`, `etkili=False`. Panelde **TODO 1'deki uyarı metni** gösterilir. Değiştirme düğmesi **yok**.

**Test:** temizlik ayarı için hiçbir değiştirme `callback_data`'sı üretilmiyor · uyarı metni panel çıktısında var · `etkili is False` assert'i.

---

## 14. TODO 12 — YÜKLEMSİZ TEST DÜĞMESİ (en yüksek fayda/maliyet)

Ayrı düğme: **`🧪 Render testi (YouTube'a yükleme YOK)`**

`repository_dispatch` çağrısı:
```json
{"event_type": "bobi-tv-produce",
 "client_payload": {"yukleme_atla": "1", "force": "true"}}
```

Panelde sonuç: süre · çıktı dosyası boyutu · QC sonucu · "yükleme yapılmadı".

> Bu düğme, **"video üretiliyor mu?"** sorusunu kotasız ve yayınsız cevaplar. Canlı kanalı riske atmadan doğrulama yolu budur.

**Testler:** dispatch payload'ında `yukleme_atla=1` · workflow payload'ı env'e çeviriyor · `YUKLEME_ATLA=1` iken yükleme adımı çağrılmıyor (mock) · sonuç mesajı "yükleme yapılmadı" içeriyor.

---

## 15. DEĞİŞECEK DOSYALAR

| Dosya | İşlem |
|---|---|
| `modules/ayar_katalogu.py` | **YENİ** — TODO 1 |
| `modules/ayar_deposu.py` | **YENİ** — TODO 2, 6, 8 (atomik yazma, şema, geçmiş, bekleyen kuyruk) |
| `modules/telegram_bot.py` | Menü hiyerarşisi, edit-in-place, onay ekranları, test düğmesi (TODO 3,4,5,12) |
| `.github/workflows/hourly_production.yml` | Köprü adımı + 5 sabit satırın silinmesi + `KOTA_DOLU_DAVRANIS` (TODO 9,10) |
| `.github/workflows/telegram_bot.yml` | `\|\| echo` kaldır, `exit 1`; ayarlar commit yolu (TODO 8, P2) |
| `main_pipeline.py` | `min(GUNLUK_MAKS,6)` + `KOTA_DOLU_DAVRANIS` kapısı (TODO 10) |
| `bobi_tv/state/ayarlar.json` | **YENİ** — ilk sürüm katalog varsayılanlarıyla |
| `tests/test_ayar_katalogu.py` | **YENİ** |
| `tests/test_ayar_deposu.py` | **YENİ** |
| `tests/test_telegram_menu.py` | **YENİ** |
| `tests/test_kota_kapisi.py` | **YENİ** |
| `docs/AYARLAR.md` | **YENİ** — hangi ayar ne yapar, hangisi neden etkisiz |

**Dokunulmayacaklar:** `modules/youtube_upload.py`, `modules/kota_state.py` (okuma dışında), `.github/workflows/cleanup_low_views.yml`, `tests/test_archive_integrity.py`, `SKILL.md`, `README.md`, `bobi_tv/archive/videos.json` (şema), `bobi_tv/queue/`.

---

## 16. KABUL KRİTERLERİ (hepsi geçmeden push yok)

1. `pytest -q` → **≥679 passed, 1 skipped**; hiçbir test silinmemiş/skip'lenmemiş.
2. `ruff check` yeni dosyalarda temiz; `mypy` toplam hata sayısı **bazın üstüne çıkmıyor** (baz: 185).
3. `grep -c "GUNLUK_MAKS:" .github/workflows/hourly_production.yml` → **0**.
4. `grep -c '|| echo "Push atlandı"' .github/workflows/telegram_bot.yml` → **0**.
5. Tüm panel ekranlarında secret deseni taraması → **0 eşleşme** (TODO 7 testi).
6. Katalogda `GUNLUK_MAKS` seçeneklerinin maksimumu **6**.
7. Ana menüde **4** düğme; her `callback_data` ≤64 byte; derinlik ≤3.
8. 10 tıklama → 1 `sendMessage` + 9 `editMessageText`.
9. `docs/AYARLAR.md` hangi ayarın etkisiz olduğunu **açıkça** yazıyor (H1 referansıyla).

---

## 17. COMMIT PLANI (5 commit, her biri kendi testleriyle)

```
1. feat(ayarlar): ayar kataloğu — tek doğruluk kaynağı (TODO 1)
2. feat(ayarlar): atomik state deposu + şema + değişiklik geçmişi (TODO 2,6,8)
3. feat(telegram): hiyerarşik ayarlar menüsü + tek mesaj kuralı + onay (TODO 3,4,5,7)
4. ci(ayarlar): state→env köprüsü; sabit değerler kaldırıldı (TODO 9, P2)
5. feat(kota): GUNLUK_MAKS tavanı 6 + KOTA_DOLU_DAVRANIS + render testi düğmesi (TODO 10,11,12)
```

Her commit mesajının sonunda: `Baz: 679 passed + 1 skipped → Şimdi: N passed + 1 skipped`.
Yapılamayan madde varsa: `YAPILMADI: <sebep>`.

---

## 18. BİLİNEN SINIRLAR (dürüstlük notu — rapora da yaz)

1. **Bu talimat video üretmez.** Üretim, harici tetikleyicinin (cron-job.org → `repository_dispatch`) kurulmasına bağlı. Panel ne kadar iyi olursa olsun, tetikleyici yoksa koşu olmaz.
2. **"Tüm ayarlar değiştirilebilir" mümkün değil.** 6 secret + YouTube kota limiti salt-okunur. Güvenlik sınırı, eksiklik değil: bot secret yazabilirse, bot ele geçirilirse kanal gider.
3. **Temizlik grubu şu an kozmetik.** H1 çözülene kadar değiştirilmesi gerçek davranışı değiştirmez; panel bunu açıkça söyler.
4. **Panel görselliği Telegram'ın sınırında.** Zengin görsel isteniyorsa çözüm PNG render + `sendPhoto`; bu talimatın kapsamı dışında.
5. **Push başarısızlığı hâlâ en büyük risk.** TODO 8 ve P2 bunu azaltır ama `repository_dispatch` + aynı anda iki koşu çakışırsa commit yarışı olabilir; TODO 8'deki bekleyen kuyruk bunu sınırlar, sıfırlamaz.
