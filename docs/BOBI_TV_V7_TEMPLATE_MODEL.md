# Senaryo v7 — Şablon ve Diyalog Veri Modeli

Bu not `modules/senaryo_v7/models.py` içindeki kanonik veri sözleşmesini ve renderer/TTS uyumluluk kurallarını açıklar. Şablon kaynakları `modules/senaryo_v7/sablonlar/veri.json` içindedir.

## Her diyalog satırı

| Alan | Tip / sınır | Amaç |
|---|---|---|
| `karakter_ref` | string | Şablondaki kalıcı `Karakter` kartına referans; kaynak şablonda gösterim adı yerine kullanılır. |
| `metin` | string | Seslendirilecek Türkçe replik. |
| `ses` | `Duygu` enum | Kanonik duygu etiketi. `suprized`, `bikeyn`, `bikeyn_dramatik`, `soğuk` gibi eski değerler `sasirmis`, `bikkin`, `bikkin_dramatik`, `soguk` olur. Bilinmeyen etiket en yakın enum değerine eşlenir ve logging uyarısı üretilir. |
| `hiz` | float, 0.85–1.25 | Edge TTS/gTTS/espeak konuşma hızı çarpanı; sınır dışı değer aralığa clamp edilir. |
| `duraklamams` | int, 0–3000 ms | Bu satırın arkasındaki sessizlik. TTS zaman çizelgesi, birleşik WAV, altyazı ve animasyon zamanlamasına uygulanır; son satırın kuyruğunda video uzatılmaz. |
| `vurgukelimeler` | string listesi | Girilmemişse Türkçe replikten anlamlı sözcükler otomatik seçilir; boş dizi yerine güvenli fallback kullanılır. Eski `vurgu_kelimeler` adı renderer uyumluluğu için ayrıca yazılır. |
| `altyazistili` | enum: `normal`, `büyük`, `titreşimli`, `renkli` | Karaoke altyazı büyüklüğü/renk/hareket vurgusu. |
| `kamera` | enum: `cut`, `zoomin`, `zoomout`, `shake`, `whippan` | Satıra bağlı sahne hareketi. |
| `emojioverlay` | `string | null` | İsteğe bağlı tek emoji işareti. |
| `tahminisuresn` | float | Satırın tahmini konuşma süresi. Hız çarpanı ile hesaplanır; render QC gerçek ses süresini kullanmaya devam eder. |
| `rol` | enum: `hook`, `setup`, `escalation`, `twist`, `loopkapanis` | Hikâye ritmindeki replik görevi. |
| `twist` | bool | Twist satırı için açık bayrak; aynı satırın `rol` alanı da `twist` olur. |
| `sesid` | string | TTS'ye giden sabit karakter voice ID; legacy tüketiciler için satırda taşınır. |
| `karakter`, `cinsiyet`, `sfx` | legacy/render alanları | Eski pipeline'ı değiştirmeden çalıştırmak için JSON çıktısında tutulur; kaynak şablonlarda karakter adı yerine `karakter_ref` kullanılır. |

## Karakter kartı

`Karakter` modeli `ref`, `ad`, `cinsiyet`, `sesid`, `yasaraligi`, `kisiliknotu`, `varsayilanduygu` alanlarına sahiptir. Türkçe TTS kimlikleri cinsiyete göre sabittir: erkek karakterler `tr-TR-AhmetNeural`, kadın karakterler `tr-TR-EmelNeural`. Gelen uyuşmayan `sesid` değeri sessizce başka karaktere geçirilemez; sabit ID'ye normalize edilip loglanır. Aynı `karakter_ref`, şablon boyunca aynı kartı ve sesi çözer.

## Şablon yayın metadata'sı

- `etiketler`: hashtag listesi
- `hedefkitle`: hedef izleyici açıklaması
- `mevsimsellik`: ör. `Pazartesi`, `bayram`, `yılbaşı` (uygulanmıyorsa boş liste)
- `tekrarkullanimgunsayisi`: tekrar kullanım için en erken gün aralığı
- `performanspuani`: analytics tarafından güncellenecek başlangıç puanı
- `yasakkelimekontrolugecti`: kontrol durumunu belirten boolean

## Twist index uyumluluğu

Kanonik `Senaryo` ve `Sablon` modellerinde twist bir satır rolü/bayrağıdır; indeks domain modelinde tutulmaz. `modules/scenario.py` ve mevcut video/TTS tüketicileri kırılmasın diye `to_dict()` çıktısında `twist_indeksi` yalnızca türetilmiş uyumluluk alanı olarak üretilebilir. Eski index ile gelen girdiler migration sırasında doğru satırın `rol="twist"`, `twist=true` alanlarına dönüştürülür.

## Kontroller

`tests/test_senaryo_v7_models.py` typo normalizasyonu ve uyarı, alan sınırları, otomatik vurgu, sabit karakter sesi, kaynak JSON'da referans kullanımı, meta alanlar ve legacy twist migration'ını test eder. Genel kapılar:

```bash
pytest -q
mypy --strict
ruff check
ruff format --check
```
