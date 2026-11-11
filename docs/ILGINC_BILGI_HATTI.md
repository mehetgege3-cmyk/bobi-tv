# İlginç Bilgi İçerik Hattı (v8.0)

> Kullanıcı kararı (2026-11-11): *"Bu kategorileri, formatı ve konuların hepsini çöpe at.
> Hiçbir kullanıcı bu saçmalıklara zaman ayırmaz."*
> Eski VS/Clash diyaloğu, iki karakter düellosu ve "😱 … Şoke Etti" kalıbı **kaldırıldı**.

## 1. Yeni format (zorunlu)

```
🧠 Günün Merak Uyandıran Sorusu
<tek cümlelik merak sorusu>

🔍 Cevabı Biliyor Muydun?
<200–300 kelime, sohbet tonu, günlük hayat örneği>

💡 Şaşırtıcı Sonuç
<1–2 cümlelik kapanış>
```

Başlıklar **ekranda görünür, sesli okunmaz** (`diyaloglar[].ekran_basligi`).
Seslendirme tek anlatıcı (BOBİ). Ölçülen süre: 220–260 kelime ≈ **75–97 sn** →
180 sn YouTube tavanının altında, Shorts olarak yayınlanabilir.

## 2. Sekiz kategori (her paylaşımda rastgele biri)

| # | Anahtar | Ad | Palet |
|---|---|---|---|
| 1 | `bilim_teknoloji` | Bilim ve Teknoloji | koyu mavi → camgöbeği |
| 2 | `tarih_medeniyet` | Tarih ve Medeniyetler | toprak → altın |
| 3 | `doga_evren` | Doğa ve Evren | gece → mor |
| 4 | `hayvanlar` | Hayvanlar ve Canlılar | orman → nane |
| 5 | `insan_vucudu` | İnsan Vücudu ve Biyoloji | koyu kırmızı → pembe |
| 6 | `yiyecekler` | Yiyecekler ve Beslenme | bal → sarı |
| 7 | `kulturler` | Kültürler ve Gelenekler | mor |
| 8 | `gunluk_yasam` | Günlük Yaşam ve İlginç Olaylar | petrol → turkuaz |

"Rastgele" = **tekrarsız rastgele**: son 8 videoda çıkan kategori seçilmez
(tam döngü garantisi). Paletler birbirinden ayrı → her video farklı görünür.

## 3. On iki kural → on iki denetim fonksiyonu

`modules/ilginc_bilgi/kurallar.py` — her kural bağımsız `Ihlal` üretir
("kalite 68/100" gibi anlamsız tek sayı yerine **düzeltilebilir** çıktı).

| Kod | Kural | Ağırlık |
|---|---|---|
| R1 | Merak uyandıran soruyla başla (soru işareti şart) | 3 |
| R2 | Cevabı hemen verme (ilk cümlede sızmamalı) | 2 |
| R3 | Sohbet tonu (resmî dil yasak) | 2 |
| R4 | Az bilinen bilgi (klişe ifade yasak) | 1 |
| R5 | Doğruluk → `dogruluk.py` | 3 |
| R6 | Önceki konuları tekrar etme (kelime örtüşmesi >%55) | 3 |
| R7 | Kategori geçişi | 2 |
| R8 | **200–300 kelime** (alt sınır kritik) | 3 |
| R9 | Günlük hayattan örnek | 2 |
| R10 | Sade Türkçe (cümle >26 kelime ort., tek cümle >35) | 2 |
| R11 | Emoji (2–12) | 1–2 |
| R12 | Tamamen Türkçe (İngilizce işlev kelimesi = kritik) | 3 |

## 4. Doğruluk: "uydurma bilgi yok" nasıl kodla garanti ediliyor

`modules/ilginc_bilgi/dogruluk.py`

1. **Kaynak zorunlu.** Kart `kaynak` alanında gerçek kurum/kitap/dergi adı
   taşımak zorunda. "internette okudum" gibi zayıf kaynak reddedilir.
2. **Tehlikeli iddia kara listesi.** "tedavi eder", "kanseri yener",
   "garanti kazanç" → kesin RED (T3 sürçme ve T4 ters psikoloji de bu
   kategorilerde yasak).
