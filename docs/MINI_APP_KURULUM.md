# Mini App'i Telegram'a bağlama (5 dakika, tek sefer)

Bu adımlar **bir kez** yapılır. Sonrasında Mini App hem bot menüsünden hem
`/mini` ekranındaki **📱 Mini App'i aç** düğmesinden açılır.

## 1. Doğru URL (kopyala)

```
https://mehetgege3-cmyk.github.io/bobi-tv/
```

> Sondaki `/` önemli değil ama **https** olmak zorunda. Bu adres GitHub Pages'te
> canlı ve yalnız `webapp/` klasörünü yayınlıyor.

## 2. BotFather'da nereye girilecek

Ekran görüntüsündeki sayfa: **Bot Settings → Mini Apps**.
Sırayla:

1. **☰ Menu Button** → dokun
2. Açılan alanda **URL** satırına yukarıdaki adresi yaz
3. **Button text** (düğme yazısı) → `BOBİ TV` veya `Mini App`
4. Kaydet

Bundan sonra botun sohbetinde **sol altta mavi "BOBİ TV" düğmesi** görünür ve
Mini App'i açar.

### "Main App" ne zaman gerekli?

`Main App` **zorunlu değil**. Yalnız `t.me/<bot>/<app_kisa_ad>` biçiminde özel
kısa link üretmek için kullanılır (`/newapp` komutuyla uygulama tanımlanır).
v1 için gerekmiyor — Menu Button yeterli. İstersen sonra `Main App` →
`<adres>` ile aynı URL verilebilir.

### "Create Direct Link" (Direct Links)

Sohbete atılabilen `t.me/<bot>/<app>?startapp=...` linki üretir.
**v1 için gerekmiyor**; Mini App'i paylaşmak istersen kullan.

## 3. Same-Origin Restriction

Ekranda **açık** (mavi) duruyor ve "25 Temmuz 2026'da otomatik açılacak" diyor.
Bu bir güvenlik **artısıdır**: yalnız senin origin'in (`github.io`) WebApp
SDK'sını çağırabilir ve kullanıcı verisini okuyabilir.
**Açık bırak** — bizim sayfamız kendi origin'inden yükleniyor, etkilenmez.

## 4. Yazma düğmeleri çalışmıyorsa

| Belirti | Sebep | Çözüm |
|---|---|---|
| Düğmeler gri/soluk, "çalışmaz" yazısı | Sayfa düz tarayıcıda açıldı | Mini App'i **Telegram içinden** aç (Menu Button) |
| "İstek gönderilemedi" | `sendData` yok (eski Telegram sürümü) | Telegram'ı güncelle **veya** panelden `🎬 Üret` kullan |
| İstek gitti ama cevap yok | Poller yavaş (5.5 saatlik döngü) | Panelde `📡 Bot gecikmesi` satırına bak; 1-2 dk sonra tekrar dene |
| Sayfa eski içerik gösteriyor | Pages gecikmesi | `🔄` / sayfayı yenile; veri 15 dk'da bir tazelenir |

> **Önemli:** Mini App yazmayı **kendisi yapmaz**. İstek bota gider, bot **onay
> ekranı** açar; onaylamadan üretim başlamaz. Onaydan sonra işlem denetim
> kaydına (`📋 Denetim`) yazılır.

## 5. Kontrol listesi

- [ ] Menu Button URL'si `https://mehetgege3-cmyk.github.io/bobi-tv/`
- [ ] Button text: `BOBİ TV`
- [ ] Same-Origin Restriction: açık (dokunma)
- [ ] Telegram'da mavi düğme göründü, sayfa açılıyor
- [ ] Panelde `/mini` → **📱 Mini App'i aç** da çalışıyor
- [ ] Bir yazma düğmesine bas → botta **onay ekranı** çıkıyor
