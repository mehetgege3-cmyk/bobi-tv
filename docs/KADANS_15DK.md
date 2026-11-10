# ⏱️ Üretim Kadansı — Her 15 Dakikada Bir

**Karar tarihi:** 2026-11-11
**Tek doğruluk kaynağı:** `modules/kadans.py`
**Bağlayıcı kural:** `docs/BOBI_TV_V6_PRO_MIMARI_VE_KURALLAR.md` → Bölüm 5
**Özet:** `SKILL.md` → §7.5

---

## 1. Ne istendi, ne yapıldı

**İstek:** "Her 15 dakikada bir video üretilip kanala yüklensin."

**Yapıldı:**
- `KADANS_DK = 15` — `modules/kadans.py` (tek kaynak)
- `hourly_production.yml` cron → `*/15 * * * *`
- Katalogda `KADANS_DK` ayarı (panelden 15/30/60 seçilebilir)
- `GUNLUK_HEDEF` günlük toplam oldu (koşu başına değil) — bkz. §4
- Çıkış kodu günlük toplama bağlandı — 96 kırmızı tik yerine no-op yeşil
- SKILL.md, kural dosyası ve bu doküman güncellendi

---

## 2. En önemli ayrım: kadans ≠ yükleme sayısı

"Her 15 dakikada bir video" cümlesi **iki ayrı şeyi** birleştiriyor. Sistem
ikisini ayrı tutar, çünkü biri ücretsiz, diğeri platform sınırına bağlı:

| Kavram | Anlamı | Değer | Sınır |
|---|---|---|---|
| **KADANS_DK** | Ne sıklıkta **deneneceği** (zamanlama) | **15 dk** | Yok — ücretsiz |
| **GUNLUK_MAKS** | Günde kaç **yükleme** yapılacağı | varsayılan **6** | **Kota: 10.000 / 1.600 = 6** |
| **GUNLUK_HEDEF** | Günde **en az** kaç yayın | varsayılan **2** | ≤ GUNLUK_MAKS |

### Matematik (Google'ın sabiti, değiştirilemez)

```
YouTube Data API günlük kota     : 10.000 birim
videos.insert maliyeti           :  1.600 birim
─────────────────────────────────────────────────
Günde en fazla yükleme           :      6 video
15 dakikalık kadansla fırsat     :     96 koşu   (24×60/15)
Kota dolduktan sonra kalan       :     90 no-op tur
Fiili yükleme aralığı (6/gün)    :    240 dk  → 4 saatte 1 video
Fiili yükleme aralığı (4/gün)    :    360 dk  → 6 saatte 1 video
```

**Sonuç:** Sistem günde **96 kez uyanır**, günün ilk ~90 dakikasında kotayı
doldurur, sonra sessizce bekler. Bu **atıl kapasite değil**, platformun sabit
sınırıdır. Kota artırımı YouTube'a başvuru gerektirir (ücretsiz, ama onay süreci
vardır); o güne kadar 6 tavanı geçerlidir.

### Dürüstlük kuralı

Hiçbir yerde "her 15 dakikada bir video **yayınlanıyor**" denmez. Doğru cümle:

> "Her 15 dakikada bir üretim denenir; kota günde 6 yükleme izin verdiği için
> gerçekte 4 saatte 1 video yayınlanır."

Bu cümle `modules/kadans.py → kota_uyarisi()` tarafından üretilir ve log ile
Telegram panelinde aynen görünür.

---

## 3. GitHub cron'una güvenilmez

`*/15 * * * *` yazmak 15 dakikada bir çalışacağı anlamına **gelmez**.

| Ölçüm | Sonuç |
|---|---|
| 2026-11-10, cron `*/10` | Fiilen **günde 1–2 koşu** |
| 2026-11-10, üretim | 01:46'dan sonra **16 saat hiç koşmadı** |
| Telegram poller, `*/5` | Günde 2 koşu, aralar **168 dk** |

**Bu yüzden:** birincil tetikleyici **dış dağıtıcı** olmalıdır.

```
cron-job.org (15 dk)  ──POST──▶  /actions/workflows/hourly_production.yml/dispatches
                                   │
                                   ▼
                          hourly_production.yml çalışır
                                   ▲
GitHub cron '*/15'  ───────────────┘  (yalnızca YEDEK)
```

Kurulum adımları: `docs/TETIKLEYICI_KURULUM.md`.
Dış dağıtıcı ayarlanmazsa kadans **kâğıt üzerinde 15 dakika, gerçekte günde
1–2 koşu** olur. Bu doküman bunu gizlemez.