3. **Çürütülmüş bilgi bankası.** %10 beyin, dil haritası, sakız 7 yıl,
   at nalı yengeci kanı, tıraş kılı… (14 kayıt) — bunlar **gerçek gibi
   sunulamaz**; ancak **çürüten** içerik yapılabilir (T1 taktiğinin malzemesi).
4. **Aşırı kesinlik sınırı.** "asla/her zaman/kanıtlanmıştır/%100" en fazla 1.
5. **Arena çökerse üretim durmaz:** `yedek_bilgiler.py` içinde 3 doğrulanmış
   bilgi (ahtapot kalpleri, köpekbalığı evrimi, Kleopatra–piramit–Ay).
   Banka tükenirse **üretim o tur durur** — uydurmaktansa durmak doğru.

## 5. Etkileşim taktikleri (rotasyon + yasaklar)

`modules/ilginc_bilgi/etkilesim.py` (doküman: `docs/ETKILESIM_TAKTIKLERI.md`)

- 10'luk rotasyon: `T1 T2 T5 T4 T6 T1 T2 T5 T4 T6`
- 20'de bir `T3` (sürçme) — **ama** yetkinlik kanıtı (≥20 yayın) ve
  hassas olmayan kategori şartıyla
- **Yasak:** `saglik/beslenme/insan_vucudu/para/guvenlik/hukuk/gunluk_yasam`
  kategorilerinde `T3` ve `T4`
- `T3` sürçmesi **düzeltilmeden bırakılamaz**: `t3_duzeltme_dogrula()`
  "pardon/doğrusu/düzeltiyorum" izi arar; yoksa içerik reddedilir
  (YouTube *deceptive practices* riski)

## 6. Video hattı değişmedi

`senaryo_paketi` sözleşmesi korunur; `tts_engine` ve `video_render` aynen
çalışır. Değişenler:

- `diyaloglar` = 1 kanca + 5 gövde parçası + 1 sonuç (tek anlatıcı)
- Yeni alanlar: `soru`, `dogru_bilgi`, `kaynak`, `sayilar`, `kapak_baslik`,
  `taktik`, `tam_metin`, `kelime_sayisi`, `format`
- `semaversiyonu = "8.0-ilginc"` → render/kapak bu bayrağı görüp
  VS sahnesini, eski şok şeritlerini ve çift balon düzenini atlar

### Bu tur bulunan ve düzeltilen gerçek hatalar

| Hata | Etki | Düzeltme |
|---|---|---|
| `_ses_suresi` yalnız `ffprobe` kullanıyordu, yoksa 2.0 sn dönüyordu | 96 sn ses "2 sn" sayıldı, render minimum süre kapısına takıldı | önce `wave` ile okuma |
| Bozuk/boş TTS çıktısı (97 kelime → 0.37 sn) | **sessiz video yayınlanabilirdi** | beklenen süreye göre 2 kez yeniden deneme + net hata |
| Balon 4 satırla sınırlıydı | Metnin yarısı ekranda kayboluyordu | 10 satır + taşarsa "…" + günlük log |
| Tek anlatıcıda eski balon ekranda kalıyordu | İki kart üst üste, okunmuyordu | `semaveriyonu 8.0` → yalnız aktif balon |
| `ffmpeg` thread/lookahead | 2 GB sandbox'ta OOM-kill | `RENDER_THREADS`, `RENDER_X264_PARAMS` env |
| Kapak başlığı `baslik[:34]` | "…BİRİ Y!" gibi kelime ortası kesme | `kapak_basligi()` tam kelime sınırı |
| Emoji fontu sunucuda yok | Kapakta "tofu" kutusu | vektörel halka + "?" rozeti |

## 7. Yapılandırma

| Env | Varsayılan | Anlamı |
|---|---|---|
| `ILGINC_BILGI_AKTIF` | `1` | `0` → eski VS hattı (geri dönüş sigortası) |
| `KONUSMA_KELIME_DK` | `180` | süre tahmini için konuşma hızı |
| `BALON_AZAMI_SATIR` | `10` | konuşma balonu satır sınırı |
| `RENDER_THREADS` | `2` | ffmpeg thread sayısı (bellek koruması) |
| `RENDER_X264_PARAMS` | `rc-lookahead=10:ref=2:bframes=2` | x264 bellek ayarı |
| `RENDER_PRESET` | `fast` | düşük RAM'de `ultrafast` |
