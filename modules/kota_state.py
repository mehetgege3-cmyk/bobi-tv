"""
YouTube Kota Durum Takibi
- Günlük kota durumunu state dosyasına yazar
- Kota dolduğunda workflow'un düzgün hata vermesini sağlar
"""
import json
from datetime import datetime, timezone
from pathlib import Path


KOTA_STATE_YOLU = Path("bobi_tv/state/youtube_quota.json")


def kota_state_yaz(doldu: bool, kalan_saat: int = 0, video_sayisi: int = 0) -> None:
    """
    Kota durumunu state dosyasına yaz.

    Args:
        doldu: Kota doldu mu?
        kalan_saat: Kotanın açılmasına kalan saat (yaklaşık)
        video_sayisi: Bugün yüklenen video sayısı
    """
    KOTA_STATE_YOLU.parent.mkdir(parents=True, exist_ok=True)

    state = {
        "doldu": doldu,
        "kalan_saat": kalan_saat,
        "video_sayisi": video_sayisi,
        "guncelleme": datetime.now(timezone.utc).isoformat(),
    }

    KOTA_STATE_YOLU.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def kota_state_oku() -> dict:
    """
    Kota durumunu oku.

    Returns:
        State dict veya boş dict
    """
    if not KOTA_STATE_YOLU.exists():
        return {"doldu": False, "kalan_saat": 0, "video_sayisi": 0}

    try:
        return json.loads(KOTA_STATE_YOLU.read_text(encoding="utf-8"))
    except Exception:
        return {"doldu": False, "kalan_saat": 0, "video_sayisi": 0}


def kota_dolu_mu() -> bool:
    """Kota dolu mu kontrol et."""
    state = kota_state_oku()

    if not state.get("doldu"):
        return False

    # Kota dolu ama 24 saat geçtiyse sıfırla
    guncelleme = state.get("guncelleme", "")
    if guncelleme:
        try:
            guncel_zaman = datetime.fromisoformat(guncelleme.replace("Z", "+00:00"))
            gecen_saat = (datetime.now(timezone.utc) - guncel_zaman).total_seconds() / 3600

            if gecen_saat >= 24:
                # 24 saat geçti, kota sıfırlanmış olmalı
                kota_state_yaz(doldu=False, kalan_saat=0, video_sayisi=0)
                return False
        except Exception:
            pass

    return True


if __name__ == "__main__":
    # Test
    print(f"Kota durumu: {'DOLU' if kota_dolu_mu() else 'BOŞ'}")
    print(f"State: {kota_state_oku()}")
