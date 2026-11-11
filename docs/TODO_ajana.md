# TODO — Ajan İçin Kalan İşler

Güncel: **2026-11-11**. Bölüm 6'daki 7 madde `f4d2ca1` ile main'de; TEKRAR
YAPILMAZ. Bu dosya yalnız gerçekten kalan işleri tutar.

## ✅ Tamamlandı (Bölüm 6 — dokunma)

1. `models.py` `__all__` dışa aktarımı düzeltildi.
2. "şaşkın" duygu alias'ı eklendi.
3. "üzgün" duygu kararı (kullanılmıyor, kasıtlı NORMAL fallback) dokümante edildi.
4. Karaoke testi zayıflatıldı (tam boyut eşitliği 960×210).
5. Skip'li render testi v7 API ile yeniden yazıldı.
6. Telegram paneline HTML escape (tek nokta, `<b>` etiketleri korunur).
7. pyflakes artıkları temizlendi (kullanılmayan importlar, placeholder'siz f-string'ler).

## ✅ Bu turda kapatılanlar (2026-11-11)

### ~~Madde 3 — Çerez yenileme, Seçenek C (yarı-otomatik)~~ → YAPILDI
`modules/arena_cerez_uyari.py` + `arena_smoke_test.yml` içinde uyarı adımı.
- `oturum-gecersiz` / `cookie-yapilandirma-hatasi` verdict'inde Telegram'dan
  "çerezi yenile" uyarısı gider; 30 dakikada bir tekrar eder (spam yok).
- Otomatik secret yazma YOK; çerez yalnız kullanıcı eliyle değişir.
- Bildirim susturulmuşsa uyarı gönderilmez. Metinde çerez/token yok
  (yalnız secret'ın ADI: `ARENA_COOKIES_JSON`).
- Test: `tests/test_todo36_arena_cerez_uyari.py` (6 test).

### ~~Madde 4 — Cron cadans gözlemi~~ → YAPILDI (ölçüm)
`modules/cadans_olcum.py` + `.github/workflows/cadans_olcum.yml` (günlük).
- Cron ifadesine değil, GERÇEK koşu geçmişine bakar; 24 saatte kaç koşu,
  medyan aralık, beklentiye oran.
- Panel: 🛠 Sistem → `📉 Cadans: ⚠️ %30 (24sa: 43 koşu, medyan 15.0 dk)`.
- **Ölçüm (2026-11-11 12:00 UTC):**
  | workflow | beklenen | 24sa koşu | medyan aralık | oran |
  |---|---|---|---|---|
  | `hourly_production.yml` | 10 dk | 43 | 15.0 dk | %30 |
  | `telegram_bot.yml` | 5 dk | 7 | **148.4 dk** | %2 |
- **Yorum:** üretim cadansı cron hedefinin ~%30'u; poller ise fiilen ~2.5
  saatte bir koşuyor → kullanıcının "bot geç cevap veriyor" şikâyetinin
  kökü. Çözüm cron'a güvenmek değil, poller'ı sürekli ayakta tutmak
  (uzun ömürlü döngü zaten var; koşu süresi/kesinti oranı izlenmeli).
- **Poller için düzeltme yapıldı (2026-11-11):**
  1. `409 Conflict` kökü bulundu: 03:02 TR'de başlayan 5.5 saatlik koşu
     ayaktayken yeni koşu aynı token'la `getUpdates` çağırıyordu → iş
     düzeyi `concurrency: telegram-poller` kilidi + 409'da TEMİZ çıkış.
  2. Koşu bitince bir sonrakini başlatan yoktu → `success()` olduğunda
     `gh workflow run telegram_bot.yml` ile zincir; koruma: gerçek süre
     ≥ 30 dk değilse zincir YOK (dispatch fırtınası olmaz).
  3. Eski (kod öncesi) 03:02 koşusu iptal edildi; yeni poller `bcfc231`
     üzerinde çalışıyor — yeni menü artık canlı koda bağlı.
- Kalan insan kararı: günlük üretim hedefi bu gerçek cadansa göre
  DÜŞÜRÜLSÜN mü (artırılmasın) — hedef sayısı kullanıcı onayı ister.

### ~~Madde 5 — Arşiv ↔ kanal periyodik eşitleme~~ → YAPILDI
`modules/arsiv_esitleme.py` + `.github/workflows/arsiv_esitleme.yml` (haftalık).
- Kayıt SİLİNMEZ: kanaldan düşen video `durum: kaldirildi` + `kaldirilma_kaynagi`
  + `kaldirilma_tespit` alanlarıyla işaretlenir.
- İki bağımsız kontrol (oembed + watch sayfası). Çelişki = `bilinmiyor` →
  kayıt DEĞİŞMEZ. Ağ hatası/401/403 = `bilinmiyor`.
- Toplu kayıp koruması: kontrol edilenlerin TAMAMI yoksa (≥5 kayıt) veya tek
  koşuda 25'ten fazla kayıt yoksa eşitleme DURUR, arşiv olduğu gibi kalır.
- **İlk koşu (2026-11-11):** 13 geçerli kayıt kontrol edildi → **8 video
  kanalda YOKTU** (6'sı eşitleme ile işaretlendi; 2'si zaten işaretliydi).
  Arşivde `yayinda` görünen 8 kayıt kanalda bulunmuyordu; panel artık
  yalnız kanalda duran geçerli kayıtları "🚀 Yayında" sayıyor.
- Test: `tests/test_todo34_arsiv_esitleme.py` (9 test).

## 🔴 Kalan

### 1. Canlı cookie ile uçtan uca Arena doğrulaması — **KULLANICI GİRDİSİ GEREKİR**
- `arena-selftest.mjs` ve `arena-ask.mjs` sahte cookie ile statik doğrulandı;
  gerçek oturumla çalıştırılmadı. Benim elimde geçerli `ARENA_COOKIES_JSON`
  yok ve bu sandbox'ta Actions workflow tetikleme yetkim de yok.
- Yapılacak (kullanıcı): Actions → **Arena Smoke Test** → *Run workflow*
  (`accept_tos=1` gerekirse) → `exit 0` görülmeli.
- `exit 2` gelirse: çerez düşmüş demektir; **artık Telegram'a uyarı gelir**
  (madde 3). Cookie-Editor ile `arena-auth-prod-v1.0` yenilenir.

### 2. Çerez yenileme — Seçenek B (otomatik secret yazma) — **BLOKE**
- Şu an KAPALI ve bilinçli olarak açılmadı. Sebep: pipeline'ın yazılan
  çerezi okuyabildiğini kanıtlayan format testi yok; yanlış format çalışan
  secret'ı bozar. Ayrıca GitHub App kurulumu (`APP_ID`, `APP_PRIVATE_KEY`,
  `APP_INSTALLATION_ID`) kullanıcı tarafından yapılmalı — `docs/GITHUB_APP_TOKEN.md`.
- Ön koşul (kod tarafı, hazır): normalize JSON yazımı için birim testi.

### 3. ~~Cron cadans gözlemi~~ → kapandı (yukarıda); kalan: hedef kararı.

## Yapılmadıysa

Herhangi bir madde yapılamazsa commit mesajına `YAPILMADI: <sebep>` yaz;
sonraki maddeye geç. Bu dosyayı güncellemeyi unutma.
