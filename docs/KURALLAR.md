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
