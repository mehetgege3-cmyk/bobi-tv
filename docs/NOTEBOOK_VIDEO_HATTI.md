# NotebookLM Video Hattı — Çalışan Çözüm

**Tarih:** 2026-11-15 · **Durum:** ✅ CANLI DOĞRULANDI (yerel + GitHub Actions)

---

## Kısa özet

Elle `batchexecute` RPC çağırmak **bırakıldı**. Hazır kütüphane kullanılıyor:
**[notebooklm-py](https://github.com/teng-lin/notebooklm-py) v0.8.6**.

| Denen | Sonuç |
|---|---|
| RPC'leri elle çağır (`gArtLc`, `R7cb6c`…) | ❌ `wrb.fr` yükü `null` |
| Playwright ile tıklama | ❌ kırılgan, çerez `CookieMismatch` |
| **notebooklm-py** | ✅ **çalışıyor, 3 satır kod** |

---

## Ölçülen sonuçlar

| Ölçüm | Yerel (sandbox) | GitHub Actions |
|---|---|---|
| Defter oluşturma | ~2 sn | ~2 sn |
| Metin kaynağı ekleme | ~5 sn | ~5 sn |
| **Video üretimi** | **632 sn** | **285 sn** |
| Toplam | 10.5 dk | 4.8 dk |
| Video | 720×1280 dikey | aynı |

Üretim süresi değişken (285–632 sn) — sıraya bağlı. **15 dakika tavan** güvenli.

## Çıktı özellikleri

```
720×1280  (9:16 DİKEY — kanala birebir uyuyor, kırpma YOK)
H.264 High, 30 fps, ~1000 kb/s
AAC mono, 44.1 kHz, 95 kb/s
~74 saniye, ~8-10 MB
```

NotebookLM'in kendi sesi konuşuyor (BOBİ değil). Görsel: el çizimi / sulu boya
stili, Türkçe altyazı gömülü.

---

## Kod

### Not defteri aç + video üret + indir

```python
import asyncio, json, os
from notebooklm import NotebookLMClient
from notebooklm.types import VideoFormat

os.environ["NOTEBOOKLM_AUTH_JSON"] = json.dumps({"cookies": [...], "origins": []})

async def main():
    async with NotebookLMClient.from_storage() as c:
        nb  = await c.notebooks.create("Başlık")
        src = await c.sources.add_text(nb.id, "Başlık", metin, wait=True)
        st  = await c.artifacts.generate_video(
                  nb.id, language="tr", video_format=VideoFormat.SHORT)
        await c.artifacts.wait_for_completion(nb.id, st.task_id, timeout=1200)
        await c.artifacts.download_video(nb.id, "/tmp/video.mp4")

asyncio.run(main())
```

### Video formatları (`VideoFormat`)

| Sabit | Arayüzdeki karşılığı |
|---|---|
| `SHORT` | **Kısa** ← bizim kullandığımız |
| `EXPLAINER` | Açıklayıcı |
| `BRIEF` | Özet |
| `CINEMATIC` | Sinematik |

### Kimlik: CI'da dosyasız

`NOTEBOOKLM_AUTH_JSON` değişkeni doğrudan JSON alır — dosya gerekmez.

**Zorunlu çerez:** `SID` + `__Secure-1PSIDTS`. İkisi de `NOTEBOOK_GOOGLE`'da var.

---

## Yazılan dosyalar

| Dosya | İş |
|---|---|
| `tools/notebook_video.py` | Defter aç → metin ekle → video üret → indir |
| `tools/notebook_kimlik_kontrol.py` | Üretimden önce hızlı kimlik testi (boşa 10 dk harcamamak için) |
| `.github/workflows/notebook_video.yml` | `workflow_dispatch`, artifact olarak video |
| `docs/ornek/kediler.txt` | Örnek konu metni |

`requirements.txt` → `notebooklm-py` eklendi.

---

## Çözülen tuzaklar

**1. `__Secure-` çerezlerinde `httpOnly` şart.**
`httpOnly: False` ile yazılınca Google `CookieMismatch` verip anonim
`/trynow` sayfasına atıyor. Sessiz başarısızlık — sayfa 200 dönüyor ama
"Oturum aç" düğmesi var.

**2. Secret'ta 3 çerez eksikti.**
`SID`, `HSID`, `APISID` yoktu. HAR'daki tam setle (20 çerez) değiştirildi.
Oturum açma için `SID` kritik.

**3. `curl` ile 200 dönmesi "giriş var" demek değil.**
Anonim kullanıcıya da 200 dönüyor. Gerçek test: sayfada "Yeni not defteri"
düğmesi var mı? Playwright screenshot'ı bunu gösterdi.

**4. `docs/pw` screenshot'ları repoda çakışma yarattı.**
Silindi; Playwright yaklaşımı tamamen bırakıldı.

---

## Açık sorular

1. **Ses BOBİ değil.** NotebookLM'in kendi anlatıcısı. Kanal kimliği için
   sorun mu? Alternatif: metni al, edge-tts BOBİ ile yeniden seslendir.
2. **~74 saniye sabit mi?** `SHORT` formatı bu uzunluğu veriyor. Daha uzun
   istenirse `EXPLAINER` denenmeli.
3. **Kota.** Her video 1 artifact harcıyor. Ücretsiz katmanda günlük sınır
   bilinmiyor — ölçülmedi.
4. **Kapak.** NotebookLM videosu kendi kapağını getirmiyor. Gemini kapağı +
   ilk 1.5 sn gömme hâlâ ayrı iş.
