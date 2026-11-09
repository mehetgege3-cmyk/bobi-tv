# 🎬 BOBİ TV — v6.3 Video Pipeline / v7.0 Senaryo Motoru

Türkçe absürt ve ironik komedi diyaloglarını **yüksek tutunmalı (high-retention)** YouTube Shorts videolarına dönüştüren uçtan uca otonom yapay zeka prodüksiyon hattı.

### Senaryo Motoru v7.0
- Senaryo çekirdeği `modules/senaryo_v7/` altında sablonlar, dogrulama, zenginlestirme, arsiv, kuyruk ve cikti sorumluluklarına ayrıldı.
- Dataclass modelleri, duygu/stil/kamera/rol Enum'ları, referanslı karakter kartları (sabit Ahmet/Emel sesi), satır başına TTS/altyazı/kamera alanları, v6/satirlar migration'ı (`semaversiyonu: "7.0"`), merkezi `Ayarlar`, logging ve alan bazlı istisnalar kullanılır. Diyalog modeli: `docs/BOBI_TV_V7_TEMPLATE_MODEL.md`.
- Geriye dönük uyumluluk: `from modules.scenario import senaryo_paketi_olustur` ve `senaryo_paketi_olustur(video_no)` aynen çalışır.
- Kalite kapısı: `pytest -q`, `mypy --strict`, `ruff check`, `ruff format --check`. Mimari kararlar ve kabul kriterleri: `docs/BOBI_TV_V7_MIGRATION_PLAN.md`.

### v6.3 PRO: Sürekli Değişen Konular + 15sn Minimum
- **Konu rotasyonu:** Bar fıkraları, paradoks hikâyeleri, absürt komedi/şakalar, çılgın ama zararsız hikâyeler, ters köşe fıkralar, eğlenceli replik düelloları ve saygılı kültürler arası mizah. Son 6 yayın kategorisi rotasyon seçiminde geriye atılır; yeni yüklemelerin kategorisi arşivlenir.
- **Kimlik güvenliği:** Irk/ten rengi/etnik köken hedefli aşağılayıcı fıkra veya stereotip üretilmez; çok kültürlü mizah, karakter ve durum komedisi şeklinde kapsayıcı yazılır.
- **Süre garantisi:** Kısa senaryolar render öncesi konuşma replikleriyle uzatılır; Render QC 15.0 saniyenin altındaki videoyu reddeder. YouTube'a yalnızca en az 15 saniyelik, QC'den geçen video gönderilir.

### v6.2 PRO: İlk Kare Kapak + 15 Dakika Üretim + Performans Kontrolü
- **Profesyonel kapak:** Özel 1080×1920 VS/Clash kapak görseli videonun Frame 0'ına gömülür; render sonrası ilk kare tekrar çıkarılır ve YouTube özel kapak olarak yüklenir.
- **15 dakikada bir:** `.github/workflows/hourly_production.yml` cron'u `*/15 * * * *`; bir çalıştırmada 1 video, günlük yapılandırılmış tavan 96 videodur.
- **İzlenme eşiği:** Her çalışmada, yayını en az 60 dakika önce yapılmış ve YouTube Data API'de 100'den az görüntülenen adaylar otomatik silinir; arşiv durumu ve Telegram bildirimi güncellenir.
- **OAuth önkoşulu:** Otomatik silme için `YOUTUBE_TOKEN` refresh token'ı kanal videosu silmeye izin veren `https://www.googleapis.com/auth/youtube.force-ssl` veya daha geniş bir YouTube OAuth scope'u ile verilmiş olmalıdır. Silme API izin vermezse video korunur ve log'a hata yazılır.
- **Operasyonel uyarı:** 15 dakikada bir üretim günde 96'ya kadar video anlamına gelir; GitHub Actions zamanlama gecikebilir, YouTube yükleme/API limitleri uygulanabilir ve 100 izlenme kararı için YouTube `viewCount` gecikmeli olabilir. Silme işlemi kalıcıdır; eşik, 60 dakika geçtikten sonra ilk uygun denetimde uygulanır.


---

## 🚀 v6.3 PRO Mimari Özeti

