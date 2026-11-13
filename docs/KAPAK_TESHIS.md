# KAPAK NEDEN GÖRÜNMÜYOR — Teşhis (2026-11-13)

**Kullanıcı şikâyeti:** *"Video üretiliyor, fotoğraf 1 kareye koyuluyor ama kaç
saniye görünüyor? Bir sorun var. Kanala girdiğimde ön izlemede kapak fotoğrafı
hiçbir videoda görünmüyor. Sorunu teşhis et."*

Yöntem: yt-dlp ile canlı video indirildi, `ffprobe`/`ffmpeg` ile kare kare
ölçüldü, YouTube'un 4 kapak dosyası indirilip piksel farkı hesaplandı,
artifact'taki `_kapakli.mp4` 1. karesi gözle doğrulandı.

---

## KÖK NEDEN 1 — YANLIŞ DOSYA YÜKLENİYOR (asıl sorun)

`modules/uretim_hatti.py`:

```python
kapak_sonuc = kapak_uret_ve_yerlestir(paket)
video_yolu = kapak_sonuc.get("video") or video_yolu   # ← yerel değişken güncellendi
# paket["final_video"] GÜNCELLENMİYORDU  ← HATA
```

`youtube_upload.video_yukle()` `senaryo_paketi["final_video"]`'yu okuyor.
O alan hâlâ **kapaksız orijinali** gösteriyordu.

**Kanıt (koşu 43381797959, aynı koşunun iki dosyası):**

| Dosya | 1. kare | YouTube'a gitti mi |
|---|---|---|
| `..._ilginc_bilgi.mp4` (35.909 KB) | boş şablon, `{` karakterleri | ✅ **EVET** |
| `..._ilginc_bilgi_kapakli.mp4` (31.065 KB) | kapak görseli | ❌ hayır |

YouTube'daki video `EQPd1GlVCMw` indirilip 1. karesi çıkarıldı → **boş şablon**.
Log ise `ilk kareye gömüldü: EVET` diyordu — gömüldü ama **yüklenmedi**.

**DÜZELTME:** `paket["final_video"] = video_yolu` eklendi.

## KÖK NEDEN 2 — KAPAK 33 MİLİSANİYE GÖRÜNÜYOR

`modules/kapak_arena.py`:
```
-t 0.04  +  trim=end_frame=1  +  fps=30
```
1 kare ÷ 30 fps = **0.0333 saniye**

**Ölçüm (kapaklı dosya, `showinfo`):**
```
ilk kare : n=0  pts_time=0.000
ikinci kare: n=1  pts_time=0.033
→ kapak SÜRESİ: 0.033 saniye (33 ms)
```
Göz 100 ms altını yakalayamaz → teknik olarak gömülü, pratikte **görünmez**.

**DÜZELTME (kullanıcı kararı):** `trim=end_frame=45` → **1.5 saniye**

## KÖK NEDEN 3 — YOUTUBE SHORTS İKİ GÖRSEL TUTUYOR (bizim hatamız değil)

Araştırma (Kasım 2026 kaynakları) + ölçüm:

| Dosya | Boyut | Ne işe yarar | API değiştirebilir mi |
|---|---|---|---|
| `maxresdefault.jpg` | 182.584 B | kanal listesi, arama | ✅ `thumbnails.set` |
| `hqdefault.jpg` | 27.559 B | küçük önizleme | ✅ |
| **`oar2.jpg`** | 150.608 B | **Shorts rafı** | ❌ **HAYIR** |

> *"YouTube Shorts için iki görsel tutar: `hqdefault`/`maxresdefault`
> (yüklediğin) ve `oar2.jpg` (Shorts rafında görünen). `thumbnails.set`
> `oar2`'ye dokunamaz; API'de bunu ayarlamanın yolu YOK."*

**Yani:** kanalın **Shorts sekmesinde** YouTube'un kendi seçtiği kare görünür.
Bunun tek istisnası: YouTube Studio'da (bilgisayar) elle kapak yüklemek —
Partner Program + doğrulanmış hesap gerekiyor, API kapalı.

## KÖK NEDEN 4 (ayrı hata) — ANİMASYON METNİ BASMIYOR

1. karede başlık yerine **`{` karakterleri** görünüyor. Animasyon şablonunda
   değişken interpolasyonu bozuk — metin yerine `{` yazılıyor.
   Bu yüzden 1. kare zaten işe yaramaz durumda.

