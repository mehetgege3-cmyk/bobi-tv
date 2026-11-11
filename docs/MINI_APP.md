# Mini App (TODO 31) — tasarım + güvenlik sözleşmesi

Güncel: 2026-11-11 · Durum: **v1 hazır (statik kabuk + gerçek veri köprüsü)**

## 1. Neden Mini App?

Panel bir Telegram **botu**: her ekran için bir mesaj düzenleniyor, butonlar
9-12 karakterle sınırlı, tablo/grafik yok. Mini App (Telegram Web App) aynı
veriyi **tek ekranda, kaydırmalı, grafikli** gösterir — mesaj spam'i yok.

**KURAL:** Mini App v1, mevcut TEK PANEL'i **değiştirmez**, yanına eklenir.
Bot paneli çalışmaya devam eder (yedek yol). Faz 6 kuralı: "yalnız Faz 1-5
bitince ve kullanıcı onayıyla" → onay verildi (2026-11-11).

## 2. Barındırma gerçeği (dürüst sınır)

Telegram Mini App = **HTTPS ile erişilebilen bir web uygulaması**. GitHub Pages
uygun: statik, ücretsiz, HTTPS var. Sunucu tarafı (API) yok — bu yüzden:

| Veri | Kaynak | Tazelik |
|---|---|---|
| Üretim/yayın sayıları, trend | `bobi_tv/data/mini_app_ozet.json` (workflow commit eder) | son koşu |
| Stok (kuyruk) | aynı dosya (`kuyruk` alanı) | son koşu |
| Denetim kaydı (son 10) | aynı dosya (`denetim` alanı) | son koşu |
| Canlı butonlar (Üret/Sil) | **YOK** — v1 salt okunur | — |

**Neden salt okunur:** Mini App içinden üretim tetiklemek/ video silmek
tarayıcıda yaşayan bir token gerektirir → token'ın ele geçmesi = kanalın ele
geçmesi. v1'de yazma yok; yazma işlemleri bot panelinde (imzalı + süreli
callback + onay ekranı + denetim kaydı) kalır.

## 3. initData doğrulaması (v2 için hazır sözleşme)

Yazma açılırsa `Telegram.WebApp.initData` **sunucuda** doğrulanmalı:
`HMAC_SHA256(key=SHA256(bot_token), data_check_string)` + `auth_date` tazeliği
(≤ 1 saat). Bu doğrulama **istemcide yapılamaz** (token sızmasın diye) →
v2 bir küçük sunucu (worker) gerektirir. v1 bu yüzden salt okunur.

## 3.1 20 Temmuz 2026 domain kısıtı

Telegram, Mini App URL'lerinde **bot ayarlarında kayıtlı domain** şartı
getiriyor (BotFather → Configure Mini App). Bu yüzden:
- URL: `https://mehetgege3-cmyk.github.io/bobi-tv/mini_app/`
- BotFather'a **bu adres** yazılmalı; başka domain (kısa link vb.) çalışmaz.

## 4. Güvenlik kuralları (v1'de uygulanır)

1. **Secret YOK**: HTML/JS içinde token, chat_id, PAT, cookie bulunmaz.
2. **Dış kaynak YOK**: CDN, harici font, harici script yok (CSP `default-src 'none'`
   benzeri katı yaklaşım; tüm stil/JS satır içi).
3. **Hash → içerik** (XSS savunması): özet JSON'dan gelen her metin
   `textContent` ile yazılır, `innerHTML` KULLANILMAZ.
4. **Veri yoksa uydurma yok**: dosya boş/eksikse "bilinmiyor" yazar.
5. **Salt okunur**: hiçbir buton üretim/silme tetiklemez.

## 5. Dosyalar

| Dosya | İş |
|---|---|
| `webapp/index.html` | Mini App kabuğu (satır içi CSS/JS, tek dosya) |
| `webapp/veri/mini_app_ozet.json` | Panelin ürettiği özet veri (workflow commit eder) |
| `modules/mini_app_veri.py` | Özeti **tek doğruluk kaynağı**ndan üretir (uydurma sayı yok) |
| `.github/workflows/mini_app_veri.yml` | Özeti 15 dk'da bir tazeler + commit eder |
| `docs/MINI_APP.md` | Bu belge |

## 6. Veri şeması (`mini_app_ozet.json`)

```json
{
  "guncelleme": "2026-11-11T12:00:00+00:00",
  "bugun": {"uretilen": 16, "yayinda": 5},
  "kuyruk": {"toplam": 0, "sebep_dagilimi": {}},
  "trend7": [0, 1, 2, 3, 4, 5, 6],
  "denetim": [{"zaman": "...", "olay": "uretim_tetikle", "sonuc": "ok"}],
  "sinirlar": {"gunluk_yukleme_tavani": null}
}
```

`gunluk_yukleme_tavani: null` = **tavan yok** (2026-11-11 kullanıcı kararı).

## 7. Kabul kriterleri (v1)

- [x] Tek dosya HTML, harici kaynak yok, secret yok
- [x] Veri yoksa "bilinmiyor" (uydurma sayı yok)
- [x] `innerHTML` ile dış veri yazılmıyor
- [x] Özet üreticisi mevcut modüllerden okuyor (tek kaynak)
- [x] 15 dk'da bir tazelenen workflow + testler
- [x] GitHub Pages açıldı ve yayınlandı (2026-11-11, `mini_app_pages` ✓)
- [x] Canlı doğrulama: `https://mehetgege3-cmyk.github.io/bobi-tv/` → HTTP 200,
      `veri/mini_app_ozet.json` → gerçek sayılar (16 üretildi / 5 yayında)
- [ ] BotFather → Configure Mini App → URL yaz (senin yapman gereken tek adım)
- [ ] (Opsiyonel v2) yazma işlemleri: initData doğrulayan küçük sunucu
