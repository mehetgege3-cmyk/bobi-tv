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

## 2. Kapak hattı — `modules/kapak_arena.py`

Kullanıcının sorusu: *"Arena AI her videoya özel kapak tasarlasın, kapak
videonun ilk karesine yerleşsin ve otomatik seçilsin — mantıklı mı?"*

Cevap: **mantıklı** ve altyapı zaten vardı; eksik olan üç şey bu turda kapandı.

| Adım | Durum |
|---|---|
| 1. kareden kapak çıkarma (ffmpeg, 1080×1920) | vardı (`ilk_kare_cikar`) |
| Arena'dan başlık/vurgu/renk önerisi | vardı (`arena_kapak_onerisi_al`) |
| 3 aday + okunabilirlik skoru + otomatik seçim | vardı |
| **Vurgu kelimesini renklendirme** | **YENİ** (`baslik_kaplama`) |
| **Seçilen kapağı videonun 1. karesine GÖMME** | **YENİ** (`ilk_kareye_yerlestir`) |
| **AI görsel zemini (D adayı)** | **YENİ** (`ai_gorsel_zemin`, opsiyonel anahtar) |
| **Anonim GitHub + Arena `gorsel_prompt`** | **YENİ** |

### Kritik düzeltme: kapak artık gerçekten "ilk kare"

Önceki sürümde `kapak_sec_ve_hazirla()` yalnız YouTube'a yüklenecek JPEG'i
seçiyordu; **videonun ilk karesi değişmiyordu**. Artık:

```
seçilen kapak  →  ffmpeg: 1 kareye indir  →  videonun başına ekle
                  (-c:a copy: ses yeniden encode EDİLMEZ)
               →  paket["final_video"] bu yeni dosya olur
```

Kanıt (yerel test videosu, 2 sn):
`ilk kareye yerlesti → süre 00:00:02.03 → ilk kare pikseli (200,28,59) = kapak
rengi → Audio: aac korunmuş`. Test:
`tests/test_todo38_kapak_ilk_kare.py::test_kapak_videonun_ilk_karesine_yerlesir`.

### Dürüst sınır: Arena sohbeti görsel ÜRETMEZ

Arena'nın sohbet arayüzü metin döner (şok başlık, vurgu, renk, **gorsel_prompt**).
Görselin kendisini üretmek için ayrı bir görsel modeli gerekir:

- `GEMINI_API_KEY` **veya** `OPENAI_API_KEY` tanımlıysa: Arena'nın verdiği
  `gorsel_prompt` ile AI arka plan üretilir → D adayı.
- Tanımlı değilse: D adayı **sessizce atlanır**, akış 1. kare + tipografi ile
  devam eder. "AI kapak yapıldı" denmez — yapılmaz.

---

## 3. Arena çerezleri GitHub'a ne zaman eklenmeli?

`ARENA_COOKIES_JSON` + `ARENA_SMOKE_TEST` ile doğrulama sırası:

1. **Şimdi eklenebilir** — çerez yalnız *senaryo + kapak önerisi* için kullanılır.
   Geçersizse üretim DURMAZ: yerel senaryo şablonu + yerel kapak üreticisi
   devreye girer (`ARENA_COOKIES_JSON yok → yerel kapak üreticisi`).
2. **Doğrulama koşulu:** ekledikten sonra `Actions → Arena Smoke Test` →
   `Run workflow`. Beklenen verdict: `oturum-gecerli`.
   `oturum-gecersiz` ise çerez sohbet sayfasında değil, yanlış domain'de alınmış
   demektir (detay: `docs/ARENA_COMPOSER_TESHIS.md`).
3. **Yenileme:** çerez ~2-4 haftada düşer. Düşünce Telegram'a "çerezi yenile"
   uyarısı gider (`modules/arena_cerez_uyari.py`, 30 dk'da bir, spam yok).
4. **Ölçüm:** ekledikten sonra 🩺 Kanal Sağlığı ekranında `🪝 Kanca` satırı ve
   kalite ortalaması dolar. Çerez yoksa bu satırlar "veri yok" der — bu bir hata
   değil, dürüst durumdur.

---

## 4. YAPILMADI / sınırlar (dürüstlük)

- **Canlı Arena çerez testi yapılmadı** — bu ortamda geçerli çerez yok.
  Kullanıcı ekleyip `Arena Smoke Test` koşmalı.
- **AI görsel zemin canlı denenmedi** — `GEMINI_API_KEY`/`OPENAI_API_KEY`
  tanımlı değil. Kod yolu test edildi (anahtar yok → `None`, akış durmaz).
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
