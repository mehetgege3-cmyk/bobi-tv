# Tam Yetkili Ajan Promptu — BOBİ TV Otonom Üretim Sistemi

Bu repo üzerinde çalışan her ajan (insan veya LLM) için bağlayıcı kurallar.
İhlal iş başarısız sayılır.

## Amaç

Otonom, etik, Türkçe YouTube Shorts (komedi) üretimi; kalite kapısından
geçmiş senaryo → TTS → render → kapak → yükleme → arşiv zinciri. Kota ve
günlük hedef aşılmaz.

## Mutlak kurallar (ihlali = geri alma)

1. **Gizlilik mutlak:** `GH_PAT`, `ARENA_COOKIES_JSON`, `YOUTUBE_TOKEN`,
   `YOUTUBE_CLIENT_SECRET`, `TELEGRAM_BOT_TOKEN`, çerez değerleri ASLA
   ekrana basılmaz, log'a yazılmaz, commit'e dahil edilmez, dokümana
   geçmez. Raporlarda yalnız ad + uzunluk. `git remote -v` bile
   çalıştırılmaz (origin URL'sinde token gömülü).
2. **Veri bütünlüğü:** `videos.json` arşivi elle silinmez; kayıtlar
   `durum` alanıyla işaretlenir (`yayinda` / `kaldirildi`). Kota/kuyruk/
   hata durumu `videos.json`'a YAZILMAZ — `bobi_tv/state/` altına.
3. **Etik:** Irk, ten rengi, etnik köken, cinsiyet, din, engel veya başka
   korunan kimliği hedef alan aşağılayıcı içerik ÜRETİLMEZ. Karakterler
   eşit ve saygılı yazılır. Alkol/uyuşturucu özendirilmez.
4. **Testler silinmez / skip'lenmez.** Mevcut test sayısı (103 passed,
   1 skipped) ALTINA DÜŞMEZ; yeni özelliklerle test sayısı ARTAR.
   Zayıf assert (örn. `assert True`, sadece varlık kontrolü) KABUL
   EDİLMEZ. `pytest.mark.integration` işaretli gerçek render testleri
   normal koşuda skip kalabilir.
5. **Tek konulu commit.** Her commit bir iş maddesi; mesaj Türkçe,
   `fix(alan):`, `feat(alan):`, `ci(alan):`, `refactor(alan):`,
   `docs:`, `test:` önekli. Yapılamayan adım varsa commit mesajına
   `YAPILMADI: <sebep>` yaz ve devam et — sessizce atlama.
6. **Force push YOK.** `rm -rf` YOK. Push öncesi `git fetch origin` +
   taban kontrolü; uzak main hareket etmişse rebase/cherry-pick.
   Conflict dürüstçe raporlanır.
7. **Her commit öncesi `python3 -m pytest -q` YEŞİL olmalı.** Sayı not
   edilir. Python dosyası değiştiyse `python3 -m py_compile` de geçmeli.
8. **Arena ToS duvarı:** `ACCEPT_TOS=1` yoksa Agree'ye BASILMAZ; net hata
   + ekran görüntüsü. Otomatik çerez yenileme KAPALIDIR (Bölüm 3-A);
   cookie elle yenilenir.

## Tek kaynaklar (değiştirirsen her iki tarafı da güncelle)

- Arena seçiciler: `skills/arena-playwright-agent/scripts/arena-dom.mjs` ↔
  `modules/arena_api.py` `ARENA_*` sabitleri. Ayrışma testi kırar.
- Silme eşiği: tek env kaynağı (bkz. `docs/OTOMASYON_TESHIS_2026-11-10.md`).
- Cadans: `hourly_production.yml` cron + kota kapısı (SKILL.md'de cron
  güvenilir değil notu).

## Kabul kriterleri

- `pytest -q` yeşil, sayı önceki ≥.
- `ruff check` + `ruff format --check` (ilgili dosyalar) geçer.
- `mypy --strict` (ilgili dosyalar) geçer.
- `pyflakes` temiz (kullanılmayan import, tanımsız ad yok).
- Workflow YAML'leri parse olur; self-repair izleme listesi tam.
