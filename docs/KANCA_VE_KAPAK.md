# Kanca (Hook) + Kapak — A1/A2 sertleştirmesi

Güncel: **2026-11-11**. Kullanıcı kararı: **"A ile yapalım"** (içerik/kanca),
çünkü ölçülen durum şu: son 7 günde 41 video, 22 silinen, **akışa giren %0**,
ortalama izlenme ~2.3. Yani sorun "yükleme sayısı" değil, **ilk 1.5 saniye**.

Bu dosya ne yapıldığını, neden yapıldığını ve neyin **yapılmadığını** yazar.

---

## 1. Kanca motoru — `modules/senaryo_v7/kanca_motoru.py`

Eski motor (`hook_engineer.py`) **puan hesaplıyordu ama hiçbir şeyi değiştirmiyordu**:

| Eski davranış | Sorun | Yeni davranış |
|---|---|---|
| `_sayi_formu_olustur` → `random.choice([3,5,7,10])` | **uydurma sayı** (metinde olmayan veri) | sayı yalnız metinde geçiyorsa kullanılır; yoksa form üretilmez |
| Yasaklı kelime → yalnız `oneriler` listesine yazılıyordu | clickbait metni **kalıyordu** | `yumusat()` metne uygulanır (`ŞOK!` → `Beklenmedik!`) |
| `onerilen_varyant` hesaplanıp **hiçbir yere yazılmıyordu** | motorun çıktısı süstü | `paket_kancasini_uygula()` senaryoya yazar |
| Kanca puana %25 ağırlık | kötü kanca ~25 puan kaybettiriyordu | kanca **zorunlu** adım (TTS'den önce) |
| İlk satır 12 kelime sınırı | sadece uyarı | kanca ≤ 12 kelime, puan eşiği `KANCA_ESIGI = 75` |

### Ne yazılıyor (senaryo alanları)

```
hook_ust_bant   → seçilen kanca metni (üst bantta görünür)
hook_metni      → aynı metin (ilk saniye)
tts_metinleri[0]→ kanca (konuşulan ilk cümle)
diyaloglar[0]   → kanca (ekranda/karakeoke ilk replik)
kanca_formu     → soru | sahne | iddia | itiraf | sayi   (ölçüm için)
kanca_ab        → A | B | C                              (ölçüm için)
kanca_puan      → 0-100
kanca_kaynak    → özgün cümle (tekrar uygulamada metin çoğalmaz)
```

### Form rotasyonu ve öğrenme

`ROTASYON = ("soru", "sahne", "iddia", "itiraf")`, video numarasına göre
deterministik. Her video bir sonraki formu dener; böylece **hangi formun daha
çok izlenme getirdiği** ölçülebilir hale gelir.

- Arşiv kaydına `kanca_formu / kanca_ab / kanca_puan / hook_ust_bant` yazılır
  (`modules/youtube_upload.py:arsive_ekle`).
- `modules/kanal_sagligi.py:kanca_formu_performansi()` form bazında ortalama
  izlenme verir; **en az 2 video** görmeden "kazanan form" demez (tek video
  yanıltıcı).
- Panel: 🩺 Kanal Sağlığı → `🪝 Kanca:` satırı ("soru önde · soru 12.0 (2) …").
  Veri yoksa "ölçüm sürüyor" yazar, sayı uydurmaz.

### Kalite kapısı ilişkisi

Mevcut `kalite_kapisindan_gecir()` **değiştirilmedi** (regresyon riski yok).
Kanca artık kalite kapısından geçmeden ÖNCE uygulanıyor; yani kapı sahte bir
"kötü kanca" yüzünden senaryoyu reddetmiyor. Kalite günlüğüne de
`kanca_sonuc.form / motor_puan / metin` ekleniyor.

---

## 2. Kapak hattı — `kapak_gorsel.py` + `kapak_hatti.py` (2026-11-12 DEVRİM)

> **Bu bölümün eski hâli (A/B/C/D adayları, okunabilirlik skoru, `sok_baslik`/
> `vurgu_kelime`/HEX renk JSON şeması, 1. kareden kapak türetme, `ai_gorsel_zemin`)
> kullanıcı talimatıyla SİLİNDİ.** "Mevcut tüm kuralları çöpe at."

Kullanıcının talimatı (aynen): *"Arena AI'ye videonun içeriği hakkındaki tam
metni ver, bu metni okusun ve buna uygun Short video için kapak fotoğrafı
oluştursun … Oluşturduğu resmi indir ve oluşturulan videonun ilk karesine
yerleştirilip seçilsin."*

### Tek yol (kodda tek giriş noktası: `kapak_hatti.kapak_uret_ve_yerlestir`)

```
1. kapak_gorsel.video_metni(paket)
      → videonun TAM metni (senaryo.tam_metin → diyaloglar → başlık)
2. kapak_gorsel.gorsel_promptu(paket)
      → "VİDEO METNİ (TAM)" bloğu + 7 tasarım kuralı
        (tek baskın özne, üst 2/3, kontrast, merak/duygu, renk,
         GÖRSELİN İÇİNE YAZI KOYMA, 9:16, tıklama/izleme teşviki)
3. kapak_gorsel.arena_kapak_gorseli_uret(paket)      [SYNC sarmalayıcı]
      → Arena'ya prompt gider, sayfada beliren görsel yakalanır + indirilir
        (img src / canvas dataURL / background-image; blob: ise img bitmap'i
         canvas üzerinden kurtarılır; min 400×400 doğrulaması)
4. kapak_gorsel.gorseli_karesine_oturt()  → 1080×1920 kırpma
5. kapak_arena.ilk_kareye_yerlestir()     → kapak = videonun 1. KARESİ
```

### Arena görsel üretemezse (dürüst yedek)

`kapak_arena.ilk_kare_cikar` + `baslik_kaplama_jpg` → video karesi + videonun
kendi başlığı. **Üretim durmaz**; konsola `kaynak=video_karesi` yazılır.
Hiçbiri olmazsa `kaynak=yok` ve video kapaksız yüklenir (sessiz yalan yok).

### Dürüst sınır (CANLI DOĞRULANMADI)

Arena'nın **sohbet/agent arayüzünün görsel ÜRETİP ÜRETMEDİĞİ** henüz canlı
doğrulanmadı. Eski kod notu "Arena sohbet arayüzü görsel ÜRETMEZ" diyordu.
Üretmezse hat sessizce yedeğe düşer ve log'da `kaynak=video_karesi` görünür.
Doğrulama: `hourly_production.yml` dispatch → log'da
`[Kapak] ✅ Arena kapak görseli indirildi` satırı aranır.

### Silinen/korunan dosyalar

| Dosya | Durum |
|---|---|
| `modules/kapak_gorsel.py` | YENİ — metin → prompt → Arena görsel → indir → kırp |
| `modules/kapak_hatti.py` | YENİ — tek giriş `kapak_uret_ve_yerlestir` |
| `modules/kapak_arena.py` | SADELEŞTİ — yalnız mekanik: `ilk_kare_cikar`, `baslik_kaplama`, `baslik_kaplama_jpg`, `ilk_kareye_yerlestir` |
| `modules/kapak_uret.py` | SİLİNDİ (yerel VS/Clash kapak üreticisi) |
| `arena_api.arena_kapak_onerisi_al(_async/_kisa)` | SİLİNDİ (JSON şema önerisi) |

Testler: `tests/test_todo43_kapak_gorsel.py` (7 test) — prompt tam metni taşır,
yazı yasağı var, eski karar hattı yok, Arena görseli → 1. kare, yedek yol
ImportError vermez, sync sarmalayıcı loop içinde de çalışır, 1080×1920 kırpma.

### CANLI DOĞRULAMA — 2026-11-12 17:05–18:14 UTC (6 koşu)

| Koşu | Sonuç |
|---|---|
| `43265657831` | ❌ **REGRESYON**: `'NoneType' object has no attribute 'read'` → 0 video. Kapak render'dan sonra üretildiği için `animasyon.py` çöküyordu. DÜZELTİLDİ. |
| `43266695264` | ✅ Video yayınlandı ama ❌ `[YouTube] ⚠️ Kapak dosyası yok: (boş)` — paket alanları doldurulmuyordu. DÜZELTİLDİ. |
| `43268041894` | ✅ **Tam çalıştı**: `Kapak: ..._kapak.jpg \| kaynak: video_karesi \| ilk kareye gömüldü: EVET` → [shorts/_u54iIC1I8M](https://www.youtube.com/shorts/_u54iIC1I8M) |
| `43270740614` | ❌ Teşhis workflow'u `ModuleNotFoundError: modules` (PYTHONPATH yok). DÜZELTİLDİ. |
| `43271340457` | ❌ **SESSİZ YALAN**: Arena'ya prompt HİÇ gitmiyordu. 480 sn ölçüm: `img=0 canvas=0 metin=1766` sabit; ekran görüntüsünde prompt editörde duruyor. Eski `_promptu_gonder` tıklama başarısızken `True` dönüyordu. DÜZELTİLDİ (doğrulama eklendi). |
| `43274897203` / `43275868230` | ❌ `[Arena] ❌ GÖNDERİLEMEDİ — editör hâlâ dolu` + DOM dökümü: `Log In / Sign up for free / login: True`, ardından sayfa **accounts.google.com**'a yönlendi. **KÖK NEDEN: ARENA_COOKIES_JSON SÜRESİ DOLMUŞ.** |

### Kesin kök neden (tahmin değil, ölçüm)

`ARENA_COOKIES_JSON` ölü. Kanıt (run `43275868230`, adım DOM dökümü):

```
DOM[1_sayfa_acildi]  : {'login': True, 'buttons': [... 'Log In', 'Sign up for free' ...]}
DOM[2_gonderim_sonrasi]: {'url': 'https://accounts.google.com/v3/signin/identifier?...',
                          'tiptap': 0, 'textarea': 0, 'send_btn': 0}
```

Bu yüzden: Arena görsel üretim yolu **hiçbir zaman çalışmadı** — üretim, video
karesi yedeğine düşüyordu. "Arena kapak görseli üretti" iddiası yanlıştı ve
artık kod bunu saklamıyor.

### ÇÖZÜM: Arena tamamen terk edildi (2026-11-13)

Kullanıcı kararı: *"arena ai'yi ve gemini api'yi sok at çöpe at artık bunu
kullanalım gemini cookie işimize yarar."*

| Sağlayıcı | Durum | Neden |
|---|---|---|
| Arena AI | ⛔ **çöpe atıldı** | Çerez 401, tarayıcı duvarı, güvenilmez |
| Gemini API | ⛔ **çöpe atıldı** | Görsel kotası `limit: 0` |
| **Gemini web çerezi** | ✅ **TEK SAĞLAYICI** | Görsel + metin çalışıyor, kanıtlı |

Arena kodu `arsiv/arena_olu_kod/` altında duruyor (tarihsel). Üretim ona bakmaz.
Çalışan yol: `docs/GEMINI_WEB.md` ve SKILL.md §32.

## 3. Gemini web çerezi — kurulum ve doğrulama (2026-11-13 GÜNCEL)

> **DEĞİŞİKLİK:** Bu bölüm eskiden "Arena çerezleri"ni anlatıyordu. Arena AI
> 2026-11-13'te **tamamen çöpe atıldı** (kullanıcı kararı: *"arena ai'yi ve
> gemini api'yi sok at çöpe at"*). Tek sağlayıcı **Gemini web çerezi**.

### Çerez neden gerekli

Kapak görseli, senaryo ve yorum cevabı **hepsi** Gemini web'den gelir.
`GEMINI_COOKIES` yoksa bunların hiçbiri üretilemez — **uydurma içerik yazılmaz**.

### Kurulum

```bash
# 1) Çerezi doğrula (secret'a YAZMADAN)
python3 tools/gemini_cerez_kur.py --kuru

# 2) Doğruysa GitHub Secret'a yaz
python3 tools/gemini_cerez_kur.py --dosya <export.json>
```

### Doğrulama

```bash
PYTHONPATH=. python3 -c "from modules import gemini_web; print(gemini_web.durum())"
```

Beklenen: `hazir=True`. Değilse çerez düşmüş → Cookie-Editor ile yenile.

### Yenileme

Çerez ~2-4 haftada düşer. Düştüğünde üretim **durmaz** ama kapak üretilemez;
durum `gemini_web.durum()` ile görülür. Durum bilgisi Telegram paneline düşer.

---

## 4. YAPILMADI / sınırlar (dürüstlük)

- **Arena yolu kapandı** — 2026-11-13'te tamamen çöpe atıldı; test edilecek
  bir şey kalmadı. Gemini web çerezi bunun yerini aldı (kanıtlı).
- **Gemini API görsel üretimi ÇALIŞMIYOR** — ücretsiz katmanda görsel kotası
  `limit: 0`. Bu yüzden web çerezi kullanılıyor; API anahtarı kullanılmıyor.
- **8 saatlik kadansın izlenmeye etkisi henüz ÖLÇÜLMEDİ** — kadans 11 Kasım'da
  değişti; ölçüm için en az 3-5 gün ve `kanal_sagligi_gecmis.json` birikmesi
  gerekiyor. Bu dosya artık her gün tek satır biriktiriyor.
- **Kanca formu kazananı henüz belli değil** — form bazlı karşılaştırma için
  her formdan en az 2 video gerekiyor.

## 5. Testler

```
tests/test_todo38_kanca_motoru.py      16 test  (form, yumuşatma, uygulama, rotasyon, arşiv, geçmiş)
tests/test_todo38_kapak_ilk_kare.py     8 test  (ilk kareye gömme, vurgu rengi, AI zemin yokluğu)
```


---

## 6. CANLI TEST — 2026-11-11 10:01 UTC (run `42999272269`)

Gerçek kanal üzerinde tek seferlik uçtan uca deneme. **Sonuç: başarılı.**

| Adım | Sonuç |
|---|---|
| Konu/senaryo | "Buzdolabı Hırsızı Çıkan İsim Herkesi Şoke Etti" (makarna hırsızı) |
| Kanca | **100/100** · TTS ilk replik kancayla başladı: "MAKARNAMI YİYEN BENMİŞİM" |
| Döngü | **0/100 → 100/100** (bu turda `dongu_uygula()` eklendi) |
| Kalite kapısı | 68/100 (döngü düzeltmesi sonrası yeni koşularda yükselecek) |
| Render | 17.39 sn · 1080×1920 · H.264+AAC · 3470 KB |
| Arena kapak | **17 sn** yanıt (Arena'nın kendi süresi 8 sn) · öneri: "MAKARNAMI YİYEN BEN" |
| Kapak seçimi | A adayı (1. kare + Arena başlık), okunabilirlik 0.953 |
| İlk kareye gömme | ⚠️ **YANLIŞ ÇIKTI** — `_kapakli.mp4` üretiliyordu ama `paket["final_video"]` güncellenmediği için YouTube'a kapaksız video gidiyordu. Düzeltildi 2026-11-13: `docs/KAPAK_TESHIS.md` |
| YouTube | ✅ https://www.youtube.com/shorts/XSoVlWV304s |
| Toplam | 306 sn |

### Canlı testin ortaya çıkardığı 3 hata (hepsi düzeltildi)

1. **Test hiçbir şey yapmıyordu** (ilk deneme, run `42998937740`): `Üretim
   tavanına ulaşıldı (24/1)` → 80 sn'de "success". `CANLI_TEST=1` modu eklendi
   (tavan/sayım yok sayılır, silme kontrolü atlanır).
2. **Döngü 0/100**: son cümle "..." ile bitmiyor, ilk cümle bağlaçla
   başlamıyordu; öneri üretiliyor ama **uygulanmıyordu** → `dongu_uygula()`.
3. **Kapak yükleme sessizdi**: `_kapak_yukle` başarısız olsa da log "kapak
   yüklendi" diyordu → artık HTTP kodu + sebep yazılır, sonuç arşive işlenir.

### Kuyruk kilidi (bonus düzeltme)
Zincirleme adımı üretim job'unun içinde ~8 saat uyuyordu; `concurrency`
yüzünden yeni koşular saatlerce `pending` kalıyordu (kanıt: run `42975301955`
üretimini 07:00'de bitirdi, job 15:00'e kadar `in_progress`). Uyku ayrı
`bekle-ve-zincirle` job'una taşındı.