---

## DÜZELTMELER

| # | Dosya | Değişiklik |
|---|---|---|
| 1 | `modules/uretim_hatti.py` | `paket["final_video"] = video_yolu` |
| 2 | `modules/kapak_arena.py` | `trim=end_frame=45` (1.5 sn), `-t 1.5` |
| 3 | `tools/kapak_yenile.py` | Geçmiş 60 video için Gemini kapak + `thumbnails.set` |
| 4 | `.github/workflows/kapak_yenile.yml` | Günde 3 video, elle de çalıştırılabilir |

## MEVCUT VİDEOLARIN KAPAKLARINI GÜNCELLEME

### ⚠️ HATA DÜZELTMESİ — "60 video" YANLIŞTI

İlk sürümde `bobi_tv/archive/videos.json` sayıldı ve **60 video** denildi.
**Bu yanlıştı.** O dosya kanal değil, geçmiş kayıt defteridir:

| durum | adet | ne demek |
|---|---|---|
| `silindi_dusuk_izlenme` | 37 | otomatik silme kuralı sildi (6 saatte 100 izlenme altı) |
| `kaldirildi` | 9 | YouTube/manuel kaldırma |
| `yayinda` | 17 | kayıt "yayında" diyor |
| (yok) | 1 | — |

oEmbed ile doğrulama: "yayında" görünen 17 kayıttan **yalnız 10'u erişilebilir**,
7'si 404/özel.

**GERÇEK ENVANTER (YouTube Data API, `channels.list` + uploads playlist):**

```
KANAL: BOBİ TV  (UCJzCURUGVP3-baKe7N9FNjw)
  abone=2   video=13   izlenme=6136
```

### KURAL (bundan sonra)

> Kanal verisi **her zaman** YouTube Data API'den alınır.
> `archive/videos.json` yalnız yerel geçmiş içindir, kanal envanteri DEĞİLDİR.

Araç: `tools/kanal_envanteri.py` · Workflow: **📊 Kanal Envanteri**
`tools/kapak_yenile.py` artık `canli_videolar()` ile API'yi okuyor — arşiv
kullanımı tamamen kaldırıldı.

```bash
# 3 video (varsayılan günlük)
python3 tools/kapak_yenile.py --azami 3

# kuru çalışma (üret, yükleme yapma)
python3 tools/kapak_yenile.py --azami 5 --kuru

# tek video
python3 tools/kapak_yenile.py --video-id EQPd1GlVCMw
```

Workflow: **🖼️ Mevcut Kapakları Yenile (Gemini)** — `workflow_dispatch` +
günlük cron (09:15). 60 video ≈ 20 günde tamamlanır (YouTube kotası dostu).

**Her video için aynı istem (K8):**
`<video başlığı> İsimli short video için kapak fotoğrafı istiyorum; etkileşim ve
izlenme rekorları kırması için profesyonel şekilde tasarla. Kapak fotoğrafını
gören merak edip tıklasın.`

## BEKLENTİ YÖNETİMİ (dürüst)

| Yer | Kapak değişir mi |
|---|---|
| Kanal → Videolar listesi | ✅ Evet (`thumbnails.set`) |
| Arama sonuçları | ✅ Evet |
| Paylaşım önizlemesi | ✅ Evet |
| **Kanal → Shorts sekmesi** | ❌ Hayır — `oar2.jpg`, YouTube seçer |
| Shorts akışı (feed) | ❌ Hayır |

---

## UYGULAMA SONUCU (2026-11-13)

| Koşu | İş | Sonuç |
|---|---|---|
| 43386571176 | Yeni üretim (kapak gömme testi) | ✅ https://www.youtube.com/shorts/dT-fJ7roco8 — 1. kare KAPAK, süre **1.5 sn** |
| 43386568087 | Kapak yenile (3 video) | ✅ 3/3 |
| 43388062706 | Kapak yenile (10 video, API envanteri) | ✅ 10/10 |

**Toplam: kanaldaki 13 videonun tamamı** yeni Gemini kapağıyla güncellendi.

**Kapak süresi ölçümü** (indirilen videodan, `ffmpeg` kare boyutu değişimi):
```
kare  0: 35.292 B  ← kapak
kare 40: 18.899 B  ← hâlâ kapak
kare 45: 18.333 B  ← içerik başladı
→ 45 / 30 fps = 1.5 saniye ✅
```
