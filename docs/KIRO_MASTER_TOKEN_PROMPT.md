# Kiro için Master Token Promptu

Aşağıdaki bloğu **olduğu gibi** kopyalayıp Kiro'ya ver. `HESAP@gmail.com` yerine
NotebookLM defterlerinin bulunduğu hesabı yaz.

---

```
GÖREV: NotebookLM için kalıcı bir master token üret ve dosyayı teslim et.

ÇIKTI: ~/.notebooklm/profiles/default/master_token.json
        (mode 0600, JSON, içinde "aas_et/..." ile başlayan master token)

HESAP: HESAP@gmail.com
Bu hesapta 23 NotebookLM defteri var. Doğrulama: aynı sayıyı görmelisin.

=== DAHA ÖNCE DENENDİ VE BAŞARISIZ OLDU — TEKRARLAMA ===
1. `notebooklm login --master-token` (tarayıcı otomatik yakalama)
   → EmbeddedSetup akışında oauth_token cookie'si gelmiyor, Google bloke ediyor.
2. `notebooklm login --browser-cookies chrome --account ...`
   → token yakalanmıyor.
3. `notebooklm login --cdp-url http://localhost:9222`
   → Chrome remote debugging policy tarafından engelli.
4. `gpsoauth.perform_master_login(email, gerçek şifre, android_id)`
   → BadAuthentication.
5. Aynı komut uygulama şifresiyle ("gcbr vyuq nlqr vszn" formatı)
   → BadAuthentication. Uygulama şifresi bu akışta KULLANILMAZ (sadece SMTP/IMAP).
6. ADB + root ile telefon çerezi → telefon root'lu değil.

Bu altı yolu tekrar denemeyin. Aşağıdaki A veya B yolunu deneyin.

=== YOL A — oauth_token'ı ELLE yakala, --oauth-token ile ver ===

Kütüphane belgesi (data/SKILL.md) diyor ki:
  "the browser oauth_token capture also needs [browser] — or skip it by
   passing --oauth-token"

Yani tarayıcı yakalamasını atlayıp token'ı elle verebiliriz. oauth_token,
EmbeddedSetup akışında oluşan TEK KULLANIMLIK bir değerdir.

Adımlar:
1. pip install "notebooklm-py[headless,browser]"
2. Chrome'da yeni bir gizli pencere aç (mevcut profili kullanma).
3. https://accounts.google.com/EmbeddedSetup adresine git.
   HESAP@gmail.com ile giriş yap. "Devam" ekranlarını sonuna kadar geç.
4. DevTools aç (F12) → Application (Uygulama) → Storage → Cookies
   → https://accounts.google.com
   Liste içinde `oauth_token` adlı çerezi bul. Değerini kopyala.
   (Yoksa: Network sekmesi, "Preserve log" işaretle, sayfayı yenile,
    isteklerde `oauth_token` geçen yanıt başlığına bak.)
5. Şu komutu çalıştır:
     notebooklm login --master-token --account HESAP@gmail.com \
       --oauth-token "BURAYA_OAUTH_TOKEN"
6. Başarılıysa 3. adımdaki doğrulamayı yap.

Not: `--force` gerekebilir (profil başka hesaba bağlıysa).
Not: `--android-id` sabittir; ilk çalıştırmada üretilip saklanır.
     Aynı değeri tekrar kullan, yoksa perform_oauth reddeder.

=== YOL B — tarayıcı profiline zaten düşmüş token'ı bul ===

Master token bazen ~/.notebooklm/ altında kalmış olur:
1. Şunları ara ve varsa içeriğini kontrol et (değeri EKRANA BASMA):
     ~/.notebooklm/master_token.json
     ~/.notebooklm/profiles/*/master_token.json
     ~/.config/notebooklm/**
2. Varsa ve içinde "aas_et/" geçiyorsa iş bitmiştir — dosya yolunu bildir.

=== DOĞRULAMA (zorunlu) ===
Şunları çalıştır ve çıktısını bildir:

  notebooklm auth refresh --verify
      → "ok verified" görmelisin

  notebooklm list
      → 23 defter listelenmeli

İkisi de geçmezse master token İŞE YARAMIYOR demektir; öyle söyle.

=== RAPOR FORMATI (bana döneceğin cevap) ===
1. Dosya yolu: <tam yol>
2. Dosya boyutu ve izinleri (0600 mü)
3. Token'ın İLK 6 ve SON 6 karakteri (tam değeri ASLA yazma)
4. `notebooklm auth refresh --verify` çıktısı
5. `notebooklm list` defter sayısı
6. Başarısızsa: hangi adımda, tam hata metni

=== GÜVENLİK KURALLARI ===
- Master token değerini sohbete/log'a YAZMA. Sadece ilk 6 + son 6 karakter.
- Dosyayı 0600 yap.
- Repo PUBLIC — token'ı repoya, commit'e, .env'e KOYMA.
- Token değeri bana lazım; ben GitHub secret'ına kendim yazacağım.
```

---

## Neden bu iki yol?

Kütüphanenin kendi belgesi (`data/SKILL.md`) master token'ı şöyle tarif ediyor:

> "oauth_token (single-use, from one EmbeddedSetup browser sign-in)
> → exchange_token → aas_et/ master token (durable; persisted 0600)
> → perform_oauth → ya29 OAuthLogin token → MergeSession → SID/SAPISID/..."

Yani **tek kritik parça `oauth_token`**. Kiro'nun 1. denemesi bunu tarayıcıdan
otomatik yakalamaya çalışıp başarısız oldu; YOL A aynı değeri **elle** alıp
komuta veriyor. Kaybedilen halka bu.

## Başarısız olursa

Master token gerçekten kapanmışsa zorlamayalım. Yedek plan hazır:
`storage_state.json` + 15 dakikalık tazeleme job'u (`tools/notebook_cerez_tazele.py`
zaten yazılı). O yol **kanıtlanmış** — bugün 19:37'de video üretti.
