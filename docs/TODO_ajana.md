# TODO — Ajan İçin Kalan İşler

Güncel: 2026-11-10. Bölüm 6'daki 7 madde **ZATEN YAPILDI** ve `f4d2ca1`
ile main'de; TEKRAR YAPILMAZ. Aşağıda yalnız gerçekten kalan işler var.

## ✅ Tamamlandı (Bölüm 6 — dokunma)

1. `models.py` `__all__` dışa aktarımı düzeltildi.
2. "şaşkın" duygu alias'ı eklendi.
3. "üzgün" duygu kararı (kullanılmıyor, kasıtlı NORMAL fallback) dokümante edildi.
4. Karaoke testi zayıflatıldı (tam boyut eşitliği 960×210).
5. Skip'li render testi v7 API ile yeniden yazıldı.
6. Telegram paneline HTML escape (tek nokta, `<b>` etiketleri korunur).
7. pyflakes artıkları temizlendi (kullanılmayan importlar, placeholder'siz f-string'ler).

## 🔴 Kalan (öncelik sırası)

### 1. Canlı cookie ile uçtan uca Arena doğrulaması
- `arena-selftest.mjs` ve `arena-ask.mjs` sahte cookie ile statik olarak
  doğrulandı; canlı oturumla test edilmedi.
- Yapılacak: geçerli `ARENA_COOKIES_JSON` ile `arena_smoke_test.yml`'i
  manuel tetikle, exit 0 bekle. ToS duvarı çıkarsa `ACCEPT_TOS=1` ile.
- Exit 2 (oturum-gecersiz) gelirse cookie'yi Cookie-Editor ile yenile.

### 2. Çerez yenileme — Seçenek B (önerilen sonraki adım)
- Otomatik yenileme şu anda KAPALI (Bölüm 3-A: kırık zincir kaldırıldı).
- B: `_guncel_cerezleri_kaydet` doğru **normalize JSON** formatında yazsın
  (Cookie-Editor uyumlu, ham Set-Cookie değil) + GitHub App installation
  token ile `gh secret set`. Bkz. `docs/GITHUB_APP_TOKEN.md`.
- Ön koşul: yazılan formatın pipeline tarafından okunabildiği birim testi.

### 3. Çerez yenileme — Seçenek C (yarı-otomatik)
- Otomatik secret yazma yerine: cookie düştüğünde (smoke test exit 2)
  Telegram bot'u üzerinden uyarı gönder, kullanıcı onaylayınca manuel
  yenile. Daha güvenli, secret yazma izni gerektirmez.

### 4. Cron cadans gözlemi
- `hourly_production.yml` artık `*/10 * * * *`. GitHub scheduler fiilen
  daha seyrek çalışabilir; bir hafta koşu sayısı gözlemlenip günlük hedef
  (kota) ile kıyaslanmalı. Gerekirse günlük hedef düşürülür (artırılmaz).

### 5. Arşiv ↔ kanal periyodik eşitleme
- `videos.json` ile YouTube kanalının oembed ile periyodik (haftalık)
  karşılaştırılması; kaybolan videolar `durum: kaldirildi` olarak
  işaretlenmeli (silinmeden). Şu anda elle yapıldı (2026-11-10).

## Yapılmadıysa

Herhangi bir madde yapılamazsa commit mesajına `YAPILMADI: <sebep>` yaz;
sonraki maddeye geç. Bu dosyayı güncellemeyi unutma.
