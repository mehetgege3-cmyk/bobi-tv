"""BOBİ TV — Mini App veri üreticisi (TODO 31).

TEK GÖREV: Mini App'in okuyacağı `webapp/veri/mini_app_ozet.json` dosyasını
mevcut modüllerden üretmek. Kendi başına HESAP YAPMAZ, sayı UYDURMAZ:

- üretim/yayın sayıları  : `main_pipeline.bugun_arsiv_kayitlari`
- stok                    : `modules.kuyruk_yonetimi.ozet`
- denetim kaydı           : `modules.denetim.son_kayitlar`
- 7 günlük seri           : arşiv tarihlerinden sayılır

Dosya okunamazsa ilgili alan `null` olur ve Mini App "bilinmiyor" yazar.
Günlük yükleme tavanı YOKTUR (2026-11-11) — şemada `null` olarak durur.
"""
from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

OZET_YOLU = Path(os.environ.get("MINI_APP_OZET_YOLU", "webapp/veri/mini_app_ozet.json"))
ARSIV_YOLU = Path("bobi_tv/archive/videos.json")

#: Mini App'te gösterilecek azami denetim satırı (mobil ekran).
DENETIM_AZAMI = 10


def _arsiv() -> list[dict[str, Any]] | None:
    """Arşiv kayıtları; okunamazsa None (uydurma yok)."""
    try:
        veri = json.loads(ARSIV_YOLU.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if isinstance(veri, dict):
        return [k for k in veri.values() if isinstance(k, dict)]
    if isinstance(veri, list):
        return [k for k in veri if isinstance(k, dict)]
    return None


def _tarih(kayit: dict[str, Any]) -> str:
    return str(kayit.get("tarih", ""))[:10]


def bugun_sayilari(simdi: datetime, kayitlar: list[dict[str, Any]] | None) -> dict[str, Any]:
    """Bugün üretilen/yayınlanan. Arşiv yoksa None (0 YAZILMAZ — 0 gerçek olabilir)."""
    if kayitlar is None:
        return {"uretilen": None, "yayinda": None}
    gun = simdi.strftime("%Y-%m-%d")
    bugun = [k for k in kayitlar if _tarih(k) == gun]
    return {
        "uretilen": len(bugun),
        "yayinda": sum(1 for k in bugun if k.get("durum") == "yayinda"),
    }


def trend_serisi(simdi: datetime, kayitlar: list[dict[str, Any]] | None, gun: int = 7) -> list[int] | None:
    """Son `gun` günün günlük üretim sayısı (eskiden yeniye). Arşiv yoksa None."""
    if kayitlar is None:
        return None
    seri = []
    for geri in range(gun - 1, -1, -1):
        hedef = (simdi - timedelta(days=geri)).strftime("%Y-%m-%d")
        seri.append(sum(1 for k in kayitlar if _tarih(k) == hedef))
    return seri


def kuyruk_ozeti() -> dict[str, Any]:
    """Stok (kuyruk) özeti; modül patlarsa None alanlar."""
    try:
        from modules.kuyruk_yonetimi import ozet

        o = ozet()
        return {
            "toplam": o["toplam"],
            "sebep_dagilimi": o["sebep_dagilimi"],
            "bayat": o["bayat"],
            "video_yok": o["video_yok"],
        }
    except Exception:
        return {"toplam": None, "sebep_dagilimi": {}, "bayat": None, "video_yok": None}


def denetim_ozeti() -> list[dict[str, Any]]:
    """Son N denetim kaydı (secret içermez — maskelenmiş dosyadan gelir)."""
    try:
        from modules.denetim import son_kayitlar

        kayitlar = son_kayitlar(DENETIM_AZAMI)
    except Exception:
        return []
    # Yalnız güvenli alanlar Mini App'e gider (ayrinti TAŞINMAZ).
    return [
        {
            "zaman": str(k.get("zaman", ""))[:16],
            "olay": str(k.get("olay", "bilinmiyor")),
            "sonuc": str(k.get("sonuc", "bilinmiyor")),
        }
        for k in kayitlar
    ]


def ozet_uret(simdi: datetime | None = None) -> dict[str, Any]:
    """Mini App özetini üretir (saf; dosyaya yazmaz)."""
    simdi = simdi or datetime.now(UTC)
    kayitlar = _arsiv()
    return {
        "guncelleme": simdi.isoformat(),
        "bugun": bugun_sayilari(simdi, kayitlar),
        "kuyruk": kuyruk_ozeti(),
        "trend7": trend_serisi(simdi, kayitlar),
        "denetim": denetim_ozeti(),
        "sinirlar": {"gunluk_yukleme_tavani": None, "not": "tavan YOK"},
    }


def yaz(simdi: datetime | None = None, yol: Path | None = None) -> dict[str, Any]:
    """Özeti dosyaya yazar. Döner: üretilen sözlük (çağıran loglar)."""
    yol = yol or OZET_YOLU
    veri = ozet_uret(simdi)
    try:
        yol.parent.mkdir(parents=True, exist_ok=True)
        yol.write_text(json.dumps(veri, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as e:
        veri["yazma_hatasi"] = str(e)[:120]
    return veri


def metin_ozet(veri: dict[str, Any]) -> str:
    """Telegram'da paylaşılabilir kısa özet (bot komutu `/mini`)."""
    b = veri.get("bugun") or {}
    k = veri.get("kuyruk") or {}
    uretilen = b.get("uretilen")
    yayinda = b.get("yayinda")
    toplam = k.get("toplam")
    return (
        "📱 <b>Mini App verisi</b>\n"
        f"🎥 Bugün: {uretilen if uretilen is not None else 'bilinmiyor'} üretildi\n"
        f"🚀 Yayında: {yayinda if yayinda is not None else 'bilinmiyor'}\n"
        f"📦 Stok: {toplam if toplam is not None else 'bilinmiyor'}\n"
        f"🕐 Güncelleme: {str(veri.get('guncelleme', ''))[:16]}"
    )
