# BOBİ TV v6.3 PRO — Dönen Konular, 15sn Minimum, 15 Dakika ve Frame 0 Kapak

## Davranış

- GitHub Actions `hourly_production.yml` zamanlaması `*/15 * * * *` olarak ayarlanmıştır. Her tetikleme bir Shorts üretmeye çalışır; varsayılan günlük üretim tavanı 96'dır.
- Render'dan önce v6.2 PRO 1080×1920 kapak görseli hazırlanır. Animasyon üretiminde `kare_no == 0` için bu kapak Frame 0 olarak yazılır ve FFmpeg ilk kareyi keyframe'e zorlar.
- Render sonrasında `videodan_ilk_kareyi_kapak_sec()` ile videonun t=0 karesi `_thumb.jpg` dosyasına çıkarılır. Bu dosya YouTube `thumbnails.set` çağrısına gönderilir.
- Her workflow çalışmasında önceki yüklemeler kontrol edilir. Yaşı en az 60 dakika olan ve YouTube Data API `viewCount` değeri 100'ün altında kalan video, OAuth yetkisi varsa `videos.delete` ile silinir. Uygun olmayan/henüz 60 dakikası dolmamış içerik korunur.
- Silme işlemi `videos.json` ve `archive/published/*.json` kayıtlarında `silindi_dusuk_izlenme` olarak işaretlenir; Telegram yapılandırılmışsa bildirim gönderilir.
- Arşiv denetimi ve kanalın son yüklemeleri birleştirilir; her turda API'ye en fazla 50 ID gönderilir.

## Gerekli yapılandırma

GitHub Actions secrets:
- `YOUTUBE_TOKEN`: Geçerli refresh token JSON'u. Otomatik silme için OAuth izni `youtube.force-ssl` veya daha geniş kapsam içermelidir. Yükleme izni tek başına silmeye yetmeyebilir.
- `ARENA_COOKIES_JSON`: Arena üretim oturumu.
- `GH_PAT`: güncel Arena oturum çerezini yenileme için workflow'un kullandığı token.
- İsteğe bağlı Telegram bot/chat secrets: yayın, silme ve hata bildirimleri.

Workflow env vars:
- `GUNLUK_HEDEF=1`
- `GUNLUK_MAKS=96`
- `MOD=isindirma_15dk`
- `OTOMATIK_SIL_AKTIF=1`
- `MIN_IZLENME_ESIGI=100`
- `IZLENME_KONTROL_DK=60`

## Güvenlik ve işletim notları

- `videos.delete` kalıcıdır; silinen videonun URL'si ve yorum/izlenme geçmişi artık kullanılabilir olmaz. Bu otomasyon, kullanıcı tarafından açıkça talep edilen `<100 / 60 dk` eşiğiyle sınırlıdır.
- YouTube `viewCount` her zaman gerçek zamanlı değildir. Kontrol 60. dakikada yapılır ve sonraki 15 dakikalık denetimlerde de uygun videoyu değerlendirebilir; bu yüzden gecikmeli sayım riski vardır.
- Kanalda 15 dakikada bir yayın, teorik olarak 96 video/gün eder. GitHub zamanlayıcısı kesin zaman garantisi vermez; yoğunlukta gecikebilir. YouTube günlük upload limiti ve Google API kotası yayınları engelleyebilir. Çalışan concurrency grubu aynı workflow run'larının çakışmasını önler; bu tek başına YouTube limitini yükseltmez.
- Silme yetkisi/API çağrısı başarısız olursa video silinmez; hata loglanır. Konfigüre edilmemiş YouTube token'ı varsa silme fonksiyonu güvenli biçimde atlanır.

## Yerel doğrulama

```bash
python3 -m py_compile main_pipeline.py modules/youtube_upload.py modules/kapak_uret.py modules/animasyon.py modules/video_render.py
YUKLEME_ATLA=1 GUNLUK_HEDEF=1 python3 main_pipeline.py
```

Frame 0 testi: `ffprobe -select_streams v:0 -show_entries frame=pict_type,pts_time -of csv=p=0 <video.mp4>` çıktısında ilk satır `0.000000,I` olmalıdır. Yerel üretimde test için yüklemeyi atla env'si kullan; YouTube silme fonksiyonunu gerçek kanalda test etme.

## v6.3 konu rotasyonu ve 15 saniye alt sınırı

- Konu havuzu: `bar_fikralari`, `paradoks_hikayeleri`, `absurt_komedi`, `absurt_sakalar`, `cilgin_hikayeler`, `ters_kose_fikralar`, `eglenceli_replikler`, `kulturlar_arasi_mizah` ve mevcut gündelik yaşam şablonları.
- `siradaki_kategori()` arşivin son altı videosundaki kategorileri geriye atıp yeni bir kategori seçer. Kategori `videos.json` içine yazılır; geçmiş dosya adlarından eski kategori kayıtları da çıkarılır. Arena prompt'u seçilen kategoriye göre özel ortam/karakter ve yeni olay örgüsü ister.
- Irk/ten rengi/etnik kökeni hedef alan aşağılayıcı içerik ve stereotipler üretilmez. Kültürler arası mizah, kimliği değil nazik gündelik yanlış anlaşılmaları konu alır.
- Arena senaryosu tahmini 19 saniyenin altında kalırsa doğal ek replik çiftleri ters köşe öncesine yerleştirilir. `video_kalite_kontrol()` 15.0 saniyenin altındaki veya 59.5 saniyeyi aşan MP4'ü reddeder; reddedilen video yükleme aşamasına ulaşmaz.
- `hourly_production.yml` hâlâ `*/15 * * * *`, `GUNLUK_HEDEF=1`, `GUNLUK_MAKS=96` ile çalışır. Gerçek yayın zamanlaması GitHub runner'ına ve YouTube yükleme kotasına bağlıdır.
