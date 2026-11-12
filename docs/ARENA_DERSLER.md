# Arena Entegrasyonu — Dersler ve Hata Kaydı

**Amaç:** Aynı hatayı ikinci kez keşfetmemek. Her satır **canlı koşu veya
ölçümle** kanıtlıdır. Kanıtsız hiçbir iddia burada yoktur.
**Son güncelleme:** 2026-11-13

---

## 1. ASLA tekrar denemeyecekler (ölü yollar)

| Denenmiş | Sonuç | Kanıt |
|---|---|---|
| Google OAuth'u otomatik geçmek | `accounts.google.com/v3/signin/rejected`, "This browser or app may not be secure". Gerçek Chrome 157 + kalıcı profil + stealth + xvfb **yetmedi** | koşu serisi 2026-11-12 |
| `accounts.google.com/v3/signin/identifier`'a doğrudan gitmek | **HTTP 400** | ölçüm |
| `create-chat`'i jetonsuz çağırmak | **HTTP 400** `ZodError recaptchaV3Token` | ölçüm |
| Guest oturumla gönderim | Terms Agree → login modalı; 150 sn boşa | `/tmp/guest_test*.py` |
| `arena.ai/login` | **404** — login yalnız `/agent/` modalı | fetch |
| Pollinations/flux ile kapak | 402 / soyut leke kalitesi | `kanit/AI_kapak_flux.jpg` |
| Cevabı ekran görüntüsü/DOM'dan beklemek | 8 dk'ya kadar sürüyor, yanlış "gönderildi" logu | koşu `43292738267` |
| reCAPTCHA duvarını aşmaya çalışmak | Tasarımı gereği imkânsız | koşu serisi |

## 2. Kodlama tuzakları (hepsi canlı kanıtlı)

### 2.1 "Doğrulama" eklemek gönderimi bozdu
Araya Enter yedeği, `keyboard.type`, "editör boşaldı mı" kontrolü ekledim.
Sonuç: **istem kutuda kaldı**, sohbet başlamadı; log ise "gönderildi
(doğrulandı)" dedi (yanlış pozitif).
**Kural:** Çalışan kodu "iyileştirme" adı altında değiştirme. Çalışan sürüm
(`editor.click()` → `insert_text` → `Send message` tıkla) korunur.
**Kanıt:** koşu `43292738267`.

### 2.2 `rfind()` cevabın kendi başını kesiyor
Soru `"Merhaba"`, cevap `"Merhaba! 👋 Size nasıl yardımcı olabilirim?"`.
`_cevabi_ayikla` `rfind(prompt)` kullandığı için cevabın **kendi** "Merhaba"sını
bulup kesti → dönen cevap `"! 👋 Size nasıl yardımcı olabilirim?"`.
**Çözüm:** Kısa sorularda (`<40 karakter`) `find()` kullan.
**Kanıt:** koşu `43298899604`.

### 2.3 Eski sohbet tuzağı
Çerezle açılınca Arena **son sohbeti** açıyor; istem oraya gidiyor.
Arena "Anlaşıldı! Bundan böyle daha ayrıntılı yanıt vereceğim" dedi.
**Çözüm:** `/agent/00000000-0000-0000-0000-000000000000` adresine geç +
`create-chat` yanıtını dinle.
**Kanıt:** koşu `43316348923` (yakalanan sohbet başlığı: "Kendi kendini tanıt").

### 2.4 chat_id'yi yanlış yerden okumak
| Denenen | Sonuç |
|---|---|
| Sayfa URL'si (`/agent/<uuid>`) | URL `/agent/` kalıyor → **başarısız** (koşu `43315259344`) |
| `/api/history/unified` listesi | Yeni sohbet gecikmeli → **başarısız** (koşu `43313640773`) |
| **`create-chat` yanıtı** | **ÇALIŞTI** (koşular `43320057811`, `43323638730`) |

### 2.5 Dinleyiciyi yanlış yere koymak
`create-chat` dinleyicisi `_arena_sorgusu_yap` içine gömülüydü. Kapak hattı
farklı akış kullandığı için **chat_id yakalanamadı**.
**Çözüm:** `arena_api.create_chat_dinleyici_ekle(page)` ortak fonksiyon, her
akışta çağrılır.
**Kanıt:** koşu `43321910940`.

