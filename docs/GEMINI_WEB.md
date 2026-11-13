# Gemini WEB ile Görsel Üretimi — Çalışan Yol (2026-11-13)

**Durum: ✅ ÇALIŞIYOR.** API anahtarı gerekmez; `gemini.google.com` oturum
çerezi yeterli. Bu, `limit: 0` veren `GEMINI_API_KEY` yolunun yerini alır.

**Canlı kanıt (gerçek dosyalar):**
| Dosya | Boyut | Ölçü | Not |
|---|---|---|---|
| `kanit/gemini/web_elma.png` | 27.690 B | 286×512 | ilk başarılı istek (küçük URL) |
| `kanit/gemini/modul_test.png` | 238.200 B | **1408×768** | `=s2048` büyük boy |
| `kanit/gemini/dikey_test.jpg` | 265.369 B | **768×1376** | dikey zorlaması (oran 1.79 ≈ 9:16) |

---

## 1. Gereken çerezler

`GEMINI_COOKIES` secret'ı — **"ad=değer; ad=değer"** biçiminde (JSON dizi de kabul).

| Çerez | Rol | Ömür |
|---|---|---|
| `__Secure-1PSID` | **ana oturum** — zorunlu | uzun (≈ yıllar) |
| `__Secure-1PSIDTS` | zaman damgası — önerilir | **kısa**; `RotateCookies` ile yenilenir |
| `SID/HSID/SSID/APISID/SAPISID/NID` | tam oturum (daha sağlam) | değişken |

**Toplam yazılan:** 21 çerezden 11'i seçildi → **1520 karakter**.

> ⚠️ **Gemini sekmesini AÇIK BIRAKMA.** Tarayıcı token'ı yeniledikçe eski kopya
> yetim kalır ve çerez daha hızlı ölür.

## 2. Uçlar

| Uç | Amaç |
|---|---|
| `https://gemini.google.com/app` | `SNlM0e` (CSRF/at) jetonu — HTML içinde |
| `https://gemini.google.com/_/BardChatUi/data/assistant.lamda.BardFrontendService/StreamGenerate` | üretim |
| `https://accounts.google.com/RotateCookies` | `__Secure-1PSIDTS` yenileme (kullanılmıyor) |

**Sorgu:** `?hl=tr&_reqid=100000&rt=c`

**Başlıklar (zorunlu):**
```
cookie: <GEMINI_COOKIES>
content-type: application/x-www-form-urlencoded;charset=UTF-8
origin: https://gemini.google.com
referer: https://gemini.google.com/app
x-same-domain: 1
x-goog-ext-525005358-jspb: ["<UUID>",1]
user-agent: <Chrome UA>
```

## 3. Gövde biçimi — EN KRİTİK KISIM

İlk denemem **HTTP 400** verdi çünkü iç listeyi yanlış kurdum. Doğrusu
`gemini_webapi` 2.1.1 `client.py` kaynağından **okunarak** alındı (K1 kuralı):

```python
ic = [None] * 81
ic[0]  = [prompt, 0, None, None, None, None, 0]   # mesaj
ic[1]  = ["tr"]                                    # dil
ic[2]  = ["", "", "", None, None, None, None, None, None, ""]  # metadata (10 öğe)
ic[6]  = [1]
ic[7]  = 1        # STREAMING_FLAG_INDEX
ic[10] = 1
ic[11] = 0
ic[17] = [[0]]
ic[18] = 0
ic[27] = 1
ic[30] = [4]
ic[41] = [1]
ic[53] = 0
ic[61] = []
ic[68] = 1
ic[79] = 1        # model numarası (1 = varsayılan)
ic[80] = 1
ic[59] = str(uuid.uuid4()).upper()

f_req = json.dumps([None, json.dumps(ic)])        # ← DIŞ sarmalayıcı ŞART
govde = urlencode({"at": SNlM0e, "f.req": f_req})
```

**Tuzak:** `f.req = json.dumps([[None, ic, None, "!id"]])` **YANLIŞ** → 400.
Doğrusu 2 öğeli `[None, "<json string>"]`.

## 4. Yanıttan görsel çıkarma

```python
re.findall(r"https://[A-Za-z0-9._/-]*googleusercontent\.com/[A-Za-z0-9._/=-]+", yanit)
```
- İndirirken **de çerez gerekir**.
- URL'in sonuna **`=s2048`** eklenirse büyük boy gelir:

