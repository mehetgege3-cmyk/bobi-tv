# GEMİNİ'NİN YAZDIĞI MOTOR

**Arayüz:** TAMAM — video_uret mevcut

**Uçtan uca doğrulama:** ✅ GEÇTİ
`{'sure_sn': 14.28, 'cozunurluk': '1080x1920', 'ses': 'aac', 'boyut_kb': 1152}`

## Üretilen dosyalar
_YOK_

## Gemini'nin planı
```
- **Dosyalar (3 adet):**
  1. `modules/yeni_motor/motor.py`: Ana orkestratör (`video_uret` fonksiyonu).
  2. `modules/yeni_motor/generator.py`: İçerik üretimi (metin üretimi, Gemini görsel çağrısı, edge-tts seslendirme).
  3. `modules/yeni_motor/assembler.py`: ffmpeg ile dikey video (1080x1920), görsel, ses ve altyazı birleştirme.

- **Video Üretim Adımları:**
  1. Rastgele ilginç bir konu seçilir ve metin (başlık, açıklama, seslendirme metni) hazırlanır.
  2. `edge-tts` ile ses dosyası (`.mp3`) ve `gorsel_uret` ile arka plan görseli (`.png`) üretilir.
  3. ffmpeg kullanılarak görsel ve ses dikey (1080x1920) MP4 formatında birleştirilir.
  4. Paket sözlüğü oluşturulup `video_yukle(paket)` fonksiyonuna gönderilir.

- **Kullanılan Kütüphaneler:** `edge-tts`, `ffmpeg`, `PIL` (Pillow), `modules.gemini_web`, `modules.youtube_upload`.
```
