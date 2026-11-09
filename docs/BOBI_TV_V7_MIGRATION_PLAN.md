# BOBİ TV Senaryo Motoru v7.0 — TODO Kararları ve Kabul Kriterleri

Bu dönüşüm, mevcut `modules/scenario.py` sözleşmesini korurken senaryo üretim çekirdeğini modüler ve test edilebilir hale getirir. Doğrulama kapsamı yeni v7 senaryo paketi ile geriye dönük uyumluluk façade'ıdır; video render/YouTube/TTS gibi senaryo dışı modüller bu lint kapsamına dahil edilmemiştir.

## 1. Tek dosyayı sorumluluklara böl

- **Neden gerekli:** Tek modülde şablon, migration, arşiv, kuyruk, zenginleştirme ve dosya yazımı bulunması değişiklikleri riskli kılar; bir katmandaki hata diğer davranışı da bozabilir.
- **Nasıl uygulanacak:** Yeni `modules/senaryo_v7/` paketi oluşturuldu: `sablonlar/`, `dogrulama/`, `zenginlestirme/`, `arsiv/`, `kuyruk/`, `cikti/`, ayrıca `models.py`, `ayarlar.py`, `loglama.py`, `service.py` ve `cli.py`. Eski `modules/scenario.py` küçük bir compatibility façade olarak kaldı.
- **Kabul kriteri:** Her alt modül tek sorumluluğa sahip; `from modules.scenario import senaryo_paketi_olustur` ve eski tek argümanlı çağrı değişmeden çalışıyor; testte paket dict alanları eski ana pipeline sözleşmesiyle aynı.

## 2. dict yerine tipli domain modelleri

- **Neden gerekli:** Serbest biçimli dict'lerde yazım hataları ve eksik alanlar çalışma anına kadar fark edilmez; farklı modüllerin aynı alanı farklı yorumlaması kolaylaşır.
- **Nasıl uygulanacak:** Pydantic ek bağımlılığı yerine standart kütüphane `dataclasses` ve manuel doğrulama seçildi. `Diyalog`, `Karakter`, `Senaryo`, `SenaryoPaketi`, `Sablon` modelleri alan açıklamaları/default'larla kuruldu. `Duygu`, `AltyaziStili`, `KameraHareketi`, `DiyalogRolu` enum'ları kullanılır. Diyalog satırı hız, sessizlik, vurgu kelimeleri, altyazı/kamera işaretleri ve tahmini süre taşır; karakter referansları sabit Ahmet/Emel voice ID kartlarına çözülür. `to_dict()` mevcut renderer/TTS mapping'ini korur.
- **Kabul kriteri:** Domain modelleri tipli, açıklamalı ve default/default_factory'ye sahip; v6 JSON -> model -> dict round-trip, etiket normalizasyonu/uyarı, karakter sesi tutarlılığı ve satır/şablon metadata testleri geçiyor. Satır rolü twist'in kanonik kaynağı; index sadece uyumluluk alanı.

## 3. Şema sürümü ve migration

- **Neden gerekli:** Arşiv ve Arena kuyruğunda eski v6 verileri kalabilir; yeni model bunları okuyamazsa üretim hattı kırılır.
- **Nasıl uygulanacak:** Yeni JSON'lara `semaversiyonu: "7.0"` ekleniyor. `migrate()` v6.0 nesnelerini, paket içindeki nested senaryoları ve `satirlar` biçimini otomatik `diyaloglar` alanına yükseltiyor. Daha ileri/uyumsuz şema sürümleri sessizce düşürülmüyor.
- **Kabul kriteri:** v6.0, `satirlar` ve nested package migration testleri geçiyor; girdi nesnesi mutate edilmiyor; v8 bilinmeyen şeması `SenaryoHatasi` veriyor.

## 4. Sihirli sayıları merkezi ayarlara taşı

- **Neden gerekli:** Süre, karakter, hook ve başlık sınırları kodun farklı yerlerine dağılırsa tutarsız kalite ve farklı ortamlarda farklı davranış oluşur.
- **Nasıl uygulanacak:** `Ayarlar` dataclass'ı varsayılanları ve açıklamaları merkezileştiriyor; `BOBI_SCENARIO_*` ortam değişkenleri override sağlayabiliyor. Öncelikli değerler arasında `0.36`, `1.6`, `38`, `34`, `88`, maksimum ilk replik sayısı `8`, 15sn yayın eşiği, TTS güvenlik payı ve uzatma sınırları var. TTS ve render süre kontrolleri de aynı Ayarlar sınıfını okuyor.
- **Kabul kriteri:** Örnek env override testleri geçiyor; geçersiz değerler anlaşılır `SenaryoHatasi` üretiyor; senaryo çekirdeğinde listelenen sabitler dağınık literal olarak tekrarlanmıyor.

## 5. print yerine logging

