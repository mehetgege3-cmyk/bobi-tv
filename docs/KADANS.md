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

---

# BÖLÜM 5 — BAĞLAYICI KURAL (taşındı)

> Bu bölüm eskiden `docs/BOBI_TV_V6_PRO_MIMARI_VE_KURALLAR.md` içindeydi.
> O dosya 2026-11-13'te silindi (tarihsel, %90'ı eski V6 planı); **yürürlükteki
> tek kadans kuralı buradadır**. Çelişki hâlinde bu bölüm ve `modules/kadans.py`
> esas alınır.

## ⏱️ Bölüm 5: ÜRETİM KADANSI — 8 SAATTE BİR (2026-11-11 kuralı, GÜNCELLENDİ)

Bu bölüm **bağlayıcı kuraldır** (normatif). Çelişki hâlinde bu bölüm ve
`modules/kadans.py` esas alınır.

> **DEĞİŞİKLİK KAYDI (2026-11-11):** Önceki kural "her 15 dakikada bir" idi.
> Ölçüm kanalı yaktığını gösterdi: 1 saatte silinen 21 videonun ortalama
> izlenmesi **0.8**, hiçbiri Shorts akışına girmedi, günde ~22 yükleme +
> aynı gün silme YouTube'a "yükle-sil" spam sinyali verdi. Yeni rejim:
> **8 saatte bir = günde 3 video, sabit saatler (00/08/16 UTC).**

### K1 — Kadans tanımı

Üretim ve yükleme **8 saatte bir** denenir (günde 3).

| Sabit | Değer | Yeri | Doğrulama |
|---|---|---|---|
| `KADANS_DK` | `480` | `modules/kadans.py` | test |
| `KADANS_CRON` | `0 */8 * * *` | `modules/kadans.py` | test |
| Workflow cron | `0 */8 * * *` | `.github/workflows/hourly_production.yml` | test (ikisi eşit) |
| Katalog kaydı | `KADANS_DK` seçenekleri `480/240/65` | `modules/ayar_katalogu.py` | test |
| `IZLENME_KONTROL_DK` | `360` (6 saat) | `main_pipeline.py` | test |
| `MIN_IZLENME_ESIGI` | `100` | `main_pipeline.py` | test |

### K2 — Kadans ≠ yükleme sayısı

8 saat **zamanlamadır**, yükleme kotası değildir. **Günlük yükleme tavanı
YOKTUR** (eski `GUNLUK_MAKS=6` tavanı 2026-11-11'de kaldırıldı). 8 saatlik
kadans günde 3 **fırsat** yaratır ve üretilen her video yüklenir. Tek engel
YouTube'un kendi 403 `quotaExceeded` hatasıdır: o an video stoğa alınır, kota
açılınca (UTC 00:00) yüklenir — üretim durmaz.

### K3 — Düşük izlenme silme eşiği: 6 saat / 100 izlenme

- ❌ Eski: 1 saatte 100 izlenme almayan video silinir. **Çok erkendi** —
  Shorts dağıtımı ilk saatte genelde test aşamasındadır; 1 saatte 0-4
  izlenme "içerik kötü" değil "henüz dağıtılmadı" demekti.
- ✅ Yeni: **6 saat** sonunda 100 izlenme. Silme hâlâ geri alınamaz; geçmiş
  silmeler arşivde `silindi_dusuk_izlenme` olarak durur.

### K4 — Kota ve hedef no-op → YEŞİL

Kota dolu veya günlük hedef tamam ise koşu **başarısız sayılmaz** (`exit 0`).
`KOTA_DOLU_DAVRANIS` varsayılanı `sessiz_dur`'dur.

### K5 — GitHub cron'una güvenilmez

`0 */8 * * *` yazmak 8 saatte bir çalışacağı anlamına gelmez (ölçüm: `*/10`
fiilen günde 1-2 koşuya düştü). **Birincil tetikleyici, koşu bitince bir
sonrakini açan zincirleme adımıdır** (`hourly_production.yml`); GitHub cron
yalnızca **yedektir**. Kurulum: `docs/TETIKLEYICI_KURULUM.md`.

### K6 — Kalite kadansın önünde

Kadans değişikliği kalite eşiğini düşürmez. Kalite kontrolünü geçmeyen video
sırf süre doldu diye yayımlanmaz; eksik üretim açıkça raporlanır.

### K7 — Geri dönüş ölçütü

1 hafta sonra: yükleme başına ortalama izlenme, 6 saatte 100 eşiğini geçen
video oranı ve ölçülen kadans (`modules/cadans_olcum.py`). İyileşme varsa
kullanıcı kararıyla 65 dakikaya (günde ~22) çıkılabilir.
---