### 2.6 `video_metni` 21 karakter gösterdi
Fonksiyon yalnız `senaryo.tam_metin` okuyordu; test paketi `paket["metin"]`
kullanıyordu → Arena'ya **21 karakter** gitti.
**Çözüm:** `senaryo.tam_metin` → `paket["metin"]` → `diyaloglar` → `baslik`.
**Kanıt:** koşu `43321910940`, koşu `43323078600` (düzeltme sonrası 637 karakter
metin, 2112 karakter istem).

### 2.7 ffmpeg PATH'te değil
`shutil.which("ffmpeg")` → `None`. Kapak "1. kareye yerleştirme atlandı" diyip
sessizce geçti.
**Çözüm:** `imageio_ffmpeg.get_ffmpeg_exe()` (paket binary getiriyor).

### 2.8 concat çözünürlük uyuşmazlığı
Kapak 1080×1920'e ölçekleniyordu, video 720×1280 ise:
```
Input link in0:v0 parameters (size 720x1280) do not match ... (1080x1920)
→ rc=234, çıktı 0 bayt
```
**Çözüm:** `_video_boyutu()` ile videonun gerçek boyutu okunur, kapak o boyuta
`scale+crop+setsar=1` edilir.

### 2.9 Tek seferlik akış okuma
Arena görsel üretimi ilk denemede başarısız olursa cevabında
"İlk deneme tüm modellerde başarısız oldu... yeniden deneyeceğim" diyor ve
**sonra** yeni deneme başlatıyor. Tek okuma bunu kaçırdı.
**Çözüm:** `hash_bekle()` — 10-15 sn aralıkla akışı yeniden okur.
**Kanıt:** koşu `43311322015`.

### 2.10 401 spam'i
Ölü çerezde `sohbet_id_bekle` 15 tur boşuna denedi, log doldu.
**Çözüm:** `oturum_doldu_mu()` ise hemen çık.
**Kanıt:** koşu `43318433306`.

## 3. Kullanıcı gözlemleri (altın değerinde)

| Gözlem | Kodda karşılığı |
|---|---|
| "Arena her görselde 'Which image do you prefer?' diye soruyor; istem sonuna **'Soru sorma, yap.'** eklersen doğrudan yapıyor" | `kapak_gorsel.gorsel_promptu` + `arena_http.prompt_hazirla` |
| "Timeoutlar zaman kaybettiriyor; durumu sorup bitince çık" | `tools/kosu_bekle.sh` (10 sn aralık, bitince anında döner) |
| "Önceden çalışan şey şimdi çalışmıyor" | Gönderim kodu geri alındı (bkz. 2.1) |
| "Her adımda ne yaptığını yaz" | Her komuttan önce ne/niçin/nasıl açıklaması |

## 4. Doğrulanmış ölçümler (referans)

| Ölçüm | Değer | Koşul |
|---|---|---|
| Uçtan uca kapak (metin→1. kare) | **144 sn** | koşu `43323638730` |
| Arena görsel üretimi (kapak) | 768×1376, ~200 KB | aynı |
| Kapaklı video | 617.294 bayt | aynı |
| Arena görseli (ilk kanıt) | 1408×768, 3.165.495 bayt | HAR hash |
| Testler | 801 passed, 1 skipped | `pytest -q` |
| Çerez pulse | 72–84 | `/api/me/pulse` |

## 5. Çalışma disiplini (kullanıcı kuralları)

1. **Her komuttan önce** ne / niçin / nasıl yazılır.
2. **Kanıt göster:** log satırı tek başına kanıt değil; gerçek dosya/ölçüm.
3. **Uydurma yok:** çalışmayan özellik "çalışıyor" denmez; commit mesajında
   `YAPILMADI: <sebep>` yazılır.
4. **Testler yeşil olmadan push yok.**
5. **Sabit `sleep` yok** — durum sorgulayan döngü kullan (`tools/kosu_bekle.sh`).
6. **Çalışan kodu bozma:** "iyileştirme" adı altında değiştirmeden önce canlı
   kanıt iste.
7. **Telegram:** tur başına tek mesaj + edit.

---

## 6. Üretim hattını tetikleme (2026-11-13'te öğrenildi)

