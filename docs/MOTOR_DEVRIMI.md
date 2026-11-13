# MOTOR DEVRİMİ — 2026-11-13

**Kullanıcı:** *"Kanka mevcut motoru çöpe at. Animasyon ve diğer her şeyi.
Yapacağın işlem çok basit: promptu Gemini'ye at video üretsin."*
Sonra: *"Mevcut motorları Gemini kendisi yazsın. Çok detay verme, sadece short
videosu ve konular. Diğer basit şeyler."*

---

## 1. Ne silindi

**20 dosya + 1 workflow + 13 test.**

| Silinen | Ne yapıyordu |
|---|---|
| `modules/uretim_hatti.py` | Üretim zinciri orkestratörü |
| `modules/tts_engine.py` | edge-tts çift ses + WordBoundary karaoke |
| `modules/video_render.py` | ffmpeg render + QC |
| `modules/animasyon.py` (791 satır) | Vektör karakter, karaoke altyazı, twist zoom/shake, SFX |
| `modules/audio_fx.py` | Sidechain BGM, -14 LUFS mastering |
| `modules/kapak_hatti.py` + `kapak_arena` + `kapak_gorsel` + `kapak_uret` | Kapak üretimi, 1. kareye gömme |
| `modules/ilginc_bilgi/` (7 dosya) | 8 kategori, 7 taktik, 12 kural denetimi, onarım turu |
| `modules/senaryo_v7/` | Senaryo modelleri, kanca motoru, loop validator |
| `modules/scenario.py` | v6 uyumluluk katmanı |
| `tools/kapak_yenile.py` + `kapak_yenile.yml` | Kapak yenileme cron'u |

Bağımlılıklar da temizlendi: `gTTS`, `pydub`, `numpy` (yalnız silinen modüller
kullanıyordu).

## 2. Ne kaldı — tek yol

```
main_pipeline.py
   → modules/yeni_motor/motor.py :: video_uret(video_no)
        → KONU_LISTESI[video_no % 4]        (Gemini'nin yazdığı konu havuzu)
        → gemini_web.gorsel_uret()           (çerez, gerçek görsel)
        → edge_tts  tr-TR-AhmetNeural        (seslendirme)
        → ffmpeg                             (1080x1920, H.264 + AAC)
        → paket döndür
   → toplu_yukle()                            (YouTube)
```

**4 modül, 1 fonksiyon, 174 satır.** Motoru Gemini yazdı.

## 3. Gemini nasıl yazdı

`tools/motor_yazdir.py` — brief **kasıtlı kısa** (kullanıcı talebi):

```
Konu al, video üret, YouTube'a yükle. Hepsi bu.
- dikey 1080x1920, sesli, 15-60 sn
- konular: ilginç bilgiler, Türkçe, sade
- yapı/sınıf/dosya sayısı SENİN kararın. Yaratıcı ol.
```

Tek zorunluluk: `video_uret(video_no) -> dict` arayüzü + ortam gerçekleri
(Gemini API anahtarı yok → `gemini_web.gorsel_uret`; `video_yukle` `dosya_adi`
ister).

### Onarım döngüsü — 3 tur

| Tur | Sonuç |
|---|---|
| 1. kod | `from google import genai` + Imagen → **çalışmaz** (API anahtarı yok) |
| Doğrulama | `ImportError: cannot import name 'genai'` |
| Gemini'ye hata gösterildi | `gorsel_uret`'e geçti, Imagen'i attı |
| 2. doğrulama | `dosya_adi` eksikti → düzeltildi |
| **3. doğrulama** | ✅ **14.28 sn, 1080x1920, AAC, 1.152 KB** |

Sözdizimi geçen kod çalışan kod değildir: `tools/motor_dogrula.py` motoru
gerçekten koşturur, ffprobe ile denetler, `video_yukle`'i stub'lar.

## 4. Canlı kanıt (koşu `43419373202`)

```
[INFO] 🎬 Video #9 — yeni motor (Gemini kendi yazdı) başlıyor...
[BOBİ TV] Video üretiliyor: 'Beyninin Asla Unutamadığı O Sır'
[GeminiWeb] ✅ görsel indi: 140631 bayt → /tmp/bobi_gorsel_9.jpg
[BOBİ TV] İşlem tamamlandı: /tmp/bobi_video_9.mp4
[INFO] ✅ Video hazır: ... (14.08sn)
[YouTube] 🚀 Yayınlandı: https://www.youtube.com/shorts/wyjAN09NyDc
[INFO] === Tamamlandı: 1 yayınlandı, 0 kuyrukta (35sn) ===
```

