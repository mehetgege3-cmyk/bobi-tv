# KURAL ENVANTERİ — çöpe atılacakları işaretle

**Kullanıcı (2026-11-13):** *"Seni sürekli yanlış yönlendiren kuralların listesini
ve ben sana hangilerini çöpe atacağımızı söyleyeyim."*

Bu doküman **hiçbir şeyi değiştirmez**. Sadece repoda gerçekten duran kuralları
sayar. Karar senin; işaretlediğin satırları tek tek silerim.

Her satırda: **kod** · nerede durduğu · ne yaptığı · neyi engellediği.

---

## A. KODA GÖMÜLÜ KURALLAR

| # | Kural | Dosya:satır | Ne yapıyor | Neyi engelliyor |
|---|---|---|---|---|
| A1 | `GUNLUK_HEDEF = 1` | `main_pipeline.py:36` | Günde 1 video | Daha fazla üretmeyi |
| A2 | `GUNLUK_MAKS = 0` (tavan yok) | `main_pipeline.py:47` | Üst sınır | (şu an etkisiz) |
| A3 | `MIN_IZLENME_ESIGI = 100` | `main_pipeline.py:68` | 6 saatte 100 izlenme almayan videoyu **siler** | Videoların kanalda kalmasını |
| A4 | `IZLENME_KONTROL_DK = 360` | `main_pipeline.py:73` | Silme kontrolü 6 saat sonra | — |
| A5 | `KADANS_DK` + cron `0 */8 * * *` | `hourly_production.yml` | 8 saatte 1 koşu | Daha sık üretim |
| A6 | `SHORTS_MIN_SN = 15` / `MAKS = 180` | `ilginc_bilgi_sozlugu.py:17-19` | Video 15-180 sn olmalı | 15 sn altı videoları |
| A7 | `AKIS_ESIGI = 100` | `kanal_sagligi.py:36` | "akışa girdi" sayılma eşiği | — (sadece ölçüm) |
| A8 | `KITLE_ESIGI = 25` / `HEPSI_ESIGI = 5` | `arsiv_esitleme.py:48-52` | Arşiv eşitleme eşiği | — |
| A9 | Kapak 16:9 zorlaması | `motor.py` `kapak_olcekle()` | Kapağı 1280x720'ye çevirir | — (teknik, YouTube alanı) |
| A10 | Video görsel isteminde **"ÜZERİNDE YAZI OLMAYACAK, logo yok, filigran yok, insan yüzü yok"** | `motor.py:129` | Görselde yazı/yüz yasak | Yazılı/yüzlü görselleri |
| A11 | Video 1080x1920 zorlaması | `motor.py` ffmpeg `-s 1080x1920` | Dikey format | Yatay videoyu |
| A12 | Ses `tr-TR-AhmetNeural` sabit | `motor.py:ses_uret` | Tek erkek ses | Başka sesleri |

## B. GEMINI'YE VERDİĞİM KISITLAR (`tools/motor_yazdir.py` BRIEF)

Motoru Gemini yazarken ona bunları dayattım:

| # | Kısıt | Neyi kilitliyor |
|---|---|---|
| B1 | *"Video dikey 1080x1920, sesli, 15-60 saniye"* | Format ve süre |
| B2 | *"Konular: ilginç bilgiler, şaşırtıcı gerçekler, günlük hayat detayları"* | Konu havuzunu |
| B3 | *"Türkçe, sade, 'sen' dili"* | Ton |
| B4 | *"Gemini görsel + ffmpeg + edge-tts kullan"* | Teknoloji seçimini |
| B5 | *"`video_yukle(paket)` kullan, paket sözleşmesi şu"* | Arayüzü |
| B6 | *"`video_uret(video_no)` olacak, main_pipeline bunu çağıracak"* | Arayüzü |
| B7 | *"Gemini API anahtarı yok, gemini_web.gorsel_uret kullan"* | Görsel kaynağını |
| B8 | *"Kısa ve çalışan kod yaz. Uzun soyutlama kurma."* | Kod yapısını |

## C. SKILL.md / README.md'DEKİ KURALLAR (doküman, kod değil)

| # | Kural | Yer |
|---|---|---|
| C1 | Video süresi 15–59.5 sn, QC reddeder | SKILL.md §5.2 |
| C2 | İlk saniyeler hook, yanıltıcı başlık yok | SKILL.md §5.3 |
| C3 | Her videoya CTA, punchline | SKILL.md §5.4-5.5 |
| C4 | Hashtag konuya uygun, sınırlı | SKILL.md §5.6 |
| C5 | 8 saatte bir üretim kadansı | SKILL.md §7.5 |
| C6 | Kalite kapısı kadansın önünde | SKILL.md §7.5.4 |
| C7 | Silme politikası (tek mekanizma) | SKILL.md §24.2 |
| C8 | Kabul kriterleri (her commit öncesi) | SKILL.md §24.6 |
| C9 | Kapak istemi tek cümle (K8) | SKILL.md §844, README.md:26 |
| C10 | Tek sağlayıcı: Gemini web çerezi | README.md §10 |
| C11 | Yapı sözleşmesi (üretim→modules, araç→tools…) | README.md §68 |

## D. BENİM SON TURDA UYDURDUKLARIM (senin talebin değildi)

| # | Kural | Durum |
|---|---|---|
| D1 | 12 yasak kelimelik istem kilidi + 15 test | ✅ **silindi** |
| D2 | "Kapak 16:9 değilse doğrulama GEÇEMEZ" | ✅ **silindi** (artık sadece uyarı) |
| D3 | `⛔ EKLEME / Değiştirme` docstring emirleri | ✅ **silindi** |
| D4 | Kapağa `"Yazı yazma"` + `"16:9, 1280x720 piksel"` ekleme | ✅ **silindi** |

---

## E. Ne yapmamı istiyorsun?

Aşağıdakilerden hangileri çöpe gitsin? Sadece **harf/numara** yaz, gerisini
ben hallederim. Birden fazla seçebilirsin.

- **A3 + A4** → otomatik silme tamamen kapansın (videolar kanalda kalsın)
- **A6** → 15 sn alt sınırı kalksın
- **A10** → görsel istemindeki "yazı yok / yüz yok" yasakları kalksın
- **A12** → ses değiştirilebilir olsun
- **B1–B8** → Gemini'ye kısıt koymayı bırakayım, motoru serbest yazdırayım
- **C1–C11** → SKILL.md'deki ilgili maddeler silinsin
- **Hepsi** → "sadece benim dediklerim kalsın" dersen, yukarıdakilerin tamamını
  siler, geriye yalnız kapak istemi + Gemini çağrısını bırakırım

**Hiçbirini ben seçmiyorum.** Sıra sende.
