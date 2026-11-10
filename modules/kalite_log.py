"""
Kalite Raporu Loglama Modülü
- Üretilen her senaryonun kalite puanını loglar
- Günlük/haftalık istatistikler tutar
- Düşük kaliteli senaryoları işaretler
"""

import json
from datetime import datetime, timezone
from pathlib import Path


KALITE_LOG_YOLU = Path("bobi_tv/logs/quality")


def kalite_log_yaz(video_no: int, rapor: dict) -> None:
    """
    Kalite raporunu dosyaya yaz.

    Args:
        video_no: Video numarası
        rapor: Kalite raporu dict (KaliteRaporu.to_dict())
    """
    KALITE_LOG_YOLU.mkdir(parents=True, exist_ok=True)

    tarih = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    zaman = datetime.now(timezone.utc).strftime("%H:%M:%S")

    kayit = {
        "video_no": video_no,
        "zaman": f"{tarih}T{zaman}",
        "toplam_puan": rapor.get("toplam_puan", 0),
        "gecti": rapor.get("gecti", False),
        "detaylar": {
            "loop": rapor.get("loop_sonuc", {}).get("puan", 0),
            "kanca": rapor.get("kanca_sonuc", {}).get("puan", 0),
            "zamanlama": rapor.get("zamanlama_sonuc", {}).get("puan", 0),
            "diyalog": rapor.get("diyalog_sonuc", {}).get("puan", 0),
        },
        "oneriler": rapor.get("oneriler", [])[:5],  # İlk 5 öneri
    }

    log_dosya = KALITE_LOG_YOLU / f"{tarih}.jsonl"

    with open(log_dosya, "a", encoding="utf-8") as f:
        f.write(json.dumps(kayit, ensure_ascii=False) + "\n")


def kalite_istatistik(tarih: str | None = None) -> dict:
    """
    Günlük kalite istatistiklerini hesapla.

    Args:
        tarih: Tarih (YYYY-MM-DD), boşsa bugün

    Returns:
        İstatistik dict
    """
    if not tarih:
        tarih = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    log_dosya = KALITE_LOG_YOLU / f"{tarih}.jsonl"

    if not log_dosya.exists():
        return {"toplam": 0, "ortalama_puan": 0, "gecen": 0, "kalan": 0}

    kayıtlar = []
    with open(log_dosya, "r", encoding="utf-8") as f:
        for satir in f:
            try:
                kayıtlar.append(json.loads(satir))
            except Exception:
                continue

    if not kayıtlar:
        return {"toplam": 0, "ortalama_puan": 0, "gecen": 0, "kalan": 0}

    toplam = len(kayıtlar)
    puanlar = [k["toplam_puan"] for k in kayıtlar]
    gecen = sum(1 for k in kayıtlar if k["gecti"])

    return {
        "toplam": toplam,
        "ortalama_puan": round(sum(puanlar) / toplam, 1) if toplam > 0 else 0,
        "gecen": gecen,
        "kalan": toplam - gecen,
        "min_puan": min(puanlar) if puanlar else 0,
        "max_puan": max(puanlar) if puanlar else 0,
    }


if __name__ == "__main__":
    # Test
    istatistik = kalite_istatistik()
    print(f"Bugünkü kalite istatistikleri: {istatistik}")
