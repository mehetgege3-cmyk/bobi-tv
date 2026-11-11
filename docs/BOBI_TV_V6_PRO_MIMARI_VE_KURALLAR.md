# 🎬 BOBİ TV v6.0 — Profesyonel Shorts Dönüşüm & Kod Geliştirme Rehberi

> **Amaç:** `mehetgege3-cmyk/bobi-tv` reposundaki tüm dosyaları tek tek inceleyerek mevcut videoların neden "basit/amatör" göründüğünü teşhis etmek, 2026 YouTube Shorts algoritmasının altın kurallarıyla (Retention, Stayed-to-Watch, >%100 Loop APV) birleştirmek ve her modül için doğrudan uygulanabilir teknik çözümler sunmak.

---

## 📊 Bölüm 1: 2026 YouTube Shorts Algoritmasının Altın Metrikleri (Hazine Sandığı)

Güncel YouTube Shorts algoritma verilerine göre bir Short videosunun keşfete düşmesini belirleyen **3 ana kapı** vardır:

| Metrik | Ne Ölçer? | Tehlike Bölgesi | Viral Hedef | Koddaki Karşılığı |
|---|---|---|---|---|
| **1. Stayed to Watch (İzlemeyi Seçti vs Kaydırdı)** | İlk **1.5 – 2 saniyede** izleyicinin kaydırmayı durdurup durdurmadığı | `< %60` (Dağıtım durur) | **`> %75 – %80`** | 0. saniyede sesli kanca + görsel hareket + büyük başlık + "whoosh/pop" SFX |
| **2. Average Percentage Viewed (APV - Ort. İzlenme %)** | Videonun ne kadarının izlendiği ve tekrar dönüp dönmediği | `< %70` | **15-20 sn videoda `> %100 – %130`** | Sıfır nefes boşluğu (`silenceremove`), her 2-3 sn'de kamera zoom/değişim, **kusursuz döngü (seamless loop)** |
| **3. Sessiz İzleme Tutunması & Yorum Etkileşimi** | Mobil akışta ilk anda sesi kapalı olan **%60–80** izleyicinin videoda kalması | Küçük/düz yazı | Kelime-kelime renklenen büyük altyazı + yorum tetikleyici soru | Aktif kelime vurgulu ASS (`\kf` / renk değişimi) + YouTube API ile **otomatik ilk yorum** (`commentThreads.insert`) |

---

## 🔍 Bölüm 2: GitHub Reposu Dosya-Dosya Teşhis ve Geliştirme Fikirleri

### 1. `main_pipeline.py` & `modules/arena_uretici.py` — Mimari Kopukluk
**Mevcut Sorun:**
- Repoda `tts_engine.py`, `video_render.py`, `kapak_uret.py` gibi modüller var ama `main_pipeline.py` bunların **hiçbirini kullanmıyor**! Doğrudan `arena_api.py` çağrılıyor ve düz lacivert kutu üstüne Google Translate sesi (`gTTS`) basan 4 sabit PNG karesi üretiliyor. Videoların PowerPoint slaytı gibi görünmesinin bir numaralı sebebi bu kopukluktur.
- Hata aldığında eski/yedek pipeline'a düşmüyor veya üretilen videoyu kuyruğa (`bobi_tv/queue/`) kaydetmiyor.