| URL biçimi | Gelen ölçü | Bayt |
|---|---|---|
| aynen | 286×512 | 27.690 |
| `=s2048` | **1408×768** | 238.200 |

## 5. Dikey (9:16) zorlaması — Shorts için ŞART

Gemini varsayılanı **yatay** üretiyor (1408×768). Kapak 1080×1920 dikey olduğu
için yatay görseli kırpmak görselin çoğunu atar.

**Çözüm:** istemin sonuna şunu ekle:
```
ÖNEMLİ: Görsel DİKEY (9:16, portre) olsun. Yazı, harf, logo koyma. Soru sorma, yap.
```
**Ölçüldü:** → 768×1376, oran 1.79 (9:16 = 1.78) ✅

## 6. Kapak hattındaki sıra (güncel)

1. **Gemini WEB** (çerez) → `kaynak=gemini_web`  ← **yeni, çalışan**
2. Arena (çerez canlıysa) → `kaynak=arena_gorsel`
3. Gemini API (kota varsa) → `kaynak=gemini_gorsel`
4. Video karesi (her zaman) → `kaynak=video_karesi`

## 7. Kod

| Dosya | Ne yapar |
|---|---|
| `modules/gemini_web.py` | `cerez()`, `hazir_mi()`, `jeton()`, `gorsel_uret()`, `durum()` |
| `tools/gemini_cerez_kur.py` | çerezi doğrular (`--kuru`) + secret'a yazar |
| `tests/test_gemini_web.py` | 6 test (`f.req` 81 öğe yapısı dahil) |

## 8. Teşhis tablosu

| Belirti | Sebep | Çözüm |
|---|---|---|
| `HTTP 400` | `f.req` biçimi yanlış | 2 öğeli `[None, "<json>"]` kullan |
| `HTTP 401/403` | oturum ölü | yeni çerez export et |
| `SNlM0e bulunamadı` | giriş yapılmamış | tarayıcıda giriş → export |
| `accounts.google.com'a yönlendi` | oturum yok | yeniden giriş |
| yanıtta görsel URL yok | güvenlik filtresi / limit | istemi yumuşat, bekle |
| çerez 1-2 gün sonra ölüyor | `1PSIDTS` süresi + sekme açık | yeniden export |

## 9. Sınırlar (dürüst)

- Google bu **özel arayüzü** haber vermeden değiştirebilir; resmî API değil.
- Ağır kullanımda Google limit koyabilir; nazik aralık bırakılmalı.
- Üretilen görsellerde **SynthID** filigranı olabilir.
- `__Secure-1PSIDTS` kısa ömürlü → periyodik yenileme gerekir.

---

## 10. ÜRETİMDE DOĞRULANDI (2026-11-13, koşu `43375662500`)

**Sonuç: ✅ GERÇEK ÜRETİMDE ÇALIŞTI.**

```
[GeminiWeb] ✅ görsel indi: 162058 bayt → ..._gemini_web.jpg
[Kapak] Seçilen: ..._kapak.jpg | kaynak=gemini_web
🖼️ Kapak: ... | kaynak: gemini_web | ilk kareye gömüldü: EVET
[YouTube] 🚀 Yayınlandı: https://www.youtube.com/shorts/eaIy0nXb7mI
=== Tamamlandı: 1 yayınlandı, 0 kuyrukta (175sn) ===
```

| Ölçüm | Değer |
|---|---|
| Koşu süresi | **175 sn** (önceki Arena'lı koşu 465 sn) |
| Kapak kaynağı | **`gemini_web`** (ilk kez Arena DEĞİL) |
| Görsel boyutu | 162.058 bayt → 1080×1920 kapak |
| Video | https://www.youtube.com/shorts/eaIy0nXb7mI |
| Konu | `uykuda_beyin_temizligi` |

**Kanıt dosyaları:** `kanit/uretim_gemini/.../*_kapak.jpg`,
`*_gemini_web.jpg`, `*_kapakli.mp4`.

**Öğrenilen:** Gemini web yolu Arena'dan **~290 sn daha hızlı** (çerez 401
freni ve hash bekleme yok). Kapak ilk kareye doğru gömüldü, çift başlık
kusuru yok (Arena görselinde `KAPAK_BASLIK_BINDIR` kuralı geçerli değil —
Gemini isteminde "yazı koyma" var).