**Gerçek sıklık denetimi:** workflow'un ilk adımı "son koşudan bu yana geçen
dakika"yı loglar. 15 dk ayarında **15–20** görmelisin. **60+** görüyorsan dış
dağıtıcı ölmüş, cron yedeğe düşmüşsündür. **Telegram → Ayarlar → Sistem
durumu** ekranı da poller ve tetikleyici sağlığını gösterir.

---

## 4. GUNLUK_HEDEF tuzağı (2026-11-11'de kapatıldı)

**Eski davranış:** `GUNLUK_HEDEF` **koşu başına** video sayısıydı
(`for i in range(1, GUNLUK_HEDEF + 1)`).

15 dakikalık kadansta bu felaket olurdu:

```
96 koşu/gün × 4 video/koşu = günde 384 üretim denemesi
Kota 6'da keser → 378 koşu boşa, her biri video render maliyeti
```

**Yeni davranış:** `GUNLUK_HEDEF` = **günlük toplam**.

```python
kalan_hedef = max(0, GUNLUK_HEDEF - bugunki)
kalan_kota  = max(0, GUNLUK_MAKS  - bugunki)
bu_tur      = min(kalan_hedef, kalan_kota)   # 0 ise no-op, exit 0
```

Kadans sıkılaşsa bile **günlük yükleme sayısı değişmez**. Yalnızca 6 yüklemeyi
günün hangi saatlerinde yaptığın değişir (15 dk kadansta ilk 90 dakikada,
saatlikte 6 saate yayılmış).

**Çıkış kodu da düzeltildi:** eski kod `basarili_toplam >= GUNLUK_HEDEF` idi;
bu turda 1 video yükleyip hedef 4 ise koşu **kırmızı** oluyordu → 96 kırmızı
tik + 96 otonom self-repair denemesi. Artık günlük toplama bakıyor.

---

## 5. Ayarlar (panelden değiştirilebilir)

**Telegram → ⚙️ Ayarlar → 🎯 Üretim & Kota**

| Ayar | Seçenekler | Varsayılan | Etkisi |
|---|---|---|---|
| `KADANS_DK` | 15 / 30 / 60 | **15** | Workflow cron'u da değişmeli (kod değişikliği) |
| `GUNLUK_HEDEF` | 1 / 2 / 4 | **2** | Günlük toplam hedef (kota tavanına kırpılır) |
| `GUNLUK_MAKS` | 2 / 5 / 6 | **6** | Kota tavanı — 6'yı geçemez (Google sabiti) |
| `KOTA_DOLU_DAVRANIS` | `sessiz_dur` / `hata` | **sessiz_dur** | Dolu → yeşil no-op / kırmızı tik |

> ⚠️ `KADANS_DK` panelden değiştirmek workflow cron'unu **değiştirmez** —
> cron YAML'da yaşar. Katalog açıklaması bunu yazar. Tam etki için üç yeri
> birlikte güncelle: `modules/kadans.py`, workflow cron, dış dağıtıcı interval.

---

## 6. Değişiklik prosedürü

Kadansı değiştirmek **üç yeri birlikte** gerektirir. Biri kalırsa
`tests/test_kadans.py` kırılır — bu kasıtlıdır.

1. `modules/kadans.py` → `KADANS_DK`, `KADANS_CRON`
2. `.github/workflows/hourly_production.yml` → `cron:`
3. Dış dağıtıcı (cron-job.org) → interval

Diğer tüm yerler (SKILL.md, kural dosyası, bu doküman) bu sabitten **türetilir**;
sayı **kopyalanmaz** — kopyalanan sayı zamanla çürür.

---

## 7. Bilinen sınırlar

1. **Günde 6 yükleme** — kota sabiti. 15 dakikalık kadans bunu değiştirmez.
   Kota artırımı için YouTube API başvurusu gerekir.
2. **GitHub cron güvenilmez** — dış dağıtıcı kurulmadan kadans kâğıt üzerinde kalır.
3. **Render maliyeti** — no-op turlar kodun kota kapısına çarpıp `exit 0`
   yaptığı için ucuzdur, ama yine de bir runner açar (~30–60 sn).
4. **Kalite kapısı öndedir** — kaliteyi geçmeyen video sırf süre doldu diye
   yayımlanmaz; eksik üretim raporlanır.