**Geliştirme Fikri:**
- **Hibrit Pipeline Mimarisi:** Arena AI **yalnızca yaratıcı yönetmen (senaryo, diyalog tonları, SFX zamanlamaları, B-Roll anahtar kelimeleri ve loop kurgusu)** olarak kullanılmalı; seslendirme ve görsel kurgu ise çok katmanlı yerel profesyonel motor (`tts_engine v4` + `video_render v4`) tarafından işlenmelidir.
- **Kuyruk (Queue) Sistemi:** YouTube kotası (`uploadLimitExceeded`) doluysa üretilen MP4 + JSON paketi silinmemeli, `bobi_tv/queue/` klasörüne (veya GitHub Release/Artifact'a) kaydedilip bir sonraki uygun saatte yeniden render harcamadan yüklenmelidir.

---

### 2. `modules/tts_engine.py` — Seslendirme, Diyalog Gerçekçiliği ve Boşluk Kesme
**Mevcut Sorunlar:**
1. **Herkes Aynı Erkek Sesiyle Konuşuyor:** `EDGE_SESLER` sözlüğündeki 21 ses tipinin **tamamı** `tr-TR-AhmetNeural`! Müdür de, Ayşe de, Doktor da, Kedi de aynı ses! İzleyici kimin konuştuğunu anlamıyor.
2. **Ölü Nefes/Sessizlik Boşlukları (Dead Air):** `edge-tts` ve `gTTS` her ses dosyasının başına `~200ms`, sonuna `~400ms` boşluk bırakır. 4 replikte toplam **2–2.5 saniye ölü sessizlik** oluşur; bu da Shorts'ta anında kaydırma sebebidir.
3. **Sözde SFX Üreticisi:** `ses_efekti_uret()` fonksiyonu yazılmış ama hiçbir yerde çağrılmıyor; üstelik ürettiği ses `sine=frequency=800` (düz bip sesi).

**Geliştirme Fikirleri:**
- **Çoklu Karakter Sesi (Kadın + Erkek + Karakter Profilleri):**
  - `edge-tts` içinde ücretsiz ve çok doğal olan **`tr-TR-EmelNeural`** (kadın) ve **`tr-TR-AhmetNeural`** (erkek) seslerini dönüşümlü kullan! İki karakterli her diyalogda Karakter A = `AhmetNeural`, Karakter B = `EmelNeural` (veya zıt pitch/rate profili) otomatik atansın.
  - İsteğe bağlı ücretsiz/ucuz seviye atlama: **Gemini 2.5 Flash TTS** (çoklu konuşmacı destekli doğal Türkçe tonlama) entegrasyonu.
- **Otomatik Boşluk Kesme (`silenceremove`) + J-Cut Overlap:**
  - Her replik üretildikten sonra FFmpeg ile baş/son sessizliği milisaniyesine kadar tıraşla:
    ```bash
    ffmpeg -i raw.wav -af "silenceremove=start_periods=1:start_duration=0.02:start_threshold=-42dB:stop_periods=-1:stop_duration=0.05:stop_threshold=-42dB" tight.wav
    ```
  - Replikleri birleştirirken araya boşluk koymak yerine **`acrossfade=d=0.06`** ile çok hızlı, tempolu diyalog akışı sağla.
- **Gerçek SFX Kütüphanesi (`bobi_tv/production/assets/sfx/`):**
  - Repoya 6 adet küçük (20-40 KB) telifsiz `.wav`/`.mp3` ses efekti koy: `whoosh.mp3` (sahne/kanca geçişi), `pop.mp3` (mesaj balonu çıkışı), `vine_boom.mp3` / `shock.mp3` (punchline/twist anı), `ding.mp3`, `record_scratch.mp3`, `riser.mp3` (son cümleden önce gerilim yükseltici).

---

### 3. `modules/video_render.py` — Görsel Dinamizm, Aktif Altyazı ve Ses Miksajı
**Mevcut Sorunlar:**
1. **İlk 1 Saniye Tamamen Sessiz (`zaman_oteleme = hook_suresi`):** İlk 1 saniyede ekranda sadece yazı var, ses sıfır! İzleyici videonun bozuk veya sıkıcı olduğunu düşünüp geçiyor.
2. **Eksik Font Hatası:** ASS dosyasında `Montserrat-Bold` tanımlı ama Ubuntu runner'da sadece `DejaVuSans` kurulu; bu yüzden altyazı cılız varsayılan fonta düşüyor.
3. **Ekran Dışına Taşan Hook Metni:** `drawtext` tek satır yazıyor; 4 kelimeden uzun kanca cümleleri sağdan ve soldan kesiliyor.
4. **`punchline_efekt="zoom_in"` Çalışmıyor:** Kodda `"zoom_in"` için hiçbir FFmpeg filtresi yazılmamış! Arka plan sadece düz koyu mor gradient.
5. **Arka Plan Müziği ve Loudness Normalizasyonu Yok.**

**Geliştirme Fikirleri:**
- **1. Kelime-Kelime Renk Değiştiren "Hormozi Stili" Dinamik Altyazı:**
  - 3 kelimelik grupta o an söylenen kelime **Parlak Sarı (`&H0000D6FF`) + %118 Büyümüş (`\fscx118\fscy118`)**, diğer iki kelime **Beyaz (`&H00FFFFFF`)** olacak şekilde `WordBoundary` zaman damgalarıyla her kelime için ayrı ASS `Dialogue` satırı üret!
  - Repo içine gerçek **`Montserrat-ExtraBold.ttf`** veya **`TheBoldFont.ttf`** font dosyasını koy ve FFmpeg `ass=altyazi.ass:fontsdir=bobi_tv/production/assets/fonts` parametresiyle yükle.
- **2. Üç Farklı Görsel Sahne Modu (Monotonluğu Bitirir):**
  - **Mod A — Dinamik Sohbet Kartı / WhatsApp-iMessage Akışı:** Konuşan karakterin avatar ikonu + isim rozeti + yuvarlak köşeli modern mesaj balonu `pop.mp3` sesiyle ekrana zıplayarak gelsin!
  - **Mod B — Ücretsiz Pexels / Pixabay Dikey B-Roll Arka Planı:** Ücretsiz `PEXELS_API_KEY` ile senaryonun kategorisine uygun (`office stress`, `coffee cup`, `doctor clinic`, `cat funny`) dikey HD stok videolar otomatik indirilsin, hafif karartma + bulanıklık (`boxblur=4:1,eq=brightness=-0.25:contrast=1.15`) üzerine parlak altyazılar ve büyük hareketli Twemoji PNG'leri eklensin!
  - **Mod C — 2D Konuşan Karakter İllüstrasyonları (PNG Tuber Tekniği):** `assets/characters/` klasörüne koyacağın 6-8 şeffaf PNG karakterin (Patron, Çalışan, Doktor, Kedi, Kahve) konuşurken ses şiddetine göre zıplayıp hafif büyüdüğü (`scale` + `rotate` sallanma animasyonu) ve konuşmayan karakterin soluklaştığı sahne düzeni!
- **3. Kamera Hareketi ve Punchline Zoom:**
  - Her replik değişiminde kadrajı `%100` ↔ `%112` arasında değiştirerek iki kameralı çekim (A-cam / B-cam jump cut) hissi ver!
  - Son punchline (twist) cümlesinde `vine_boom.mp3` / `record_scratch.mp3` ile birlikte **hızlı `%125` zoom-in + hafif ekran sarsıntısı (camera shake)** uygula.
- **4. Arka Plan Müziği + Otomatik Ses Kısma (Sidechain Ducking) + `-14 LUFS`:**
  - `assets/music/` içine 4-5 adet telifsiz ritmik komedi/lo-fi/gerilim fon müziği koy.
  - Konuşma varken müziği otomatik `-18dB`'e bastıran, boşlukta hafif yükselten ve final sesini YouTube Shorts standardı olan **`-14 LUFS`** seviyesine getiren FFmpeg ses zinciri:
    ```bash
    [1:a]volume=0.14[bgm];
    [0:a][bgm]amix=inputs=2:duration=first:dropout_transition=0,loudnorm=I=-14:TP=-1.5:LRA=11[aout]
    ```

---

### 4. `modules/scenario.py` & `arena-senaryo.mjs` — Senaryo, Kanca ve Kusursuz Loop
**Mevcut Sorunlar:**
1. **`loop_baslangic` Alanı Hiç Kullanılmıyor:** JSON'da var ama videoda hiçbir karşılığı yok.
2. **Kanca (Hook) Zayıf ve Merak Boşluğu (Curiosity Gap) Açmıyor:** `"BİR BAR"` veya `"DİYET GÜNÜ 1"` gibi düz etiketler kaydırmayı durdurmaz.
3. **Süre Çok Kısa (8-11 sn):** İzleyici konuya ısınmadan video bitiyor. **16–26 saniye** (6–8 hızlı replik + ara tırmanış + şok final) Shorts tutunma eğrisi için çok daha güçlüdür.

**Geliştirme Fikirleri:**
- **Gerçek Kusursuz Döngü (Seamless Grammatical Loop):**
  - Son cümle tam bitmemeli veya ilk cümlenin sebebini bağlamalı!
  - *Örnek:*
    - **0.0 sn (Kanca / İlk Cümle):** `"…işte sırf bu yüzden patronum kahve makinesini kovdu!"`
    - **Diyaloglar:** *(Olay gelişir, absürt tırmanış yaşanır...)*
    - **Son Saniye (Loop Bağlantısı):** `"Makine herkesin ortasında patrona dönüp 'Senin maaşın benim elektriğime yetmez' dedi ve…"` → *(Anında 0.0 saniyeye döner: "…işte sırf bu yüzden patronum kahve makinesini kovdu!")*
  - İzleyici videonun nerede bittiğini fark etmez, izlenme oranı **%120+ APV** olur!

---

### 5. `modules/kapak_uret.py` & `modules/youtube_upload.py` — Kapak, SEO ve Otomatik Sabit Yorum
**Mevcut Sorunlar:**
1. **`kapak_uret.py` Hiç Çağrılmıyor:** Ölü kod durumunda. Üstelik YouTube Shorts akışında harici kapak görünmez, videonun içinden bir kare gösterilir.
2. **`sabit_yorum` Açıklamaya Yazılıyor:** Shorts izleyicisi açıklamayı açmaz; yorumlar ikonuna tıklar!
3. **Hashtag ve Başlık Kalıbı Tekdüze:** Başlık sonuna çok fazla etiket sıkıştırmak yerine 1 ana merak cümlesi + `#shorts` yeterli.

**Geliştirme Fikirleri:**
- **0. Kare (First-Frame) Görsel Kanca:** `kapak_uret.py` mantığını videonun **ilk 0.2 saniyesindeki başlangıç karesine** entegre et; böylece hem Shorts akışında hem kanal profilinde yüksek kontrastlı başlık karesi görünür.
- **YouTube API ile Gerçek İlk Yorum (`commentThreads.insert`):**
  - Video yüklendikten hemen sonra `youtube_upload.py` içinden `POST https://www.googleapis.com/youtube/v3/commentThreads?part=snippet` çağrısı yaparak `sabit_yorum` sorusunu **videonun altına ilk yorum olarak otomatik yaz!** (Yorum sayısı 0 yerine 1 göründüğünde izleyicilerin yorum yazma oranı 3 kat artar!)

---

### 6. `.github/workflows/hourly_production.yml` — Yayın Sıklığı ve Kalite Kontrol (QC)
**Mevcut Sorun:**
- Saat başı günde **24 video** hedefi hem YouTube'un yeni kanal `uploadLimitExceeded` duvarına çarpıyor hem de algoritmada kanalı "seri spam botu" sinyaline düşürüyor.

**Geliştirme Fikirleri:**
- **Altın Yayın Saatleri (Günde 3 veya 4 Yüksek Kaliteli Short):**
  - Türkiye saatine göre izleyicinin telefonda olduğu pik saatler: **08:30 (İşe/okula gidiş), 12:30 (Öğle molası), 18:30 (Çıkış saati), 21:30 (Gece akışı)**.
  - Cron ifadesi (UTC): `'30 5,9,15,18 * * *'`
- **Otomatik Kalite Kapısı (Render QC):**
  - Yüklemeden önce `ffprobe` ile video süresi (`12s <= süre <= 45s`), ses seviyesi (sessiz video kontrolü) ve çözünürlük (`1080x1920`) otomatik doğrulanmalı.

---

## 🤖 Bölüm 3: BOBİ TV İçin Geliştirilmiş "Master AI Senaryo & Kurgu" Promptu

Senin paylaştığın prompt rehberini BOBİ TV'nin JSON otomasyon mimarisiyle birleştirdim. Hem `arena-senaryo.mjs` içinde hem de manuel senaryo üretirken doğrudan bu **Master Prompt** yapısını kullanabilirsin:

```text
Sen Türkiye'nin en yüksek izlenme oranına (APV > %110) sahip absürt komedi YouTube Shorts yönetmenisin.
Konu / Kategori: [KONU_VEYA_KATEGORİ — Örn: Pazartesi sabahı enerjik patron ile uykusuz çalışanın kahve makinesi başındaki absürt kavgası]

Bana toplam 18–25 saniye sürecek, izleyiciyi ilk 1.5 saniyede kilitleyen ve son cümlesi ilk cümlesine kusursuz bağlanan (seamless loop) bir Shorts senaryosu yaz.

KESİN KURALLAR:
1. KANCA (İlk 2 Saniye): "Merhaba" veya yavaş giriş YASAK! Doğrudan çatışmanın veya en absürt olayın ortasından başla.
2. TEMPO: Gereksiz tek bir kelime bile kullanma. Her replik maksimum 6-9 kelime, keskin ve ritmik olsun (toplam 6-7 replik).
3. İKİ FARKLI SES: Karakterlere "erkek_enerjik", "erkek_bikkin", "kadin_keskin", "kadin_saskin", "derin_dramatik" ses profillerinden zıt olanları ata.
4. GÖRSEL & EMOJİ & SFX: Her replikte ekranda patlayacak vurgu kelimesini (highlight_kelime), tepki emojisini ve çalacak ses efektini ("whoosh", "pop", "vine_boom", "record_scratch", "riser") belirt.
5. KUSURSUZ DÖNGÜ (LOOP): Son repliğin sonu yarım veya bağlaçlı bitsin ki video başa döndüğünde ilk replikle tek bir cümleymiş gibi birleşsin!

SADECE aşağıdaki JSON formatında yanıt ver:
{
  "kategori": "kurumsal_hayat",
  "baslik": "Patron kahve makinesini kovdu! ☕😱 #shorts",
  "aciklama": "Sizin ofiste ilk kim kovulurdu? #ofishalleri #komedi #beyazyaka #shorts",
  "broll_arama": "funny office coffee stress vertical",
  "bgm_modu": "quirky_comedy",
  "kanca": {
    "ekran_yazisi": "PATRON KAHVE MAKİNESİNİ KOVDU! ☕🚨",
    "emoji": "🚨",
    "sfx": "whoosh"
  },
  "diyaloglar": [
    {
      "karakter": "ÇALIŞAN",
      "cinsiyet_ses": "erkek_bikkin",
      "metin": "…işte tam bu yüzden patron sabah kahve makinesini işten çıkardı!",
      "vurgu_kelime": "işten çıkardı!",
      "renk": "#FFD60A",
      "emoji": "☕",
      "kamera": "zoom_108",
      "sfx": "pop"
    },
    {
      "karakter": "PATRON",
      "cinsiyet_ses": "kadin_keskin",
      "metin": "Bana herkesin içinde köpüksüz latte verdi!",
      "vurgu_kelime": "köpüksüz",
      "renk": "#FF4D6D",
      "emoji": "😡",
      "kamera": "zoom_100",
      "sfx": "pop"
    },
    {
      "karakter": "MAKİNE",
      "cinsiyet_ses": "derin_dramatik",
      "metin": "Sen de üç yıldır zam yapmıyorsun, saygılar.",
      "vurgu_kelime": "zam yapmıyorsun",
      "renk": "#00F5D4",
      "emoji": "🤖",
      "kamera": "zoom_118_shake",
      "sfx": "vine_boom"
    },
    {
      "karakter": "ÇALIŞAN",
      "cinsiyet_ses": "erkek_bikkin",
      "metin": "Sonra fişini kendisi çekip kapıya yürüdü ve…",
      "vurgu_kelime": "fişini çekip",
      "renk": "#FFD60A",
      "emoji": "🔌",
      "kamera": "zoom_104",
      "sfx": "riser"
    }
  ],
  "ilk_yorum_sorusu": "Sizin ofisteki kahve makinesi konuşabilse ilk kime laf sokardı? 👇😂"
}
```

---

## 🗺️ Bölüm 4: Öncelik Sırasına Göre Uygulama Yol Haritası (Hemen Yapılacaklar)

1. **Faz 1 — Ses & Tempo Devrimi (En Yüksek Etki / En Hızlı Kazanç):**
   - `tts_engine.py` içine **`tr-TR-EmelNeural` (kadın) + `tr-TR-AhmetNeural` (erkek)** otomatik rol paylaşımı ekle.
   - Her ses çıktısına FFmpeg `silenceremove` filtresi koyarak nefes ve baş/son sessizliklerini sıfırla.
   - İlk 1 saniyedeki sessiz hook boşluğunu kaldır; ilk replik ve `whoosh.mp3` 0.0 saniyede başlasın!
2. **Faz 2 — Görsel Sahne & Hormozi Altyazı (`video_render.py`):**
   - Reponun içine `Montserrat-ExtraBold.ttf`, 5 adet SFX (`whoosh`, `pop`, `vine_boom`, `riser`, `ding`) ve 2 adet telifsiz fon müziği ekle.
   - Altyazıyı okunan kelimenin anlık renk değiştirdiği (Beyaz → Sarı/Turkuaz pop) ASS sistemine geçir.
   - Konuşma balonlu kart + karakter avatarı + Pexels ücretsiz dikey stok video arka planını devreye al.
3. **Faz 3 — Loop Senaryo + Otomatik İlk Yorum + Akıllı Takvim:**
   - Arena AI promptunu yukarıdaki **Master Loop JSON** şemasına yükselt.
   - `youtube_upload.py` içine `commentThreads.insert` ile otomatik ilk yorum atma özelliğini ekle.
   - `hourly_production.yml` zamanlamasını günde 24 spam denemesi yerine **günde 4 pik saat** olarak ayarla.

---

## ⏱️ Bölüm 5: ÜRETİM KADANSI — 8 SAATTE BİR (2026-11-11 kuralı, GÜNCELLENDİ)

Bu bölüm **bağlayıcı kuraldır** (normatif). Çelişki hâlinde bu bölüm ve
`modules/kadans.py` esas alınır.

> **DEĞİŞİKLİK KAYDI (2026-11-11):** Önceki kural "her 15 dakikada bir" idi.
> Ölçüm kanalı yaktığını gösterdi: 1 saatte silinen 21 videonun ortalama
> izlenmesi **0.8**, hiçbiri Shorts akışına girmedi, günde ~22 yükleme +
> aynı gün silme YouTube'a "yükle-sil" spam sinyali verdi. Yeni rejim:
> **8 saatte bir = günde 3 video, sabit saatler (00/08/16 UTC).**

### K1 — Kadans tanımı

Üretim ve yükleme **8 saatte bir** denenir (günde 3).

| Sabit | Değer | Yeri | Doğrulama |
|---|---|---|---|
| `KADANS_DK` | `480` | `modules/kadans.py` | test |
| `KADANS_CRON` | `0 */8 * * *` | `modules/kadans.py` | test |
| Workflow cron | `0 */8 * * *` | `.github/workflows/hourly_production.yml` | test (ikisi eşit) |
| Katalog kaydı | `KADANS_DK` seçenekleri `480/240/65` | `modules/ayar_katalogu.py` | test |
| `IZLENME_KONTROL_DK` | `360` (6 saat) | `main_pipeline.py` | test |
| `MIN_IZLENME_ESIGI` | `100` | `main_pipeline.py` | test |

### K2 — Kadans ≠ yükleme sayısı

8 saat **zamanlamadır**, yükleme kotası değildir. **Günlük yükleme tavanı
YOKTUR** (eski `GUNLUK_MAKS=6` tavanı 2026-11-11'de kaldırıldı). 8 saatlik
kadans günde 3 **fırsat** yaratır ve üretilen her video yüklenir. Tek engel
YouTube'un kendi 403 `quotaExceeded` hatasıdır: o an video stoğa alınır, kota
açılınca (UTC 00:00) yüklenir — üretim durmaz.

### K3 — Düşük izlenme silme eşiği: 6 saat / 100 izlenme

- ❌ Eski: 1 saatte 100 izlenme almayan video silinir. **Çok erkendi** —
  Shorts dağıtımı ilk saatte genelde test aşamasındadır; 1 saatte 0-4
  izlenme "içerik kötü" değil "henüz dağıtılmadı" demekti.
- ✅ Yeni: **6 saat** sonunda 100 izlenme. Silme hâlâ geri alınamaz; geçmiş
  silmeler arşivde `silindi_dusuk_izlenme` olarak durur.

### K4 — Kota ve hedef no-op → YEŞİL

Kota dolu veya günlük hedef tamam ise koşu **başarısız sayılmaz** (`exit 0`).
`KOTA_DOLU_DAVRANIS` varsayılanı `sessiz_dur`'dur.

### K5 — GitHub cron'una güvenilmez

`0 */8 * * *` yazmak 8 saatte bir çalışacağı anlamına gelmez (ölçüm: `*/10`
fiilen günde 1-2 koşuya düştü). **Birincil tetikleyici, koşu bitince bir
sonrakini açan zincirleme adımıdır** (`hourly_production.yml`); GitHub cron
yalnızca **yedektir**. Kurulum: `docs/TETIKLEYICI_KURULUM.md`.

### K6 — Kalite kadansın önünde

Kadans değişikliği kalite eşiğini düşürmez. Kalite kontrolünü geçmeyen video
sırf süre doldu diye yayımlanmaz; eksik üretim açıkça raporlanır.

### K7 — Geri dönüş ölçütü

1 hafta sonra: yükleme başına ortalama izlenme, 6 saatte 100 eşiğini geçen
video oranı ve ölçülen kadans (`modules/cadans_olcum.py`). İyileşme varsa
kullanıcı kararıyla 65 dakikaya (günde ~22) çıkılabilir.
---