**Doğru workflow:** `.github/workflows/canli_test.yml`
→ adı: `Canlı Test — 1 video üret + yükle (tek seferlik)`
→ Üretim hattının AYNISI (kanca motoru + ses + render + Arena kapak +
  1. kareye gömme + YouTube yükleme), yalnız **1 video**, `TUR_BASINA_URETIM=1`.
→ `concurrency` YOK: 8 saatlik üretim job'u açıkken bile anında başlar.

**Girdiler:**
| Girdi | Varsayılan | Anlamı |
|---|---|---|
| `yukle` | `1` | `0` = yalnız üret, YouTube'a yükleme |
| `konu_no` | `""` (boş) | boş = otomatik sıradaki konu |
| `force` | `true` | tek kullanımlık zorlama bayrağı |

**Tetikleme komutu (çalışan):**
```bash
WID=$(curl -s -H "Authorization: Bearer $TOK" \
  "https://api.github.com/repos/mehetgege3-cmyk/bobi-tv/actions/workflows" \
  | python3 -c "
import json,sys
for w in json.load(sys.stdin)['workflows']:
    if w['path'].endswith('canli_test.yml'): print(w['id'])")

curl -s -X POST -H "Authorization: Bearer $TOK" -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/mehetgege3-cmyk/bobi-tv/actions/workflows/$WID/dispatches" \
  -d '{"ref":"main","inputs":{"yukle":"1","konu_no":"","force":"true"}}'
```

**`canli_test.yml` kimliği:** `414509563` (2026-11-13 itibarıyla)

**Not:** Tüm workflow listesi ve manuel tetiklenebilenler:
`docs/WORKFLOW_DIZINI.md` (aşağıdaki bölüm).

## 7. Zaman aşımı politikası (üretimde)

- Arena yanıtı için **sabit süre sınırı YOK**.
- `ARENA_IDLE_DK=15` → 15 dk hiç değişiklik olmazsa "donmuş sayfa" freni.
- `ARENA_MAKS_DK=45` → mutlak güvenlik tavanı.
- Job `timeout-minutes: 90` → yalnız altyapı koruması.
- **Dışarıdan izlerken** sabit `sleep` yok: `tools/kosu_bekle.sh`.

## 8. Koşu log'u ve izleme — öğrenilen incelikler (2026-11-13)

### 8.1 İş SÜRERKEN log indirilemez
`GET /actions/jobs/{job_id}/logs` çağrısı, iş bitmeden şunu döndürür:
```xml
<Error><Code>BlobNotFound</Code>...The specified blob does not exist.</Error>
```
**Yanlış teşhis:** "Log yok, workflow bozuk" demek YANLIŞ.
**Doğru:** İş bitene kadar `runs/{id}` durumunu sor; log'u **completed**
olduktan sonra indir.

### 8.2 Adım düzeyinde ilerleme (iş sürerken de çalışır)
Log yerine **adım listesi** kullanılabilir:
```bash
curl -s -H "Authorization: Bearer $TOK" \
  ".../actions/runs/$RID/jobs" | python3 -c "
import json,sys
j=json.load(sys.stdin)['jobs'][0]
print('DURUM:', j['status'], j['conclusion'])
for s in j['steps']:
    print(f\"  {s['number']:2}. {s['name'][:52]:54} {s['status']:10} {s['conclusion'] or ''}\")"
```
Çıktı hangi adımda olduğunu **anlık** gösterir (ör. "7. Pipeline'ı çalıştır
(1 video, canlı test)  in_progress").

### 8.3 Üretim koşusu süresi
`canli_test.yml` (1 video, üret + kapak + yükle):
- 9 dakikada **hâlâ** `in_progress` (adım 7: pipeline) — normal.
- `tools/kosu_bekle.sh` varsayılan 60 tur = 10 dk yetmez; **90-120 tur**
  kullanın (15-20 dk) ya da `--log` olmadan izleyin.
- Job `timeout-minutes: 90`.

### 8.4 Koşu kimliklerini nereden alırsınız
```bash
# workflow id
curl -s .../actions/workflows | python3 -c "
import json,sys
for w in json.load(sys.stdin)['workflows']:
    if w['path'].endswith('canli_test.yml'): print(w['id'])"   # 414509563
# run id (en son koşu)
curl -s .../actions/workflows/$WID/runs?per_page=1 | ...
```
