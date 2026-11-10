# Arena Composer Teşhisi — Doğrulanmış Bulgular

Tarih: 2026-11-10. Bu doküman el yordamıyla (sahte cookie ile) doğrulanmış
bulguları kaydeder. **Canlı uçtan uca kanıt yoktur** — cookie süresi dolduğu
için gerçek oturumla test edilemedi. Bulgular, `arena-dom.mjs` tek kaynağına
işlenmiştir.

## Kök nedenler (eski kod neden yanlış cevap döndürdü)

1. **Composer `<textarea>` DEĞİLDİR.** Arena.ai agent arayüzü ProseMirror
   (tiptap) kullanır; gerçek seçici `div.tiptap[contenteditable="true"]`.
   Eski kodun `textarea` fallback'i her zaman boşa gider. Tek doğru seçici
   `div.tiptap[contenteditable="true"]`'dir; diğerleri sadece yedek.

2. **Hydration zaman alır.** `domcontentloaded` eventi editörü garanti
   etmez; React/ProseMirror mount'u 30-45 sn sürebilir. `waitForSelector`
   (visible) şarttır; 15 sn yetersizdir. `waitForEditor` tiptap'a tam
   timeout ayırır, fallbackleri sırayla dener.

3. **Terms of Use duvarı gönderimi engeller.** Modal açılır, mesaj
   composer'da kalır, URL değişmez. Eski kod bu durumu (boş ama "duran"
   gövdeyi) "cevap" sanıyordu ve sahte yanıt döndürüyordu.
   **Kural:** `ACCEPT_TOS=1` verilmeden Agree'ye ASLA basılmaz; duvar
   algılanırsa ekran görüntüsü + net hata.

4. **Cloudflare bot doğrulaması.** Composer hiç render olmaz. Bu durum
   oturum hatasıyla (exit 2) karıştırılmamalı — ayrı exit kodu 7
   (`bot-korumasi`). Title "Just a moment" veya gövdede `cf-chl` /
   "Checking your browser" işaretine bakılır.

5. **`page.keyboard.press('Enter')` hata fırlatmaz.** Buton yoksa veya
   odak yanlış yere gitmişse Enter sessizce başarısız olur. Bu yüzden
   gönderim "tıkladım" ile değil, **composer boşaldı VEYA URL değişti**
   doğrulamasıyla kanıtlanır. `attemptSend` sırası: Enter → Enter (tekrar)
   → bilinen gönder butonları; her denemeden sonra 5 sn doğrulama penceresi.

## Teşhis çıkış kodları (`arena-selftest.mjs`)

| Kod | Verdict | Anlamı |
|-----|---------|--------|
| 0 | `basarili` | Uçtan uca çalıştı (gönderildi + cevap büyüdü) |
| 1 | `cookie-yapilandirma-hatasi` / `ag-hatasi` | Secret eksik ya da ağ hatası |
| 2 | `oturum-gecersiz` | Giriş ekranı — cookie süresi dolmuş, elle yenile |
| 3 | `selector-bulunamadi` | Composer yok, giriş ekranı da yok — arayüz değişmiş |
| 4 | `gonderim-basarisiz` | Composer hâlâ dolu (gönderim doğrulanamadı) |
| 5 | `cevap-algilamadi` | Gönderildi ama gövde büyümedi |
| 6 | `tos-onayi-bekliyor` | ToS duvarı, `ACCEPT_TOS=1` verilmedi |
| 7 | `bot-korumasi` | Cloudflare doğrulama ekranı |

## Tek kaynak

- JS: `skills/arena-playwright-agent/scripts/arena-dom.mjs`
  (`EDITOR_FALLBACKS`, `SEND_SELECTORS`, `CONSENT_BUTTON_LABELS`)
- Python: `modules/arena_api.py` (`ARENA_EDITOR_FALLBACKS`,
  `ARENA_SEND_SELECTORS`, `ARENA_CONSENT_BUTTON_LABELS`)
- Ayrışma olursa `tests/test_arena_selector_parity.py` kırılır.

## Not

Testler sahte cookie ile yazıldı; canlı cookie ile uçtan uca doğrulama
TODO olarak `docs/TODO_ajana.md`'de bekliyor.
