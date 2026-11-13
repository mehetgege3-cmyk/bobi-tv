# GitHub Actions Geçmiş Temizliği (2026-11-13)

**Kullanıcı talebi:** *"Geçmiş action kısmını temizle"*

Actions sekmesinde 292 koşu birikmişti — %43'ü artık var olmayan
workflow'lara, %22'si başarısız/iptal koşulara aitti. Sekme okunamaz haldeydi.

---

## Ne silindi, ne kaldı

| Grup | Adet | Karar | Neden |
|---|---:|---|---|
| **Ölü workflow koşuları** | 125 | 🗑️ silindi | `workflow_id` artık repo'da yok — Arena çağı, tanımı silinmiş işler |
| **Başarısız / iptal** (canlı workflow) | 65 | 🗑️ silindi | Kırmızı X ve gri iptal gürültüsü; kök nedenleri `docs/OLU_KOD_TEMIZLIGI.md`'de yazılı |
| **Başarılı** (canlı workflow) | 101 | ✅ **korundu** | Üretim kanıtı: "bu video bu koşuda yayınlandı" zinciri |
| Devam eden | 2 | ✅ korundu | Hâlâ çalışıyor |

**Sonuç: 292 → 103 koşu.** Silinen 188, hata 2 (zaten silinmişti), korunan 101.

---

## Neden başarılılar silinmedi

Bir koşunun logu, bir videonun **neden** yayınlandığının tek kanıtıdır:

```
🚀 Yayınlandı: https://www.youtube.com/shorts/...
🖼️ Kapak: ..._kapak.jpg | kaynak: gemini_web | ilk kareye gömüldü: EVET
```

2026-11-13'te tam olarak bu log'a güvenip yanılmıştık — log "gömüldü: EVET"
diyordu ama YouTube'a kapaksız video gitmişti. Kanıtı tamamen silmek, aynı
hatayı bir daha teşhis edememek demek. Bu yüzden **başarılı koşular kalır**.

Kullanıcı isterse bu 101 de tek komutla silinebilir:

```bash
# TÜM geçmişi sil (geri alınamaz)
gh api --paginate repos/mehetgege3-cmyk/bobi-tv/actions/runs \
  --jq '.workflow_runs[].id' | xargs -I{} gh api -X DELETE repos/mehetgege3-cmyk/bobi-tv/actions/runs/{}
```

---

## Ne kaybedildi

| Kayıp | Etki |
|---|---|
| Ölü Arena koşularının logları | Yok — Arena çöpe atıldı, kod `arsiv/arena_olu_kod/`'da |
| Başarısız koşuların logları | Düşük — kök nedenler `OLU_KOD_TEMIZLIGI.md`'de yazılı |
| Artifact'lar (kapak JPG'leri) | Düşük — kanalların gerçek kapakları YouTube'da (`i.ytimg.com`) |
| Başarılı koşu logları | ❌ **KORUNDU** |

---

## Actions sekmesinde görünen eski isimler (normal)

Korunan 101 koşunun bir kısmı eski workflow adlarıyla görünür — bu **tarihsel
kayıttır**, bugünkü yapı değil:

- `BOBİ TV v6.4 PRO — Saatlik Üretim` (bugünkü adı: *Üretim (8 saatte bir)*)
- `Yorum Cevaplama — Arena AI` (bugünkü adı: *— Gemini*)
- `BOBİ TV v6.0/v6.2/v6.3 PRO` (eski sürümler)

Güncel liste: `docs/WORKFLOW_DIZINI.md`.

---

## Tekrar birikmesini önleme

GitHub, koşu geçmişini **90 gün** sonra kendisi temizler. Ek olarak:

- Artifact saklama süresi 7 gün (`if-no-files-found: ignore` + `retention-days`).
- Ölü workflow tanımı silinince eski koşuları da elle temizlemek gerekiyor —
  bu rapordaki işlem tekrarlanabilir.