**GEMINI_COOKIES workflow'lara bağlandı:** `canli_test.yml` + `hourly_production.yml`.

## 11. KULLANILAN KAPAK İSTEMİ (tam metin)

Örnek dosya: **`docs/ornek_kapak_istemi.txt`** (gerçek üretimden).

### Ölçümler (konu: `uykuda_beyin_temizligi`)

| Parça | Karakter |
|---|---|
| Sabit tasarım şablonu | 1488 |
| Dikey (9:16) zorlama eki | 85 |
| **Video metni** | **1660** (düzeltmeden ÖNCE **41** ❌) |
| **Gönderilen toplam** | **3192** |

### Şablon (sabit kısım)

```
Sen YouTube Shorts için kapak (thumbnail) tasarlayan bir görsel tasarımcısısın.
Aşağıda bir videonun TAM METNİ var. Önce metni baştan sona dikkatlice oku,
konuyu ve en şaşırtıcı noktayı belirle; sonra bu videoya kapak olacak TEK bir
dikey (9:16) görsel ÜRET.

GÖRSELİN AMACI: izleyici akışta kaydırırken durup tıklasın, sonuna kadar
izlesin, beğenip yorum yazsın.

TASARIM KURALLARI (profesyonel, üzerine düşünülmüş):
1) Metnin en çarpıcı/sürpriz fikrini tek bir sahneyle anlat; soyut değil somut.
2) Güçlü görsel hiyerarşi: baskın tek özne, sade arka plan, yüksek kontrast,
   net siluet, merkezde/üst 2/3'te özne (alt alan yazı/arayüz için boş kalsın).
3) Duygu ve merak: şaşkınlık, ölçek farkı, beklenmedik detay, 'bu nasıl olur'.
   Abartılı sahte şok, korku, kan, şiddet, çıplaklık YOK.
4) Renk: sıcak-soğuk kontrastı, tek baskın renk + tek vurgu rengi, sinematik ışık.
5) Stil: modern, sinematik, 3D/fotoğrafik gerçekçilik; jenerik stok görsel değil.
6) GÖRSELİN İÇİNE YAZI KOYMA. Kelime, sayı, harf, logo, filigran olmasın.
7) 9:16 dikey, telefon ekranında küçük boyutta bile anlaşılır olsun.

Şimdi görseli üret. Sadece görsel döndür; açıklama, metin veya kod yazma.
Soru sorma, yap. Tek bir görsel üret; birden fazla aday üretip seçenek sunma,
onay isteme.

=== VİDEO METNİ (TAM) ===
<videonun tam metni buraya gömülür>
=== VİDEO METNİ SONU ===

ÖNEMLİ: Görsel DİKEY (9:16, portre) olsun. Yazı, harf, logo koyma.
Soru sorma, yap.
```

## 12. YAKALANAN KUSUR (2026-11-13, üretim sonrası)

**Belirti:** Kapak üretildi ama isteme giden "video metni" yalnızca
**41 karakter** = videonun BAŞLIĞI (`Beyin Asıl Temizliğini Uyurken Yapıyor! 🧠`).

**Kök neden:** `video_metni()` şu sırayı deniyordu:
`senaryo.tam_metin` → `metin` → `senaryo.diyaloglar` → **`baslik`**.
İlginç-bilgi bankası kaydında bu alanların hiçbiri yok; içerik
`soru` + `cevap` + `sonuc` alanlarında. Bu yüzden **başlığa düştü**.

**Etki:** Kullanıcının "tam video metni → kapak" kuralı ihlal ediliyordu;
kapak 41 karakterlik başlıktan üretiliyordu (yine de konuyla uyumlu çıktı
çünkü başlık açıklayıcıydı — ama garanti değil).

**Düzeltme:** `video_metni()` içine **ilginç-bilgi yolu** eklendi:
`soru` + `cevap` + `sonuc` birleştirilir.

**Doğrulama:** aynı konu için video metni **41 → 1660 karakter**;
toplam istem **3192 karakter**. Testler: **679 passed, 1 skipped** (2026-11-13 güncel).