**35 saniye.** Eski zincir 104 saniyeydi.

## 5. Dürüst uyarılar (K5)

1. **Video artık hareketsiz.** Gemini video üretmiyor (ölçüm:
   `docs/MOTOR_GORUNTU_DENEY.md` — *"Aboneliğinizi yükseltirseniz..."*).
   Motor **tek bir Gemini görseli** + seslendirme yapıyor. Animasyon, karaoke
   altyazı, twist zoom/shake, SFX yok. Bu, sadeleştirmenin kaçınılmaz bedeli.
2. **Konu havuzu 4 madde.** Gemini kod içine 4 konu gömdü (`video_no % 4` →
   her 4 videoda tekrar). Tükenirse tekrar eder. Büyütmek istersen söyle.
3. **Keşif ölçümü henüz yok.** Yeni format kanalda ilk kez yayınlandı.
   `akisa_giren` / izlenme kararı için 15 video veya 5 gün gerekli.
4. **Çift yükleme riski düzeltildi.** Gemini motorun içine `video_yukle()`
   koymuştu; pipeline da `toplu_yukle()` çağırıyor → aynı video iki kez
   yüklenecekti. Yükleme motordan çıkarıldı.

## 6. Nasıl geri alınır

Yok. `git rm` ile silindi, `arsiv_workspace/`'e kopya alınmadı (kullanıcı
talebi: *"Tamamen sil"*). Eski hâle dönmek için `git log`'dan
`43419373202` öncesi commit'e bakılmalı.


---

## 7. KAPAK DÜZELTMESİ (2026-11-13, aynı gün)

### Kullanıcı bildirimi
> *"Kapak fotoğrafı yapmamış"*

### Kök neden
Motor devriminde kapak hattı (`kapak_hatti` + `kapak_arena` + `kapak_gorsel` +
`kapak_uret`) silindi — **yerine yenisi konmadı**. `youtube_upload.py` ise hâlâ
`kapak_dosyasi` alanını okuyup `thumbnails.set` çağırıyordu. Yeni motor bu alanı
döndürmediği için alan boştu → **video kapaksız yayınlandı**. Hata sessizdi:
yükleme başarılı göründü, kimse kapak sormadı.

### Düzeltme
`modules/yeni_motor/motor.py`:
1. `kapak_istemini_yaz()` — kullanıcının tek cümlesi, birebir (K8)
2. **Ayrı Gemini çağrısı** — video arka planından bağımsız kapak görseli
3. `kapak_olcekle()` — 1080×1920 cover crop, JPEG q92, <2 MB (YouTube sınırı)
4. Gemini başarısızsa **videonun 1. karesi** kapak olur (üretim durmaz)
5. `paket["kapak_dosyasi"]` dolduruluyor

`tools/motor_dogrula.py` artık kapağı da denetliyor: var mı, >10 KB, <2 MB, ölçü.
**Kapaksız motor doğrulamayı geçemez** — bu hata bir daha sessizce geçemez.

### Canlı kanıt (koşu `43420854617`)
```
[BOBİ TV]   Video üretiliyor: 'Su İçerken Hiç Düşündün mü?'
[GeminiWeb] ✅ görsel indi: 200429 bayt → /tmp/bobi_kapak_ham_10.jpg
[BOBİ TV]   ✅ Kapak hazır: /tmp/bobi_kapak_10.jpg
[YouTube]   🖼️ Kapak yüklendi: bobi_kapak_10.jpg     ← thumbnails.set BAŞARILI
[INFO]      === Tamamlandı: 1 yayınlandı, 0 kuyrukta (62sn) ===
```
https://youtube.com/shorts/rpeNeu67VTk

### Not: gömme yok, ayrı yükleme
Eski düzende kapak videonun 1. karesine 1.5 sn gömülüyordu. Yeni düzende
**gömülmüyor**: kapak ayrı JPG olarak `thumbnails.set` ile yükleniyor. Shorts
rafında ve öneri kartında görünen kapak budur. Log'daki yanıltıcı
`ilk kareye gömüldü: HAYIR` satırı da düzeltildi.
