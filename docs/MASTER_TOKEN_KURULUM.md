# Master Token Kurulumu — Adım Adım

Bu belge tek işi yapar: **NotebookLM oturumunu kalıcı hale getirmek.**

---

## Önce: sorun ne?

Şu an sistemde `NOTEBOOK_GOOGLE` adlı bir **çerez kopyası** var. Çerezler
Google tarafından ~saatte bir döndürülüyor. Kopya eskiyince oturum ölüyor:

```
18:13  ✅ 22 defter göründü, video üretildi
18:32  ❌ AuthError: signed-out page   (19 dakika sonra, aynı çerez)
```

Master token bu sorunu kökten çözer: **şifre değişse bile geçerli** bir
anahtar. Google ondan çerezi her seferinde yeniden üretir.

---

## Yöntem A — Bilgisayarından (önerilen, tek komut)

Kendi bilgisayarında terminal aç. Sırayla:

### 1) Kütüphaneyi kur

```bash
pip install "notebooklm-py[headless,browser]"
```

### 2) Tek komutla kur

```bash
NOTEBOOK_EMAIL=hesap@gmail.com GH_PAT=ghp_xxxxx \
  python3 tools/master_token_kur.py
```

Ne olacak:

| Adım | Ne olur | Senin yapman gereken |
|---|---|---|
| 1/3 | Tarayıcı açılır, Google giriş sayfası gelir | **Not defterlerinin olduğu hesapla giriş yap** |
| 2/3 | `master_token.json` üretilir | hiçbir şey |
| 3/3 | Token doğrulanır (defter listesi okunur) + GitHub secret'a yazılır | hiçbir şey |

`GH_PAT` nedir: GitHub'a yazma izni olan kişisel anahtar. Sende zaten var
(`uploads/jeton/githubpat-2.json`). GH_PAT vermezsen secret'a yazmaz,
sadece dosyayı üretir — o zaman aşağıdaki Yöntem C'yi uygularsın.

### 3) Bitince

Actions → **Notebook Hattı** → Run workflow.

---

## Yöntem B — Elle, kütüphanenin kendi komutuyla

Betiği kullanmak istemezsen:

```bash
notebooklm login --master-token --account hesap@gmail.com
```

Tarayıcı açılır, giriş yaparsın. Sonra dosya burada oluşur:

```
~/.notebooklm/profiles/default/master_token.json
```

Bu dosyayı aç, **içindeki tüm metni** kopyala (tek satır JSON'dur).
Sonra GitHub'da:

```
Repo → Settings → Secrets and variables → Actions
→ New repository secret
→ Name : NOTEBOOKLM_MASTER_TOKEN_JSON
→ Secret: (kopyaladığın metin)
→ Add secret
```

---

## Yöntem C — Sunucuda tarayıcı yoksa (bu makine gibi)

Burada tarayıcı yok, giriş yapamam. İki seçenek:

**C1.** Yöntem A veya B'yi kendi bilgisayarında yap, üretilen dosyayı bana ver:

```bash
python3 tools/master_token_kur.py --eposta hesap@gmail.com --secret-yazma
# dosya yolu ekrana yazılır → içeriğini bana ilet
```

**C2.** GitHub Actions'ın kendi secrets sayfasından ekle (Yöntem B'nin sonu).
En güvenlisi bu — token değeri hiçbir yere yapıştırılmaz.

---

## Kurulumdan sonra ne değişir?

| | Şimdi (çerez) | Master token sonrası |
|---|---|---|
| Ömür | ~1 saat | ♾️ kalıcı |
| Şifre değişirse | ölür | çalışmaya devam eder |
| Otomatik hat | ❌ mümkün değil | ✅ mümkün |
| Her koşuda tazeleme | gerekli, işe yaramıyor | kendiliğinden |

---

## Sık sorulanlar

**Token değeri sohbete yazılacak mı?**
Hayır. Betik değeri hiçbir zaman ekrana basmaz, sadece uzunluğunu söyler.
GitHub secret'a şifreli (libsodium sealed box) yazılır.

**Hesap doğru mu?**
Defterler hangi hesapta duruyorsa o hesap. Şu an 22 defter görünüyor;
kurulumdan sonra aynı sayıyı görmelisin. Görmezsen yanlış hesaba girmişsindir.

**`notebooklm: command not found` derse?**
`pip install notebooklm-py` çalışmamış. `pip install --user notebooklm-py`
veya `python3 -m notebooklm login ...` dene.

**Tarayıcı açılmıyor (uzak sunucu)?**
`--browser-cookies chrome` ile kurulu Chrome'un çerezlerini okuyabilirsin:
`notebooklm login --browser-cookies chrome --account hesap@gmail.com`

**Master token güvenli mi?**
Tam hesap erişimi verir — şifre gibi sakla. Mümkünse ayrı/atıl bir Google
hesabı kullan. Sızarsa Google hesabı ayarlarından oturumları kapat.
