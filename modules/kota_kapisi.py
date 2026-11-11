"""BOBİ TV — Kota Kapısı (TODO 10).

- GÜNLÜK YÜKLEME TAVANI YOK (kullanıcı kararı 2026-11-11: "kotayı kaldır").
  Eskiden GUNLUK_MAKS=6 tavanı vardı ve bu modül kapı olarak kullanılıyordu;
  kapı workflow'dan ve pipeline'dan KALDIRILDI. Modül yalnızca YouTube API
  hatasını sınıflandıran YARDIMCI fonksiyonlar için duruyor.
- KOTA_DOLU_DAVRANIS:
    sessiz_dur (varsayılan) → exit 0 — C2'deki exit(1) self-repair fırtınasını
        (günde ~144 deneme + main'e otonom push) durdurur.
    hata → exit 1 — kırmızı tik (eski davranış, bilinçli seçimle).
- Kota birim bilgisi: yalnızca `bobi_tv/state/youtube_quota.json`'da kayıtlıysa
  gösterilir; yoksa 'bilinmiyor' denir — sayı UYDURULMAZ.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from modules.ayar_katalogu import VIDEO_INSERT_MALIYETI
from modules.telegram_notify import send_message

KOTA_STATE_YOLU = Path("bobi_tv/state/youtube_quota.json")
ARSIV_YOLU = Path("bobi_tv/archive/videos.json")


def kota_dolu_cikis_kodu(davranis: str | None) -> int:
    """Kota dolu durumunda koşunun çıkış kodu.

    sessiz_dur → 0 (varsayılan; self-repair tetiklenmez)
    hata → 1 (kırmızı tik)
    bilinmeyen değer → 0 + log uyarısı (botu düşürmemek için güvenli varsayılan)
    """
    dav = (davranis or "sessiz_dur").strip()
    if dav == "hata":
        return 1
    if dav != "sessiz_dur":
        print(f"::warning::Bilinmeyen KOTA_DOLU_DAVRANIS={davranis!r} — sessiz_dur uygulandı")
    return 0


def kota_kontrol_yap(
    hedef: int = 1,
    arsiv_yolu: Path = ARSIV_YOLU,
    kota_yolu: Path = KOTA_STATE_YOLU,
    simdi: datetime | None = None,
) -> dict[str, str]:
    """Workflow'un kota adımı hesabı (GITHUB_OUTPUT değerleri — tümü str).

    - Kota 'doldu' işareti 24 saat içindeyse geçerlidir (kota UTC 00:00 sıfırlanır).
    - devam: bugünkü üretim hedefi tutmadıysa true; kota doluysa false.
      (force bypass'ı workflow adım koşulunda `|| force == 'true'` ile yapılır.)
    """
    simdi = simdi or datetime.now(UTC)
    kota_doldu = False
    if kota_yolu.exists():
        try:
            state: Any = json.loads(kota_yolu.read_text(encoding="utf-8"))
            guncelleme = str(state.get("guncelleme", ""))
            if guncelleme and state.get("doldu"):
                guncel_zaman = datetime.fromisoformat(guncelleme.replace("Z", "+00:00"))
                gecen_saat = (simdi - guncel_zaman).total_seconds() / 3600
                if gecen_saat < 24:
                    kota_doldu = True
        except Exception:
            kota_doldu = False  # bozuk kota dosyası koşuyu bloklamaz
    bugun = simdi.strftime("%Y-%m-%d")
    bugunki = 0
    if arsiv_yolu.exists():
        try:
            kayitlar: Any = json.loads(arsiv_yolu.read_text(encoding="utf-8"))
            bugunki = sum(1 for k in kayitlar if str(k.get("tarih", ""))[:10] == bugun)
        except Exception:
            bugunki = 0
    kalan = max(0, hedef - bugunki)
    devam = "false" if kota_doldu else ("true" if kalan > 0 else "false")
    return {
        "bugunki": str(bugunki),
        "kalan": str(kalan),
        "kota_doldu": "true" if kota_doldu else "false",
        "devam": devam,
    }


def kota_dolu_bildir() -> None:
    """Kota dolu bildirimi (sessiz_dur'da da bilgilendirir — sessizlik exit koduna
    aittir, kullanıcıyı bilgisiz bırakmaya değil)."""
    send_message(
        "🚫 <b>YouTube kota dolu</b> — bu çalıştırmada üretim atlandı. Kota UTC 00:00'da sıfırlanır."
    )


def kota_durumu_ozeti(kota_yolu: Path = KOTA_STATE_YOLU) -> str:
    """Panel kota satırı: 'Kota: 4800/10000 birim · ~3 yükleme kaldı'.
    Dosya/birim kaydı yoksa 'bilinmiyor' — sayı UYDURULMAZ (TODO 10 test sözleşmesi)."""
    if not kota_yolu.exists():
        return "Kota: bilinmiyor (durum dosyası yok)"
    try:
        state: Any = json.loads(kota_yolu.read_text(encoding="utf-8"))
    except Exception:
        return "Kota: bilinmiyor (dosya okunamadı)"
    kalan_birim = state.get("kalan_birim")
    toplam_birim = state.get("toplam_birim")
    if not isinstance(kalan_birim, int) or not isinstance(toplam_birim, int) or toplam_birim <= 0:
        return "Kota: bilinmiyor (birim kaydı yok)"
    kullanilan = max(0, toplam_birim - kalan_birim)
    yukleme_kaldi = max(0, kalan_birim // VIDEO_INSERT_MALIYETI)
    return f"Kota: {kullanilan}/{toplam_birim} birim · ~{yukleme_kaldi} yükleme kaldı"
