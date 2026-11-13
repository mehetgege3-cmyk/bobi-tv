# ÇALIŞMA KURALLARI (kalıcı — her turda uygulanır)

Bu dosya, kullanıcının verdiği **kalıcı talimatları** tutar. Yeni bir kural
geldiğinde buraya eklenir; hiçbir kural kullanıcı geri almadıkça silinmez.

---

## K1 — HER ZAMAN İNTERNET ARAŞTIRMASI + EN GÜNCEL DOKÜMAN (2026-11-13)

> "Kanka internette her zaman araştırma yap. En güncel dökümantasyonları oku,
> bunu unutma, hafızana kaydet."

**Uygulama:**
- Bir API/servis/kütüphane ile çalışmadan **önce** resmî dokümanı **oku**.
- Model adı, uç nokta, parametre, kota **ezberden yazılmaz** — doğrulanır.
- Doküman değişmiş olabilir: **legacy/deprecated** uyarılarını ara.
- Kaynak sırası: resmî doküman (ai.google.dev, aistudio.google.com, GitHub
  resmî repo) → Stack Overflow → topluluk.
- Bulunan güncel bilgi **anında** `docs/` altına yazılır (K2).

**Neden bu kural var (kanıt):** 2026-11-13'te `gemini-2.5-flash` modelinin
**yeni kullanıcılara kapandığı** (API: "no longer available to new users,
use gemini-3.8-flash"), görsel üretim dokümanının **Interactions API**'ye
taşındığı ve `gemini-2.5-flash-image`'ın artık **legacy** sayıldığı
yalnızca doküman okunarak öğrenildi. Ezberdeki bilgi yanlıştı.

## K2 — HER KOMUTTAN SONRA ÖĞRENİLENİ ANINDA YAZ (2026-11-13)

Her komut/denemeden sonra öğrenilen her detay **o anda** `docs/` (+ gerekiyorsa
`SKILL.md`) içine yazılır ve commit edilir. Tur sonuna bırakılmaz.

## K3 — HER KOMUTTAN ÖNCE TÜRKÇE AÇIKLAMA

Komuttan önce: **ne yapıyorum / niçin / nasıl**. Sonra: sonuç + kanıt.

## K4 — ARAŞTIRMA YOĞUN HATA PROTOKOLÜ

Her hatada: kök neden + 5 farklı uzman bakışı + internet/forum araştırması +
kesin çözüm. Çalışan kod kanıtsız bozulmaz.

## K5 — DÜRÜSTLÜK

Çalışmayan özellik "çalışıyor" denmez. Yapılamayan iş: `YAPILMADI: <sebep>`.
Her iddia **gerçek dosya / log / DOM** ile kanıtlanır.

## K6 — KOTA/ANAHTAR GERÇEĞİ

API anahtarı **sohbete yazılmaz**; GitHub Secrets'a yazılır. Anahtar "geçerli"
demek "kota var" demek **değildir** — ikisi ayrı ayrı ölçülür.

## K7 — WORKSPACE BÜTÇESİ: 128 MB / 10.000 DOSYA (2026-11-13, kullanıcı: "bir daha yapma")

**Olay:** Kanıt için GitHub artifact'larından videolar indirildi
(27 MB + 22 MB + 20 MB + 17 MB = **86 MB**). Workspace **179 MB / 2.786 dosya**
oldu, platform "Workspace over budget" verdi ve **33 dosya kaydedilmedi**.

**KURAL — pazarlıksız:**
1. **Video asla workspace'e indirilmez** (`*.mp4`, `*.mov`, `*.mkv`, `*.webm`).
   Video zaten YouTube'da yayında → **link yeterli kanıttır**.
2. İnceleme gerekiyorsa `/tmp`'ye indir (kalıcı değil), iş bitince sil.
3. Kanıt olarak yalnız **küçük** dosyalar: kapak JPG/PNG (≤1 MB), log, JSON.
4. Artifact zip'inden **sadece gereken dosyayı** çıkar (`unzip "*.jpg"`),
   tüm arşivi açma.
5. HAR/PCAP gibi ağ dökümleri: hem büyük hem **token sızdırır** → workspace'e
   konmaz. (Bu olayda `har/arena.md` 7,9 MB ve içinde gerçek JWT + ya29
   token'ları vardı; silindi.)
6. Her büyük indirme öncesi/sonrası: `python3 tools/disk_bekci.py`

**Otomatik koruma:**
- `tools/disk_bekci.py` — bütçe + yasak uzantı kontrolü (çıkış 1 = ihlal)
- `.gitignore` — `*.mp4`, `*.mov`, `*.mkv`, `*.webm`, `*.avi`, `*.har`, `har/`

**Ders:** "Kanıt" demek "dosyayı sakla" demek değil. Link + küçük görsel +
log satırı kanıt için yeterli; 27 MB'lık video değil.

## K9 — TEK SAĞLAYICI: GEMINI WEB ÇEREZİ (2026-11-13)

> Kullanıcı: *"Bu sorunsuz çalışıyor. Arena AI'yi ve Gemini API'yi çöpe at.
> Artık bunu kullanalım, Gemini cookie işimize yarar."*

**ÇÖPE ATILANLAR:**

| Atılan | Neden |
|---|---|
| **Arena AI** (kapak + senaryo + yorum) | Çerez sürekli 401; tarayıcı duvarı; güvenilmez |
| **Gemini API** (`GEMINI_API_KEY`) | Görsel kotası `limit: 0` (ücretsiz katmanda yok) |

**KALAN TEK YOL: `GEMINI_COOKIES` (gemini.google.com oturum çerezi)**

| İş | Fonksiyon | Durum |
|---|---|---|
| Kapak görseli | `gemini_web.gorsel_uret` | ✅ koşu 43378192358 |
| Senaryo / ilginç bilgi | `gemini_web.metin_uret` | ✅ canlı test (hidra kartı) |
| Yorum cevabı | `gemini_web.metin_uret` | ✅ test yeşil |

**Kapak hattı:** Gemini WEB → (başarısızsa) video karesi. Üretim **durmaz**.

**Çerez ömrü:** `__Secure-1PSIDTS` kısa ömürlü. Öldüğünde:
`tools/gemini_cerez_kur.py --dosya <export.json>` → doğrular + secret'a yazar.

**Ders:** API anahtarı "geçerli" olması kota olduğu anlamına gelmez. Web çerezi
abonelik kotasını kullanır — bu yüzden API'den daha çok iş görüyor.
