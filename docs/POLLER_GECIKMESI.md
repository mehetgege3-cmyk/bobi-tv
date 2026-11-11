# Poller gecikmesi — tasarım notu (TODO 28)

Güncel: 2026-11-11 · Durum: **karar verildi, uygulandı (kısmi)**

## 1. Sorun

Telegram paneli bir GitHub Actions **poller**'ı ile çalışıyor
(`.github/workflows/telegram_bot.yml`, ~330 dk tek koşu, `getUpdates` döngüsü).

Gözlenen: poller susunca (runner kesintisi, kota/yeniden başlatma) kullanıcı
**cevap alamıyor**; poller geri geldiğinde biriken tüm `/start` ve buton
dokunuşları **art arda** işleniyor ve ekrana N panel düşüyor. Ayrıca Telegram
`getUpdates` kuyruğu **24 saatten** eski update'leri düşürür → mesaj kaybı.

Bu bir "panel yavaş" şikâyeti olarak görünür ama kökü **taşıma katmanıdır**,
panel kodu değil.

## 2. Neden webhook değil?

| Seçenek | Artı | Eksi | Karar |
|---|---|---|---|
| **Uzun poller (bugünkü)** | Sunucu gerekmez, secret'lar GH'de | Runner kesintisi = gecikme; 24 saat penceresi | ✅ kalır |
| **Webhook** | Anında yanıt | Genel internete açık HTTPS uç nokta + sertifika + 7/24 süreç ister | ❌ şimdilik hayır |
| **Hibrit** (webhook + yedek poller) | Anında + dayanıklı | İki kaynak → **çift teslim** riski | ⏸️ Faz 6 sonrası |

Webhook'a geçiş, 24/7 çalışan bir süreç (VPS/Cloud Run) demek: bu projede
barındırma maliyeti ve secret dağıtımı **yeni bir kırılma noktası** olurdu.
Bu yüzden poller korunuyor.

## 3. Uygulanan hafifletmeler (bugün)

1. **Panelde görünürlük** — ana ekranda `📡 Bot gecikmesi: … dk önce` satırı
   (GitHub Actions koşu zamanından). Kullanıcı "bot mu öldü, iş mi sürüyor?"
   sorusunu panelden cevaplar.
2. **Panel temizliği** — `🧹 Panelleri temizle` düğmesi biriken panelleri siler;
   tek panel (edit-in-place) felsefesi böylece geri kazanılır.
3. **Boşluk uyarısı** — uzun kesintiden sonra kaç update'in düştüğü bildirilir
   (`bosuk_uyarisi_gonder`) — sessiz mesaj kaybı yok.
4. **Tekilleştirme (TODO 29)** — aynı update tekrar teslim edilirse ikinci kez
   işlenmez; çift tetikleme (iki üretim) engellenir.
5. **Update başına iş kısıtlı** — bir turda işlenen update sayısı sınırlı
   (`POLLER_TUR_AZAMI`), böylece birikmiş kuyruk tek koşuyu kilitlemez.

## 4. Kabul edilen sınırlar (dürüstçe)

- En kötü durumda gecikme **poller'ın yeniden başlama süresi** kadardır
  (dakikalar ile saatler arası). Panel bunu **gösterir**, gizlemez.
- **24 saatten** eski update'ler geri getirilemez (Telegram kuralı).
- Üretim zinciri poller'dan **bağımsızdır**: panel susarsa video üretimi/yükleme
  durmaz (ayrı workflow: `hourly_production.yml`).

## 5. Faz 6 (Mini App) ile ilişki

Mini App'e geçilirse poller tamamen gereksizleşmez: Mini App de bir web
uygulamasıdır ve **barındırma** ister. Karar aynı: barındırma maliyeti kabul
edilmeden webhook/Mini App'e geçilmez. Bu not, TODO 31 (Mini App) için de
geçerlidir.

## 6. Ölçüm (nasıl anlarız düzeldi?)

- Panelde `📡 Bot gecikmesi` satırı **< 10 dk** ise sağlıklı.
- `Boşluk uyarısı` mesajı gelmiyorsa kesinti yaşanmamış demektir.
- Aynı düğmeye iki kez basıldığında **tek** panel düzenlemesi olur (TODO 29).
