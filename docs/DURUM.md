# Durum — 2026-11-08 akşamı

## ✅ Çalışan kısımlar (canlı doğrulandı, run 43750550009)

| Adım | Sonuç | Süre |
|---|---|---|
| Kimlik (NotebookLM) | ✅ 39 çerez, tazelendi, secret geri yazıldı, **23 defter** | 3 sn |
| Defter temizliği | ✅ 0 silinecek (kendi defterlerim korunuyor) | 1 sn |
| Konu (Gemini web) | ✅ "Penguenlerin Ayakları Neden Donmaz?" — 120 kelime, National Geographic | 6.5 sn |
| Kapak (Gemini web) | ✅ 261 KB, 9:16 | 26 sn |
| Video (NotebookLM) | ✅ defter `84ac3346`, 720×1280 | 841 sn |
| Outro kırpma | ✅ 69.59 → 66.60 sn (**-3.00 sn**) | — |
| Kapak gömme | ✅ 68.13 sn, 720×1280, ilk 1.5 sn | 15 sn |
| **YouTube yükleme** | ❌ `invalid_grant — Token has been expired or revoked` | — |

Hat toplam **889 sn (14.8 dk)**.

## ❌ Tek engel: YouTube refresh token ölmüş

Sebep YouTube kodu değil. Google, OAuth uygulaması **"Testing"** modundayken
refresh token'ı **7 günde** geçersiz kılıyor. `YOUTUBE_TOKEN` 2026-11-08'de
üretilmiş, bugün 2026-11-08 (7 gün sonrası) → süresi dolmuş.

Video dosyası hazır ama **/tmp'de**, koşu bitince silindi. Yeniden yükleme için
hattın tekrar koşması gerekiyor (14 dk). Bu yüzden önce yetkiyi düzeltmek
mantıklı: bir sonraki koşu hem üretir hem yükler.

## Çözüm adımları (senin yapman gereken)

### 1) İzin adresini aç

https://accounts.google.com/o/oauth2/v2/auth?client_id=230224291059-7ph9kjb41fuo35d3i3u32j4j7vvlre7f.apps.googleusercontent.com&redirect_uri=urn%3Aietf%3Awg%3Aoauth%3A2.0%3Aoob&response_type=code&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fyoutube.upload+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fyoutube+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fyoutube.force-ssl&access_type=offline&prompt=consent

- **BOBİ TV kanalının bağlı olduğu Google hesabıyla** giriş yap
- İzin ekranında YouTube yönetimini onayla
- Ekranda çıkan **kodu** kopyala

### 2) Kodu workflow'a ver

Actions → **YouTube Yetki — yeni refresh token al** → Run workflow
→ `kod` alanına yapıştır → Run

Secret `YOUTUBE_TOKEN` kendiliğinden güncellenir, kanal adı doğrulanır.

### 3) Hattı çalıştır

Actions → **Notebook Hattı** → Run workflow

## Kalıcı çözüm (7 gün sorununu bitirmek için)

Google Cloud Console → APIs & Services → **OAuth consent screen** →
Publishing status: **Testing → In production** (Publish app).

Yayınlanmış uygulamada refresh token süresi dolmuyor. Doğrulama istemez
(youtube.upload hassas kapsam sayılmıyor), sadece "Publish" yeterli.

## Dosyalar

| Dosya | İş |
|---|---|
| `tools/notebook_cerez_tazele.py` | 3 kimlik modu: storage_state / master token / kısmi çerez |
| `tools/notebook_kayit.py` | Hattın açtığı defterleri kaydeder (silme güvenliği) |
| `tools/notebook_temizle.py` | Yalnız kayıtlı defterleri siler, 24 saat yaş koruması |
| `tools/konu_uret.py` | Gemini web + şablon, kelime kuralı esnek |
| `tools/video_son_isle.py` | Outro kırpma (ölçümlü) + kapak gömme |
| `tools/notebook_hat.py` | Zincir orkestrasyonu |
| `tools/hat_yukle.py` | YouTube'a yükleme |
| `tools/youtube_yetki.py` | OAuth refresh token üretimi |
| `.github/workflows/notebook_hat.yml` | Ana hat |
| `.github/workflows/youtube_yetki.yml` | Yetki yenileme |

## Secret durumu

| Secret | Durum |
|---|---|
| `NOTEBOOKLM_AUTH_JSON` | ✅ yeni, 39 çerez, koşuda tazelendi ve geri yazıldı |
| `GEMINI_COOKIES` | ✅ çalışıyor (konu + kapak üretti) |
| `YOUTUBE_TOKEN` | ❌ refresh token süresi dolmuş |
| `YOUTUBE_CLIENT_SECRET` | ✅ çalışıyor (izin adresi üretildi) |
| `NOTEBOOK_GOOGLE` | yedek olarak duruyor, artık gerekmiyor |
