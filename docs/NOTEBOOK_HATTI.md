# NotebookLM Video Hattı — Uçtan Uca

**Tarih:** 2026-11-08 · **Durum:** Hat hazır, **kimlik adımı kullanıcı onayı bekliyor**

---

## Ne yapıldı

Kullanıcı isteği: *"Gemini kapağı + ilk 1.5 sn gömme işini bu hatta ekle.
ayrıca video sonundaki eklenen gemini notebook kısmını kırp herzaman...
tümünü bitirince yeni konu ile bir video üretip youtube ye yükle"*

| Adım | Araç | Durum |
|---|---|---|
| 1. Konu | Gemini web (`GEMINI_COOKIES`) | ✅ canlı test edildi |
| 2. Kapak | Gemini web, `kapak_istemini_yaz()` | ✅ canlı test edildi (23 sn) |
| 3. Video | NotebookLM (`notebooklm-py`) | ⛔ kimlik ölü |
| 4. Outro kırpma | ffmpeg, parlaklık ölçümü | ✅ canlı test edildi |
| 5. Kapak gömme | ffmpeg concat | ✅ canlı test edildi |
| 6. YouTube yükleme | `youtube_upload.video_yukle()` | hazır (mevcut kod) |

---

## Bitiş kırpma — sabit sayı DEĞİL, ölçüm

Kullanıcı: *"yaklaşık olarak son 4 saniye olabilir sen incelersin."*

**Ölçüm** (`/tmp/nb_kisa.mp4`, 74.09 sn, son 30 sn 5 fps tarandı):

| Saniye | Ortalama parlaklık | |
|---|---|---|
| 60.0 – 70.9 | 214 – 218 | içerik |
| **71.0 – 74.0** | **244 – 246** | **"Gemini Notebook" outro** |

Kesme noktası **71.09 sn** → outro **3.00 sn**. Tahmin (4 sn) yakındı;
sabit yazmak yerine `OUTRO_PARLAKLIK = 238` eşiğiyle ölçülüyor. Böylece
NotebookLM outro'yu farklı yere koysa da doğru kesiliyor.

> ⚠️ Not: kırpılmış videonun son karesinde sağ altta silik "Gemini Notebook"
> filigranı duruyor. Konuşma sesi kesilmiyor; yazı ekranı gidiyor.

## Kapak gömme

Ayrı 1.5 sn'lik kapak klibi üretilip `concat` demuxer ile videonun önüne
ekleniyor. `filter_complex` + `-loop 1` + `-shortest` yolu 2026-11-13'te
"no packets" hatası vermişti — tekrar denenmedi.

Ölçüm: 71.10 sn + 1.5 sn = **72.63 sn**, 720×1280 korunuyor.
Kapak ayrıca `kapak_dosyasi` alanıyla `thumbnails.set`'e gidiyor.

## Sıra önemli

**Önce kırp, sonra kapak.** Tersi olsaydı kırpma noktası 1.5 sn kayardı.

---

## ⛔ Kimlik sorunu — asıl engel

### Ne oldu (ölçülmüş)

| Saat | Secret güncelleme | Sonuç |
|---|---|---|
| 17:48 | `NOTEBOOK_GOOGLE` yazıldı | — |
| 18:13 | — | ✅ 22 defter, video üretildi (285 sn) |
| 18:32 | — | ❌ `AuthError: signed-out page` |
| 18:34 | — | ❌ tazeleme de başarısız |

Aynı secret. Secret bozulmadı — **çerez döndü**.

### Sebep (kütüphanenin kendi belgesi, `data/SKILL.md`)

> "For unattended or headless work, prefer durable profile-backed
> **master-token auth** over a copied cookie snapshot... A sibling master
> token can automatically re-mint expired file-backed cookies.
> **Inline `NOTEBOOKLM_AUTH_JSON` is only a short-lived fallback; it bypasses
> this recovery path.**"

Google `__Secure-1PSIDTS` çerezini ~saatte bir döndürüyor. Secret'taki statik
kopya CI'da kullanıldığı için oturum ~1 saat sonra ölüyor. Bu yüzden
NotebookLM videosu otomatik hatta **tek seferlik** kalır — sürdürülebilir değil.

### Çözüm (kod hazır)

`tools/notebook_cerez_tazele.py` iki modu destekliyor:

| Mod | Secret | Kalıcılık |
|---|---|---|
| **A. Master token** | `NOTEBOOKLM_MASTER_TOKEN_JSON` | ♾️ kalıcı, kendini yeniler |
| B. Çerez | `NOTEBOOK_GOOGLE` | ⏱️ ~1 saat |

Master token akışı:
```bash
notebooklm login --master-token --account <email>   # bir kez, tarayıcıyla
# çıkan ~/.notebooklm/profiles/default/master_token.json → GitHub secret
```
`master_token.json` **şifre değişse bile geçerli**; kütüphane ondan çerez üretir.

---

## Dosyalar

| Dosya | İş |
|---|---|
| `tools/konu_uret.py` | Gemini web + `docs/SABLON_ISTEM.md` şablonu birebir, 8 kategori tekrarsız rotasyon, 7 taktik |
| `tools/video_son_isle.py` | Outro tespit/kırpma + kapak gömme |
| `tools/notebook_hat.py` | Zincir: konu → kapak → video → işleme → paket |
| `tools/hat_yukle.py` | `toplu_yukle` yolundan YouTube'a yükleme |
| `tools/notebook_cerez_tazele.py` | Kimlik: master token veya çerez tazeleme |
| `.github/workflows/notebook_hat.yml` | Hepsini tek koşuda çalıştırır |

---

## Ölçülen süreler

| Aşama | Süre |
|---|---|
| Konu (Gemini web) | 7 sn |
| Kapak (Gemini web) | 24 sn |
| Video (NotebookLM) | 285–632 sn |
| Kırpma + kapak | ~25 sn |
| **Toplam** | **6–13 dk** |

## Açık kararlar

1. **Master token kurulsun mu?** Kurulmazsa NotebookLM videosu otomatik hatta
   giremez (her ~1 saatte bir el ile çerez yenilemek gerekir).
2. **Not defterleri birikiyor.** Her video 1 defter açıyor (~22 defter şu an).
   Otomatik: 8 saatte bir → günde 3 → ayda ~90 defter. Silme politikası?
3. **Kalite ölçümü.** Gemini cevabı Qwen testinde 116 kelime çıktı
   (hedef 200–300). Şablon birebir; kırpma yok. Kabul mü, yoksa ikinci
   istek mi atılsın?