```text
bobi-tv/
├── .github/workflows/
│   ├── hourly_production.yml   # Her 15 dk üretim, 60 dk/100 izlenme otomatik kontrol + Artifact
│   ├── arena_senaryo.yml       # Günlük Arena AI Master Loop senaryo üretimi
│   ├── daily_production.yml    # Manuel toplu üretim tetikleyicisi
│   ├── test_pipeline.yml       # Uçtan uca v6.0 Render & QC doğrulama testi
│   └── arena-agent.yml         # Arena.ai Playwright çerez & oturum testi
├── modules/
│   ├── arena_api.py            # Arena.ai Headless Playwright Yönetmen + Çerez Yenileyici
│   ├── arena_uretici.py        # Senkron üretim sarmalayıcısı
│   ├── scenario.py             # v6 uyumlu façade; tek argümanlı senaryo_paketi_olustur(video_no)
│   ├── senaryo_v7/             # Tipli v7 çekirdeği: sablonlar/dogrulama/zenginlestirme/arsiv/kuyruk/cikti/cli
│   ├── tts_engine.py           # Çift Sesli (Ahmet+Emel), Sıfır Ölü Boşluklu TTS + WordBoundary
│   ├── audio_fx.py             # Stüdyo SFX (whoosh, pop, vine_boom, riser, ding) + Sidechain BGM (-14 LUFS)
│   ├── animasyon.py            # 1080x1920 30FPS Vektör Karakter Kartları + Kutulu Karaoke Altyazı + Zoom/Shake
│   ├── video_render.py         # Çok kanallı ses miksajı + FFmpeg rawvideo borusu + ffprobe Kalite Kontrolü (QC)
│   ├── kapak_uret.py           # 1080x1920 profesyonel VS/Clash kapak + Frame 0 çıkarımı
│   ├── youtube_upload.py       # YouTube API: ilk yorum, özel kapak, <100/60dk otomatik silme + kota koruması
│   └── telegram_notify.py      # Telegram anlık yayın, kuyruk ve hata bildirimleri
├── bobi_tv/
│   ├── assets/
│   │   ├── fonts/              # Montserrat-ExtraBold.ttf & Montserrat-Bold.ttf (Türkçe İ/Ş/Ğ tam uyumlu)
│   │   └── sfx/                # Önbellekli stüdyo ses efektleri (.wav)
│   ├── queue/                  # YouTube kotasına (uploadLimitExceeded) takılan hazır işlerin bekleme kuyruğu
│   ├── archive/                # Yayınlanan videoların geçmişi ve tekrar önleme (MD5) kayıtları
│   ├── production/             # Senaryo şablonları (prompt_template.md) ve geçici çalışma alanı
│   └── output/                 # Üretilen nihai MP4 ve kapak görselleri
├── docs/
│   ├── BOBI_TV_V6_PRO_MIMARI_VE_KURALLAR.md  # Shorts algoritma rehberi ve mimari
│   ├── BOBI_TV_V6_3_KONU_15DK_KAPAK.md       # Konu rotasyonu, minimum 15sn, Frame 0 kapak ve 15dk işleyiş
│   ├── BOBI_TV_V7_MIGRATION_PLAN.md           # 8 TODO maddesinin gerekçe/uygulama/kabul kriterleri
│   └── BOBI_TV_V7_TEMPLATE_MODEL.md           # Diyalog, karakter, duygu enum ve satır metadata sözleşmesi
├── arena-ask.mjs               # Arena.ai çerez birleştirme (<4KB) ve Tiptap otomasyon CLI aracı
├── arena-senaryo.mjs           # Master Loop JSON senaryo üretici Node betiği
├── main_pipeline.py            # Ana orkestrasyon ve akıllı kuyruk yöneticisi
├── requirements.txt            # Python bağımlılıkları
└── SKILL.md                    # BOBİ Ajan Anayasası ve v6.0 PRO Kalıcı Kuralları
```

---

## 💎 Shorts Hazırlarken Uygulanan 8 Altın Kural (v6.0 Standartları)

