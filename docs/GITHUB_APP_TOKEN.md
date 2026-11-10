# GitHub App Token — Otomatik Secret Yazma İçin Doğru Yöntem

Bölüm 3, Seçenek B referans dokümanı. Şu anda (Seçenek A uygulandı) otomatik
çerez yenileme KALDIRILDI; cookie elle yenilenir. Gelecekte otomatik yenileme
geri getirilmek istenirse, `GH_PAT` (Personal Access Token) yerine **GitHub
App installation token** kullanılmalıdır.

## Neden PAT yerine GitHub App?

- PAT tek bir kullanıcıya aittir, süresi dolabilir veya kullanıcı ayrılırsa
  erişim düşer. Ayrıca repo kapsamı dışında geniş yetki taşır.
- GitHub App, repo düzeyinde minimal yetkiyle 1 saatlik kısa ömürlü token
  üretir; `actions/create-github-app-token@v2` ile Actions içinde doğrudan
  kullanılabilir. Private key bir secret olarak saklanır, token asla
  kalıcı olmaz.

## Kurulum adımları

1. **GitHub App oluştur**: `github.com/settings/apps` (ve kuruluş) → New
   GitHub App. Webhook devre dışı bırakılabilir.
   **İzinler (Repository permissions):**
   - `Actions: Read` (çalıştırma loglarına erişim)
   - `Contents: Read and write` (tamir commit'i push'u)
   - `Secrets: Read and write` (çerez secret'ını güncellemek için — sadece
     o özellik aktifse)
2. **Private key** oluştur → `.pem` indir.
3. **Repo'ya kur**: App'i hedef repo'ya install et; `installation_id` al.
4. **Repo secret'ları** ekle:
   - `APP_ID` — App numarası
   - `APP_PRIVATE_KEY` — .pem içeriği (tüm satırlar, `-----BEGIN...` dahil)
   - `APP_INSTALLATION_ID` — kurulum numarası
5. **Workflow'de kullan**:
   ```yaml
   - name: 1 saatlik installation token al
     id: app_token
     uses: actions/create-github-app-token@v2
     with:
       app-id: ${{ secrets.APP_ID }}
       private-key: ${{ secrets.APP_PRIVATE_KEY }}
       installation-retention: 3600
   - name: Secret'ı güncelle
     env:
       GH_TOKEN: ${{ steps.app_token.outputs.token }}
     run: gh secret set ARENA_COOKIES_JSON --repo "$GITHUB_REPOSITORY" < /tmp/cookies.json
   ```

## Sık hatalar

- **Private key tek satır**: secret'a yapıştırırken yeni satırlar korunmalı;
  `-----BEGIN RSA PRIVATE KEY-----` ve `-----END...` dahil tüm blok.
- **App repo'ya kurulu değil**: `installation-retention` hatası veya 404.
  App'in kurulu olduğundan ve repo'nun erişim listesinde olduğundan emin ol.
- **Yetersiz izin**: `gh secret set` 403 verirse App'in `Secrets: write`
  izni yok demektir.
- **Token süresi**: installation token 1 saatten fazla yaşamaz; uzun işlerde
  işin başında al ve aynı job içinde kullan.
- **PAT ile karşılaştırma**: PAT `repo` + `workflow` geniş kapsamlıdır,
  sızıntı riski yüksektir. GitHub App minimal kapsam + kısa ömürlüdür.

## Şu anki durum

Otomatik yenileme kapalı (Bölüm 3-A). Bu doküman, ileride Seçenek B
(doğru formatta cookie + GitHub App token) veya Seçenek C (yarı-otomatik
Telegram uyarısı + elle onay) uygulanırsa referans olsun diye yazıldı.
Bkz. `docs/TODO_ajana.md`.
