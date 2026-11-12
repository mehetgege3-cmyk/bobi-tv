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

### 8.3 Üretim koşusu süresi — GERÇEK ÖLÇÜM (2026-11-13)
`canli_test.yml` (1 video, üret + kapak + yükle), koşu `43325201001`:

| Süre | Durum |
|---|---|
| 0–2 dk | Kurulum adımları (checkout, python, ffmpeg, pip) |
| 2 dk → **25+ dk** | **Adım 7 "Pipeline'ı çalıştır"** tek adımda sürüyor |

Adım 7 içinde: senaryo (Arena) → ses/TTS → render → kapak (Arena + 1. kare)
→ YouTube yükleme. **Bu tek adım 25-40 dk sürebilir; takılma değildir.**

**Pratik sonuç:**
- `tools/kosu_bekle.sh` en az **200-240 tur** (33-40 dk) kullanın; 60/85 tur
  yetmez.
- Daha iyisi: adım listesini 5-10 dk'da bir sorgulayın (§8.2) — adım 7
  `completed` olunca bitmiştir.
- Log, iş bitene kadar **indirilemez** (§8.1). Bu yüzden uzun koşularda
  ilerlemeyi yalnız adım listesinden görürsünüz.
- Job `timeout-minutes: 90` — 90 dk sonra zorla kesilir.

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

## 9. ÜRETİM KOŞUSU SONRASI ÖĞRENİMLER (2026-11-13, koşu `43325201001`)

Koşu **success** (465 sn) ve video yayınlandı:
**https://www.youtube.com/shorts/MO1QOKxr4NQ** (`ekmek_kabugu`, 20261112_2303_0016)
**AMA kapak `kaynak=video_karesi`** — Arena görseli kullanılmadı. Nedeni:

### 9.1 Tek koşuda İKİ farklı Arena işi çakışıyor
`canli_test` akışı sırasıyla:
1. **Senaryo** için Arena'ya sorar (`{"soru":...,"cevap":...,"sonuc":...}` JSON'u ister)
2. **Kapak** için tekrar Arena'ya sorar (görsel ister)

Aynı `chat_id` (koşuda `01a1d1ff-...`) **her ikisinde de** yakalandı: kapak
aşaması, senaryo sohbetinin akışını okudu. Onda `hash` yok (JSON cevabı), bu
yüzden "tur 1: hash yok" ve ardından çerez öldü.

**Kural:** Kapak aşaması, senaryo aşamasının `chat_id`'sini kullanmamalı.
`son_chat_id()` **her yeni gönderimden önce temizlenmeli**
(`_SON_SAYFA.pop("chat_id", None)`), yoksa önceki sohbetin kimliği okunur.

### 9.2 Çerez koşu ortasında öldü (HTTP 401)
Tur 1'den sonra `events` → **HTTP 401**. Ardından 8 tur boşa denendi
(`oturum_doldu_mu()` kontrolü `hash_bekle` içinde yok; `sohbet_id_bekle`'de var).
**İki düzeltme gerekli:**
1. `hash_bekle` içinde de `oturum_doldu_mu()` kontrolü → 401'de hemen çık.
2. Kapak aşamasına girmeden önce `GET /api/me/pulse` ile oturumu doğrula;
   ölüyse hiç denemeye girme (boşa tur harcama).

### 9.3 Arena senaryo cevabı DOM'dan kirli geldi
`[İlginçBilgi] Arena ham cevap 94 karakter | baş: 'Searched the web\nRunning
commands\n3\nUsed Bash\n80ms...'` → Arena'nın **araç çalıştırma izleri** cevaba
karıştı, cevap "kullanılabilir değil" sayıldı ve üretim **doğrulanmış bankaya**
düştü (`ekmek_kabugu`). Üretim durmadı (doğru davranış) ama Arena senaryosu
kullanılmadı.
**Öğrenim:** Arena cevabını temizlerken `Searched the web`, `Running commands`,
`Used Bash`, `Agent`, `Auto` gibi UI izleri ayıklanmalı.

### 9.4 Kapak yedeği sayesinde üretim durmadı (TASARIM DOĞRU)
Arena kapak gelmeyince `video_karesi` + başlık kaplaması kullanıldı ve video
yine yüklendi. Yedek zinciri çalışıyor — kaldırılmamalı.

### 9.5 Kapak istemi 3519 karakter (doğrulandı)
`[Arena] 📨 GİDEN MESAJ (3519 karakter)` — 2041 karakterlik video metni +
tasarım kuralları + `Soru sorma, yap.` cümlesi. İstem boyu sorun değil.

## 10. ÇEREZ ÖMRÜ — ÖLÇÜLMÜŞ (2026-11-13)

| Zaman | `GET /api/me/pulse` | Not |
|---|---|---|
| ~19:30 | `200 {"pulse":84}` | HAR çerezi ilk doğrulama |
| ~22:20 | `200 {"pulse":72}` | hâlâ canlı (secret'a yazıldı) |
| ~22:30 | `200` | görsel indirme başarılı (koşu `43320057811`) |
| ~23:03 | `200` | kapak koşusu başarılı (`43323638730`) |
| ~23:20 | **`401`** | üretim koşusu ortasında öldü (`43325201001`) |
| ~23:50 | **`401`** | hâlâ ölü |

**Sonuç: çerez ~4 saat dayandı, sonra öldü.** Ölüm ani ve **koşu ortasında**
gerçekleşebiliyor (401 her şeyi durduruyor).

### 10.1 Zorunlu önlemler (koda eklendi)
1. `arena_http.oturum_canli_mi(cerez)` → `/api/me/pulse`; pahalı işten **önce**
   çağrılır (`kapak_gorsel._http_ile_gorsel_al`).
2. `hash_bekle` içinde `oturum_doldu_mu()` → 401'de **hemen çık** (boşa tur yok).
3. Kapak aşaması gönderimden **önce** `_SON_SAYFA.pop("chat_id")` → önceki
   aşamanın sohbet kimliği okunmaz.
4. Çerez ölüyse kapak `video_karesi` yedeğine düşer → **üretim durmaz**
   (tasarım gereği doğru; kanıt: video yayınlandı).

### 10.2 Çerez ne zaman yenilenmeli
- `pulse` → **401** ise kesinlikle.
- Üretim koşusu `kaynak=video_karesi` ile bittiyse ve logda `HTTP 401` varsa.
- Önleyici: üretim koşuları arasında **4 saatten uzun** ara varsa.

**Yenileme yolları:**
1. `arena_giris_login.yml` (e-posta/şifre) — Google duvarına takılabiliyor.
2. Kullanıcı tarayıcısından Cookie-Editor → JSON → `ARENA_COOKIES_JSON`.
3. HAR dosyasındaki çerez (bir kerelik, ~4 saat).
4. **Kendi kendini besleme:** her başarılı Arena kullanımından sonra
   `_cerezi_tazele` secret'ı günceller (çalışıyor: "ARENA_COOKIES_JSON
   güncellendi (2358 karakter)") — ama **süresi dolmuş** çerezi canlandırmaz.