1. **0.0 Saniye Kancası (Sıfır Ölü Boşluk):** Videonun başında sessiz bekleme yoktur (`hook_suresi = 0.0`). İlk karede sarı şok başlık bandı, `whoosh` ses efekti ve olayın sonucundan başlayan ilk replik aynı salisede girer.
2. **Çift Sesli Zıt Diyalog:** Tekdüze anlatım yerine Karakter 1 **`tr-TR-AhmetNeural` (Erkek)** ve Karakter 2 **`tr-TR-EmelNeural` (Kadın)** sesleriyle karşılıklı konuşur.
2a. **Süre ve çeşitlilik (v6.3):** Her yayın en az **15 saniye** olmalı; daha kısa senaryo otomatik genişletilir, QC'den geçmezse yayınlanmaz. Konular son 6 kategorinin dışına rotasyonla seçilir.
3. **Nefes Boşluğu Kırpma (`silenceremove`):** TTS motorunun cümle başı ve sonuna eklediği 250–400ms ölü sessizlikler FFmpeg ile kesilir; `WordBoundary` zaman damgaları 0ms kaymayla yeniden kalibre edilir.
4. **Aktif-Kelime Kutulu Karaoke Altyazı:** Mobil izleyicilerin %60–80'i sesi kapalı başladığı için, o an okunan kelimenin arkasına yuvarlatılmış parlak sarı/kırmızı kutu (*pill*) çizilir ve Türkçe büyük harf kurallarına (`i -> İ`, `ı -> I`) tam uyulur.
5. **Vektörel Karakter Portreleri & Yaylanan Balonlar:** Sunucularda kırık emoji kutusu (`□`) oluşmaması için her karaktere özel vektörel portre rozeti ve ses şiddetine (RMS) duyarlı canlı ekolayzır çubukları çizilir.
6. **Twist Darbesi (Zoom + Shake + 808 Vine Boom):** Sondan bir önceki ters köşe cümlesinde `riser` + `vine_boom` çalar, üst bant kırmızıya döner, kamera **%118 zoom** ve hafif sarsıntı (*shake*) yapar.
7. **Sidechain Fon Müziği & `-14 LUFS` Ses Dengelemesi:** 118 BPM telifsiz ritmik fon müziği konuşma sırasında otomatik **`-20 dB`** seviyesine kısılır ve çıkış sesi YouTube Shorts standardı olan **`-14 LUFS`** seviyesine normalize edilir.
8. **%100 Dilbilgisel Kusursuz Döngü (Seamless Loop):** Son cümle yarım kalarak 0.0 saniyedeki ilk cümleye bağlanır; izleyici videonun bittiğini fark etmeden ikinci tura başlar (**>%100 APV**).

---

## ⚙️ GitHub Secrets Yapılandırması

| Secret Adı | Zorunlu | Açıklama |
|------------|:-------:|----------|
| `YOUTUBE_TOKEN` | ✅ | YouTube Data API v3 OAuth JSON (`client_id`, `client_secret`, `refresh_token`) |
| `YOUTUBE_CLIENT_SECRET` | ✅ | Google Cloud OAuth istemci yapılandırması |
| `ARENA_COOKIES_JSON` | ✅ | Cookie-Editor ile alınan Arena.ai oturum çerezleri (otomatik yenilenir) |
| `GH_PAT` | ✅ | Yenilenen Arena çerezini Secret'a geri yazmak ve workflow tetiklemek için PAT |
| `TELEGRAM_BOT_TOKEN` | ➖ | Yayın, kuyruk ve hata bildirimleri için Telegram Bot Token |
| `TELEGRAM_CHAT_ID` | ➖ | Bildirimlerin gönderileceği Telegram Chat ID |
| `PEXELS_API_KEY` | ➖ | Opsiyonel dikey HD B-Roll stok arka plan videosu anahtarı |

---

## 🧪 Çalıştırma Komutları

```bash
# Sadece yerel Pro MP4 + Kapak üretimi ve ffprobe Kalite Kontrolü (YouTube'a yüklemeden test)
YUKLEME_ATLA=1 GUNLUK_HEDEF=1 python3 main_pipeline.py

# Tam otonom üretim + YouTube yükleme + Otomatik ilk yorum + Akıllı kota kuyruğu
GUNLUK_HEDEF=1 python3 main_pipeline.py

# v7 senaryo kalite kapıları
python -m pip install -r requirements-dev.txt
pytest -q
mypy --strict
ruff check
ruff format --check
```

## 📺 Kanal
- **YouTube:** [@BOBİTİVİ](https://www.youtube.com/@BOBİTİVİ)