- **Neden gerekli:** `print` CI loglarını ayrıştırmayı, seviye filtresi uygulamayı ve dosyaya yönlendirmeyi zorlaştırır.
- **Nasıl uygulanacak:** v7 katmanları `logging` kullanıyor. `kur_logger()` seviye, console/file hedefi ve metin/JSON biçimini destekliyor; `BOBI_LOG_LEVEL`, `BOBI_LOG_FILE`, `BOBI_LOG_FORMAT` ile ayarlanıyor. CLI'nin JSON sonucu stdout'a yazması kullanıcıya yönelik çıktı olduğundan `print` değil, kontrollü stream yazımıdır.
- **Kabul kriteri:** JSON formatter yapılandırılmış zaman/seviye/logger/mesaj alanlarını veriyor; v7 paketinde tanısal `print()` bulunmuyor; dosya handler'ı açma hataları `CiktiHatasi` oluyor.

## 6. Docstring, type hint, mypy ve ruff

- **Neden gerekli:** Tipli arayüzler ve otomatik statik denetim, veri şeması değişikliklerinin runtime'dan önce bulunmasını sağlar.
- **Nasıl uygulanacak:** Yeni v7 paketinin fonksiyonları docstring ve type hint taşır. `pyproject.toml` ile senaryo v7 paketi, compatibility façade'ı ve testler için `mypy --strict` / `ruff check` kapsamı tanımlandı; geliştirici bağımlılıkları `requirements-dev.txt` içine alındı.
- **Kabul kriteri:** `mypy --strict` sıfır hata; `ruff check` ve `ruff format --check` temiz; test fonksiyonları ve yeni kod tip/docstring kurallarına uyuyor.

## 7. Alan bazlı hata sınıfları

- **Neden gerekli:** Bozuk şablon, JSON kuyruğu, arşiv ve yazma izin hatalarının tek bir `Exception` veya sessiz fallback olarak görünmesi sorunun kaynağını gizler.
- **Nasıl uygulanacak:** `SenaryoHatasi`, `SablonHatasi`, `KuyrukHatasi`, `ArsivHatasi` ve `CiktiHatasi` eklendi. Mesajlar yol/alan bilgisini taşır; bozuk kuyruk girdisi loglanıp tüketilir, yazılamayan çıktı kuyruğu ise kaybetmemek için kuyrukta bırakılır.
- **Kabul kriteri:** Her bozuk girdi ve yazılamayan hedef için doğru özel istisna test edilir; bir bozuk queue kaydı sonraki geçerli senaryoyu durdurmaz; çıktı hatasında kayıt korunur.

## 8. Enjekte edilebilir rastgelelik

- **Neden gerekli:** Global random state testleri kararsız yapar ve aynı senaryoyu yeniden üretmeyi zorlaştırır.
- **Nasıl uygulanacak:** `SenaryoUretici` `random.Random` nesnesi alabilir; `seed` verilirse `random.Random(seed)` kurar. Eski public fonksiyon `senaryo_paketi_olustur(video_no)` çağrısını korur ve isteğe bağlı `seed=` / `rng=` kabul eder. Seeded replay'de oluşturulma zamanı/senaryo dosya etiketi de sabitlenir.
- **Kabul kriteri:** Aynı seed ve video numarasıyla üretilen paket JSON'u birebir eşit; enjekte edilen aynı seed'li `Random` aynı kategori ve başlığı verir; global `random.seed()` gerekmiyor.

## Paket yapısı

```text
modules/
├── scenario.py                 # v6 import/signature uyumluluk façade'ı
└── senaryo_v7/
    ├── sablonlar/               # UTF-8 JSON şablonlar ve kategori açıklamaları
    ├── dogrulama/               # v6/satirlar migration + manuel şema doğrulama
    ├── zenginlestirme/          # hook, başlık, tahmini süre ve replik tamamlama
    ├── arsiv/                   # geçmiş, tekrar kontrolü ve kategori rotasyonu
    ├── kuyruk/                  # Arena kuyruk okuma/tüketme
    ├── cikti/                   # paket modeli, hash ve JSON yazımı
    ├── models.py                # Diyalog, Senaryo, SenaryoPaketi, Sablon
    ├── ayarlar.py               # varsayılanlar ve BOBI_SCENARIO_* override'ları
    ├── loglama.py               # seviye/dosya/JSON logging
    ├── service.py               # orchestration
    └── cli.py                   # uret/dogrula/migrate
```

## Çalıştırma ve test

```bash
python -m pip install -r requirements-dev.txt
pytest -q
mypy --strict
ruff check
ruff format --check
python -m modules.senaryo_v7.cli --help
```

Bu TODO listesindeki hiçbir madde ertelenmedi veya atlanmadı. Bilinçli seçim: Pydantic yerine standard-library dataclasses + manuel doğrulama kullanıldı; böylece production bağımlılık kümesi büyümeden Türkçe model sözleşmeleri ve doğrulama sağlandı.
