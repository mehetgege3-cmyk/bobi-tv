# GEMİNİ'NİN YAZDIĞI MOTOR

**Arayüz:** TAMAM — video_uret mevcut

## Üretilen dosyalar
- `modules/yeni_motor/motor.py`

## Gemini'nin planı
```
- **Kaç dosya olacak, adları ne?** 3 dosya: `motor.py`, `generator.py`, `utils.py`
- **Her dosya ne yapacak:**
  - `motor.py`: `video_uret(video_no)` fonksiyonunu barındırır, tüm süreci yönetir ve YouTube modülüne paket iletir.
  - `generator.py`: Gemini ile metin/görsel üretimi, `edge-tts` ile seslendirme ve `ffmpeg` ile görseli ve sesi birleştirip dikey video haline getirme işlerini yapar.
  - `utils.py`: Konu seçimi, dosya yönetimi ve yardımcı fonksiyonları barındırır.
- **Video tam olarak nasıl oluşacak:**
  1. Rastgele ilginç bir konu seçilir ve metin oluşturulur.
  2. Metin `edge-tts` ile ses dosyasına (mp3) dönüştürülür ve süresi ölçülür.
  3. Gemini API kullanılarak konuya uygun dikey görsel (1080x1920) üretilir.
  4. `ffmpeg` ile görsel ve ses dosyası birleştirilerek 15-60 saniyelik dikey MP4 video elde edilir.
- **Hangi kütüphaneler:** `google-genai`, `edge-tts`, `ffmpeg-python` (veya alt süreçler), `asyncio`
```
