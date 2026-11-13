# Ölü Kod Temizliği — Arena Tamamen Kaldırıldı (2026-11-13)

**Talep:** *"Ölü kod temizliği yap. Ayrıca workflow kısmında bazı koşucular var
sürekli hata veriyor, onları da incele ne oluyor."*

---

## 1. Arşivlenen ölü kod → `arsiv/arena_olu_kod/`

| Dosya | Ne yapıyordu | Neden ölü |
|---|---|---|
| `modules/arena_api.py` | Arena sohbet gönderimi (Playwright) | Arena çöpe atıldı |
| `modules/arena_http.py` | Tarayıcısız Arena SSE okuma | Arena çöpe atıldı |
| `modules/arena_cerez.py` | Çerez kendini besleme | Arena çöpe atıldı |
| `modules/arena_cerez_uyari.py` | Çerez ömrü uyarısı | Arena çöpe atıldı |
| `modules/arena_giris.py` | Google ile e-posta/şifre girişi | Arena çöpe atıldı |

**Testler de arşivlendi:** `test_arena_http.py`, `test_arena_selector_parity.py`,
`test_todo36_arena_cerez_uyari.py`, `test_todo39_arena_canli_surec.py`,
`test_arena_smoke_guard.py`, `test_arena_self_repair.py`, `test_todo42_ilginç_bilgi.py`

**Yeniden adlandırıldı:** `modules/arena_uretici.py` → `modules/uretim_hatti.py`,
`arena_tam_uretim()` → `uretim_hatti_calistir()`. İçindeki hat ZATEN Gemini'ye
dönüktü, sadece ismi Arena kalmıştı.

**`kapak_gorsel.py`:** Arena görsel fonksiyonları (`arena_kapak_gorseli_uret`,
`_http_ile_gorsel_al`, `_sayfadaki_gorseli_indir`) silindi.

> ⚠️ **DİKKAT — yaptığım hata:** Temizlik sırasında `gorseli_karesine_oturt`
> fonksiyonunu da sildim. Bu fonksiyon **1900→1080×1920 kırpma** yapıyor ve
> kapak hattının ZORUNLU parçası. Test yakaladı, git'ten geri getirildi.
> **Ders:** "Arena" kelimesi geçen her şey ölü değil; `kapak_arena` gibi
> mekanik yardımcılar çalışan hattın parçası.

---

## 2. Sürekli hata veren koşucular — KÖK NEDEN

### 2.1 Arena'ya adanmış 10 workflow (SİLİNDİ)

| Workflow | Hata |
|---|---|
`arena-agent.yml` · `arena_giris_login.yml` · `arena_gorsel_http.yml` ·
`arena_gorsel_test.yml` · `arena_merhaba.yml` · `arena_self_repair.yml` ·
`arena_senaryo.yml` · `arena_smoke_test.yml` · `test_arena_ask.yml` ·
`kapak_uctan_uca.yml`

**Kök neden:** Hepsi Arena çerezine bağlıydı. Çerez ölü (401) → her koşuda kırmızı.
Kanıt (koşu 43380163905): `##[error]Arena'dan cevap alınamadı (yanit.txt boş)`

**Etki:** 40 koşunun ~25'i bu yüzden kırmızıydı. Kullanıcı "sürekli hata veren
koşucular" derken bunları görüyordu.

### 2.2 Telegram Bot Poller — GERÇEK TASARIM HATASI (düzeltildi)

```
##[error]The action 'Bot mesajlarını kontrol et ve işle (uzun ömürlü döngü)'
         has timed out after 330 minutes.
```

**Kök neden:** `TELEGRAM_DONGU_DK=330` **ve** adım `timeout-minutes: 330` —
**eşit değerler.** Döngü tam 330. dakikada temiz çıkmaya çalışırken GitHub adımı
kesiyor → yarışı kaybediyor → her koşu kırmızı.

**Düzeltme:** döngü **300 dk**, adım timeout **320 dk** (20 dk güvenli pay).
**Kural + test:** `test_adim_timeout_donguden_buyuk_olmail` — adım timeout'u
döngüden en az 10 dk büyük olmalı.

### 2.3 Eksik `GEMINI_COOKIES` — SESSİZ HATA (düzeltildi)

`daily_production.yml` ve `test_pipeline.yml`'da **`GEMINI_COOKIES` yoktu.**
Bu workflow'lar çalışır ama **kapak üretemez** (video karesine düşer), kimse fark
etmez. Beş workflow'a da eklendi:

`canli_test` · `daily_production` · `hourly_production` · `test_pipeline` · `yorum_cevap`

Aynı anda **`ARENA_COOKIES_JSON` her yerden kaldırıldı.**

---

## 3. Son durum

| | Önce | Sonra |
|---|---|---|
| Workflow | 24 | **14** |
| Arena'ya bağlı workflow | 10 | **0** |
| Arena modülü (`modules/`) | 6 | **0** (5 arşiv, 1 yeniden adlandırıldı) |
| `GEMINI_COOKIES` olan üretim workflow'u | 2 | **5** |
| Testler | 817 | **674** (143 Arena testi arşivlendi) |

**Kalan 14 workflow:**

| Workflow | İş |
|---|---|
| `hourly_production.yml` | **asıl üretim** (saatlik) |
| `daily_production.yml` | günlük üretim |
| `canli_test.yml` | elle 1 video test |
| `yorum_cevap.yml` | yorum cevaplama |
| `telegram_bot.yml` | bot poller |
| `kanal_sagligi.yml`, `kanal_temizle.yml`, `cleanup_low_views.yml` | kanal bakımı |
| `weekly_report.yml`, `cadans_olcum.yml`, `arsiv_esitleme.yml` | raporlama |
| `mini_app_pages.yml`, `mini_app_veri.yml` | mini app |
| `test_pipeline.yml` | test koşusu |
