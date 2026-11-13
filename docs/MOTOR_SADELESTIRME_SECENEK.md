# MOTORU SADELEŞTİRME — ölçüm sonucu ve seçenekler

**Talep (2026-11-13):** *"Mevcut motoru çöpe at. Animasyon ve diğer her şeyi.
Yapacağın işlem çok basit: promptu Gemini'ye at video üretsin."*

Bu doküman talebi **uygulamadan önce** ölçümü kaydeder. Sebep: Gemini'nin video
üretip üretemediği bir varsayım değil, ölçülebilir bir olgu.

---

## 1. Ölçüm (koşu `43407661437`)

Prob: `tools/gemini_video_dene.py` → aynı StreamGenerate RPC'sine video istemi.

| Deneme | İstem | Sonuç |
|---|---|---|
| Metin kanalı | 8 sn dikey video, teleskop, sinematik | **Video yok.** Gemini aynen: *"Aboneliğinizi yükseltirseniz bugün sizin için o videoyu oluşturabilirim."* |
| Görsel kanalı — video istemiyle | aynı video istemi | **HATA** — `yanıtta görsel URL yok` |
| Görsel kanalı — sade görsel istemi | gece gökyüzü + teleskop, 9:16 | **ÇALIŞTI** — `sade.png` indi |

## 2. Hüküm

| Yetenek | Durum |
|---|---|
| Metin (senaryo) | ✅ çalışıyor |
| **Görsel** | ✅ çalışıyor |
| **Video** | ❌ **çalışmıyor — ücretli abonelik istiyor** |

Gemini web çerezi (mevcut hesap) **video üretemiyor**. Ücretsiz katmanda video
yok; Google AI Pro/Ultra aboneliği (Veo) gerekiyor.

**Yani "promptu Gemini'ye at, video üretsin" bugünkü hesapla mümkün değil.**
Motoru şimdi çöpe atarsak **hiç video üretilmez** — kanal durur.

---

## 3. Seçenekler

### A) Gemini aboneliği alınır → gerçek video üretimi
Google AI Pro (~20 $/ay) veya Ultra. Veo ile prompt → video.
- Motor **gerçekten** 3 satıra iner: istem → Veo → YouTube.
- TTS, animasyon, render, kapak: hepsi gider.
- **Bedel:** aylık ücret. Veo kotası sınırlı (aylık video sayısı).
- **Risk:** Veo çıktısı 8 sn civarı; Shorts'ta metin/altyazı katmanı olmaz,
  ses olmaz (Veo ses verirse değişir).

### B) Bugünkü hesapla kal → Gemini GÖRSEL üretsin, ffmpeg slayt yapsın
Gemini görsel üretimi **çalışıyor**. Motor şöyle sadeleşir:
- 1 Gemini çağrısı → 4-6 kare görsel (senaryo metni + görseller)
- ffmpeg: kareler + seslendirme → video
- **Giden:** vektör animasyon, karaoke altyazı, kanca kartı, twist zoom/shake,
  SFX, kapak hattı, 12 kural denetimi, kategori/taktik rotasyonu.
- **Kalan:** Gemini + edge-tts + ffmpeg + YouTube. ~4 modül.
- **Bedel:** 0 TL. **Risk:** dikey slayt videolar mevcut animasyondan daha
  "ucuz" görünür; kanal performansı düşebilir.

### C) Hiçbir şey silinmez, motor kalır
Ölçüm sonucu: mevcut motor **çalışıyor** (son iki koşu: 31 sn → 20 sn hedefe
oturdu, skor 100). Sadeleştirme kazanç sağlamıyorsa dokunmamak da bir karardır.

---

## 4. Neden silmeden önce soruyorum

K5 (dürüstlük) ve "çalışan kodu kanıtsız bozma" kuralı: motoru çöpe atmak
**geri dönüşü olmayan** bir adım ve gerekçesi (Gemini video üretiyor) ölçümle
**çürüdü**. Karar kullanıcının; ben yalnız ölçümü ve bedelleri koyuyorum.

**Karar bekleniyor.**
