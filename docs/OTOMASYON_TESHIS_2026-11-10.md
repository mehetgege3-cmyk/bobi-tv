# Otomasyon Neden Durdu — Teşhis (2026-11-10)

Soru: "Her 15 dakikada bir video üretecekti, neden olmadı?" Aşağıdaki bulgular
çalıştırma geçmişi ve kod incelemesiyle doğrulandı.

## 1. GitHub cron güvenilir DEĞİLDİR

`*/15 * * * *` (her 15 dk) ayarlanmasına rağmen, incelenen 18 koşunun **16'sı
manuel** tetiklemeydi; zamanlanmış koşular fiilen günde yalnızca 1-2 kez
çalıştı. GitHub Actions scheduler yüksek yüklü dönemlerde kuyruğa alır ve
atlar — garantili bir zamanlayıcı DEĞİLDİR. Bu, SKILL.md'de artık açıkça
belirtilir; "her 15 dakikada bir video" vaadi YANLIŞTIR.

## 2. Kota dolunca kuyruk → arşiv → sayaç zinciri koptu

YouTube Data API kotası dolunca video yüklenemiyor. Eski akış:
üret → yükleme başarısız → kuyrukta bekle → arşive yazılmadı → `videos.json`
sayacı artmadı → "günlük hedef dolmadı" → kapı açık → sonraki koşu yine
üretmeye çalıştı ama yine kota → **exit 0 yeşil (no-op)**. Dışarıdan bakınca
"her şey yeşil" ama hiç video çıkmıyordu.

**Kural (artık uygulandı):** `videos.json`'a kota/kuyruk/hata durumu
YAZILMAZ. Orada yalnızca geçerli `video_id` ile yayın kaydı bulunur. Kota
durumu ayrı dosyada: `bobi_tv/state/youtube_quota.json`.

## 3. Kuyruk dizini .gitignore'daydı

`bobi_tv/queue/` dizini `.gitignore`'daydı; Actions her koşuda temiz
checkout yaptığı için kuyruk her seferinde sıfırlanıyordu. Düzeltildi: kuyruk
artık izleniyor (veya kalıcı artifact olarak saklanıyor).

## 4. `git reset --hard HEAD` çalışma ağacını siliyordu

Bazı onarım adımlarında `git reset --hard HEAD` çalıştırılıyor, bu da
üretilmiş ama henüz commit'lenmemiş dosyaları (kuyruk, durum) siliyordu.
Kaldırıldı; yerine `git checkout -- <bilinen-dosyalar>` veya temiz checkout
kullanılır.

## Özet düzeltmeler

| Belirti | Kök neden | Düzeltme |
|---------|-----------|----------|
| 15dk cron çalışmıyor | GitHub scheduler güvenilir değil | SKILL.md notu; kota kapısı korunur |
| Yeşil ama video yok | Kota → kuyruk → sayaç no-op | videos.json'a sadece video_id yaz; kota ayrı state dosyası |
| Kuyruk her koşuda sıfır | queue/ .gitignore'da | queue/ izlenir/kalıcı |
| Durum dosyaları kayboluyor | git reset --hard | Kaldırıldı |

## Sonraki adımlar

- `docs/TODO_ajana.md`: canlı cookie ile Arena doğrulaması, çerez yenileme
  Seçenek B/C.
- Kota kapısı davranışı kodda teyit edildi (dokunulmadı): kota dolunca koşu
  atlanır, exit 0 — bu istenen davranıştır, cron ne sıklıkla çalışırsa
  çalışsın günlük kota aşılmaz.
