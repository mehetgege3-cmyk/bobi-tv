# Üretim Kadansı — 8 SAATTE BİR (günde 3 video)

**Güncel karar: 2026-11-11.** Önceki "her 15 dakikada bir" kadansı **iptal
edildi** — ölçümler kanalı yaktığını gösterdi.

## Neden değişti (kanıt)

| Ölçüm | Değer |
|---|---|
| 1 saatte silinen video sayısı | 21 |
| Bu videoların 1 saatte aldığı izlenme | 0,0,…,1,1,2,2,2,2,2,4 |
| Ortalama izlenme | **0.8** |
| 100+ izlenme alan | **0** |
| Günlük yükleme (9/10/11 Kasım) | 4 → 11 → **22** |

Yorum: videolar Shorts akışına **hiç girmiyordu**. 15 dakikada bir yükleme +
1 saatte silme döngüsü YouTube'a net bir **"yükle-sil" spam sinyali** veriyor.
Kanal istatistiklerinin düşmesi bunun sonucu.

## Yeni rejim

| Parametre | Eski | Yeni | Nerede |
|---|---|---|---|
| `KADANS_DK` | 15 | **480** (8 saat) | `modules/kadans.py` |
| `KADANS_CRON` | `*/15 * * * *` | **`0 */8 * * *`** (00/08/16 UTC) | `modules/kadans.py` + `hourly_production.yml` |
| Günlük video | ~22 | **3** | — |
| `IZLENME_KONTROL_DK` | 60 (1 saat) | **360** (6 saat) | `main_pipeline.py` |
| `MIN_IZLENME_ESIGI` | 100 | 100 (değişmedi) | `main_pipeline.py` |

**Neden sabit saatler:** algoritma için "tahmin edilebilir yayın saati"
düzensiz aralıktan iyidir; ayrıca 6 saatlik izlenme kontrolü tam olarak bir
sonraki yükleme penceresine denk gelir.

## Günlük yükleme tavanı

**YOK** (kullanıcı kararı 2026-11-11: "kotayı kaldır"). Kadans yalnızca
*ne zaman deneneceğini* belirler. Tek gerçek engel YouTube'un kendi 403
`quotaExceeded` hatasıdır; o an video stoğa alınır, kota açılınca yüklenir.

## Ölçüm ve geri dönüş

- Panel: `🛠 Sistem → 📉 Cadans` satırı **ölçülen** koşu aralığını gösterir
  (cron ifadesine değil, gerçek koşulara bakar — `modules/cadans_olcum.py`).
- 1 hafta sonra bakılacak: yükleme başına ortalama izlenme, 6 saatte 100
  eşiğini geçen video oranı, cadans gerçekleşme oranı.
- İyileşme görülürse kullanıcı kararıyla 65 dakikaya (günde ~22) çıkılabilir;
  panelden `KADANS_DK` değişir **ama** workflow cron'u da güncellenmeli.

## Zincirleme (cron'a güven yok)

GitHub cron'u güvenilmez (ölçüm: `*/10` fiilen günde 1-2 koşu). Birincil
tetikleyici, koşu bitince bir sonrakini açan **zincirleme adımıdır**
(`hourly_production.yml` → "Bir sonraki 8 saat turunu zincirle"). Slot
yöntemi: son koşu başlangıcı + `KADANS_DK`; çift tetikleme koruması var.
