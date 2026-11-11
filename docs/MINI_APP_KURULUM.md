# Mini App'i Telegram'a bağlama (5 dakika, tek sefer)

## ⚠️ Önce en önemli kural

Mini App **sohbete atılan düz linkle AÇILMAZ**. Telegram sohbetinde bir
`https://…` linkine dokununca **kendi tarayıcısını** açar; orada Mini App
API'si (`sendData`, `initData`) **hiç yoktur**. Bu yüzden "Bu ekrandan işlem
gönderilemez — sayfa Telegram dışında açıldı" mesajını görürsün.

Doğru kapı **iki tanedir** ve ikisi de sohbetin İÇİNDE açılır:

| Kapı | Nasıl | Not |
|---|---|---|
| **Menü düğmesi** (asıl) | BotFather → Bot Settings → **Menu Button** → URL | Sohbetin sol altında mavi düğme |
| **Panel düğmesi** | Botta `/help` → **📱 Mini App** | `web_app` düğmesi; tek dokunuş |

## 1. Doğru URL (kopyala)

```
https://mehetgege3-cmyk.github.io/bobi-tv/
```

> **https** olmak zorunda; GitHub Pages'te canlı ve yalnız `webapp/` klasörünü
> yayınlıyor.

## 2. BotFather'da nereye girilecek

Sayfa: **Bot Settings → Mini Apps** → **☰ Menu Button**

1. **☰ Menu Button** → dokun
2. **URL**: yukarıdaki adres
3. **Button text**: `BOBİ TV`
4. Kaydet

Sonra bot sohbetinin **sol altında mavi "BOBİ TV" düğmesi** görünür.

### Main App / Direct Link gerekli mi?
**Hayır.**
- `Main App`: yalnız `t.me/<bot>/<app_adı>` kısa linki içindir.
- `Create Direct Link`: sohbete atılabilen `?startapp=` linki içindir; düz link
  gibi tarayıcıya düşmez ama **v1 için gereksiz**.

### Same-Origin Restriction
Ekranda **açık** ve "25 Temmuz 2026'da otomatik açılacak" diyor. Bu bir
güvenlik **artısıdır** (yalnız senin origin'in WebApp SDK'sını çağırabilir).
**Açık bırak** — sayfamız kendi origin'inden yükleniyor, etkilenmez.

## 3. Doğru test (30 saniye)

1. Telegram'da **botu** aç (kanal değil)
2. **Sol alt mavi MENÜ düğmesi** → Mini App açılır
3. Bir işlem düğmesine bas → **botta onay ekranı** çıkmalı
4. Onayla → işlem çalışır, `📋 Denetim` kaydına düşer

## 4. Sorun giderme

| Belirti | Sebep | Çözüm |
|---|---|---|
| "sayfa Telegram dışında açıldı" + `tg=yok` | Düz link tarayıcıda açıldı | Sayfayı Telegram **içinden** aç (Menü düğmesi / `/help` → 📱) |
| `initData=boş` | Oturum tanınmadı (yan/menü düğmesi değil) | Menü düğmesinden gir; Telegram'ı güncelle |
| `sendData=yok` | Eski Telegram sürümü | Güncelle **veya** panelden yap |
| Düğmeler gri, üstte sarı bant | Tarayıcı tespiti (bilinçli) | Telegram içinden aç |
| İstek gitti, cevap yok | Poller gecikmesi (5.5 saatlik döngü) | Panelde `📡 Bot gecikmesi` satırına bak, 1-2 dk sonra tekrar |
| Sayfa eski içerik | Pages gecikmesi | Sayfayı yenile (veri 15 dk'da tazelenir) |

> **Güvenlik:** Mini App hiçbir şeyi doğrudan çalıştırmaz. İstek bota gider,
> bot **onay ekranı** açar; onaylamadan üretim başlamaz. Token tarayıcıya
> **hiç çıkmaz** (payload yalnız `{"e": <eylem>, "v": 1}`).

## 5. Kontrol listesi

- [ ] Menu Button URL: `https://mehetgege3-cmyk.github.io/bobi-tv/`
- [ ] Button text: `BOBİ TV`
- [ ] Same-Origin Restriction: açık (dokunma)
- [ ] Sohbette mavi düğme göründü, sayfa **Telegram içinde** açılıyor
- [ ] `/help` → **📱 Mini App** düğmesi de açıyor
- [ ] Yazma düğmesi → botta **onay ekranı** → onay → `📋 Denetim`de kayıt
