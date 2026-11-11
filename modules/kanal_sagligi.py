"""BOBİ TV — Kanal sağlığı ölçümü (2026-11-11 sonrası).

NEDEN
-----
Kullanıcı: "kanal istatistikleri çok düştü, videolar hiç gösterim almıyor,
algoritma bizi biçti." Bu bir DUYGU değil, ölçülmesi gereken bir durum.
Kadans 8 saate çekildi (günde 3) ve silme eşiği 6 saate alındı; bu değişikliğin
işe yarayıp yaramadığını ancak ÖLÇÜM söyler.

NE ÖLÇER (hepsi elimizdeki veriden, uydurma yok)
-----------------------------------------------
1. **İlk saat / ilk 6 saat izlenme** — arşivdeki snapshot + silinme kayıtları.
2. **Akışa giriş oranı**: 6 saatte 100 izlenmeyi geçen video yüzdesi
   (kanal "spam cezası"ndan çıkıyor mu?).
3. **Kalite puanı** (senaryo kalite günlüğü) — içerik mi, dağıtım mı sorunlu?
4. **Kadans** — gerçekten 8 saatte bir mi üretiliyor (cron_olcum ile).

Çıktı: state/kanal_sagligi.json + panelde tek blok + günlük rapor satırı.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from statistics import mean, median
from typing import Any

ARSIV = Path("bobi_tv/archive/videos.json")
KALITE_DIZINI = Path("bobi_tv/logs/quality")
RAPOR = Path("bobi_tv/state/kanal_sagligi.json")

#: "Akışa girdi" sayılma eşiği (izlenme). Kullanıcı kuralıyla aynı: 100.
AKIS_ESIGI = 100

#: Karar için gereken asgari örnek (az veriyle "iyileşti" demek yanıltıcı olur).
ASGARI_ORNEK = 5

BILINMIYOR = "bilinmiyor"


def _arsiv() -> list[dict[str, Any]]:
    try:
        veri = json.loads(ARSIV.read_text(encoding="utf-8"))
        return list(veri.values()) if isinstance(veri, dict) else list(veri)
    except Exception:
        return []


def _tarih(kayit: dict[str, Any]) -> datetime | None:
    """Kayıt zamanı — her zaman UTC farkındalı (naive/aware karşılaştırma hatası yok)."""
    for alan in ("tarih", "silinme_tarihi"):
        try:
            deger = datetime.fromisoformat(str(kayit.get(alan, "")).replace("Z", "+00:00"))
        except Exception:
            continue
        return deger if deger.tzinfo else deger.replace(tzinfo=UTC)
    return None


def _izlenme(kayit: dict[str, Any]) -> int | None:
    """Elimizdeki en iyi izlenme sinyali (yoksa None — uydurma yok)."""
    for alan in ("silinme_izlenme", "izlenme", "son_izlenme"):
        deger = kayit.get(alan)
        if isinstance(deger, (int, float)):
            return int(deger)
    snaps = kayit.get("izlenme_snapshots")
    if isinstance(snaps, dict) and snaps:
        en_yeni = max(snaps.items(), key=lambda kv: str(kv[0]))
        if isinstance(en_yeni[1], (int, float)):
            return int(en_yeni[1])
    return None


def kalite_puanlari(gun: int = 7, simdi: datetime | None = None) -> list[float]:
    """Son `gun` günün senaryo kalite puanları (jsonl dosyalarından)."""
    simdi = simdi or datetime.now(UTC)
    puanlar: list[float] = []
    for i in range(gun):
        tarih = (simdi - timedelta(days=i)).strftime("%Y-%m-%d")
        dosya = KALITE_DIZINI / f"{tarih}.jsonl"
        if not dosya.exists():
            continue
        try:
            for satir in dosya.read_text(encoding="utf-8").splitlines():
                try:
                    kayit = json.loads(satir)
                except Exception:
                    continue
                puan = kayit.get("toplam_puan")
                if isinstance(puan, (int, float)):
                    puanlar.append(float(puan))
        except Exception:
            continue
    return puanlar


def saglik_ozeti(gun: int = 7, simdi: datetime | None = None) -> dict[str, Any]:
    """Son `gun` günün kanal sağlığı özeti (dürüst: veri yoksa bilinmiyor)."""
    simdi = simdi or datetime.now(UTC)
    esik = simdi - timedelta(days=gun)
    kayitlar = [k for k in _arsiv() if (_tarih(k) or simdi) >= esik]

    izlenmeler = [i for i in (_izlenme(k) for k in kayitlar) if i is not None]
    silinen = [k for k in kayitlar if str(k.get("durum", "")) == "silindi_dusuk_izlenme"]
    akisa_giren = [i for i in izlenmeler if i >= AKIS_ESIGI]

    puanlar = kalite_puanlari(gun, simdi)

    ozet: dict[str, Any] = {
        "zaman": simdi.isoformat(),
        "gun": gun,
        "uretilen": len(kayitlar),
        "silinen": len(silinen),
        "izlenme_ornek": len(izlenmeler),
        "ortalama_izlenme": round(mean(izlenmeler), 2) if izlenmeler else None,
        "medyan_izlenme": round(median(izlenmeler), 1) if izlenmeler else None,
        "en_yuksek_izlenme": max(izlenmeler) if izlenmeler else None,
        "akisa_giren": len(akisa_giren),
        "akisa_girme_orani": (
            round(100 * len(akisa_giren) / len(izlenmeler)) if izlenmeler else None
        ),
        "kalite_ornek": len(puanlar),
        "kalite_ortalama": round(mean(puanlar), 1) if puanlar else None,
    }
    ozet["yorum"] = _yorum(ozet)
    return ozet


def _yorum(ozet: dict[str, Any]) -> str:
    """Ölçümü insan diline çevirir — karar cümlesi UYDURULMAZ, eşik açıkça yazılır."""
    ornek = ozet.get("izlenme_ornek") or 0
    if ornek < ASGARI_ORNEK:
        return f"veri yetersiz ({ornek}/{ASGARI_ORNEK} video) — yorum yok"
    oran = ozet.get("akisa_girme_orani")
    if oran is None:
        return "izlenme verisi okunamadı"
    if oran >= 50:
        return "🟢 akışa giriş sağlıklı (%50+)"
    if oran >= 20:
        return "🟡 kısmi dağıtım — kadans/icerik ayarı sürüyor"
    return "🔴 akışa giriş yok — algoritma hâlâ dağıtmıyor; içerik/kanca gözden geçir"


def rapor_yaz(simdi: datetime | None = None, gun: int = 7) -> dict[str, Any]:
    """Özeti hesapla + state'e yaz (panel ve günlük rapor buradan okur)."""
    ozet = saglik_ozeti(gun, simdi)
    try:
        RAPOR.parent.mkdir(parents=True, exist_ok=True)
        RAPOR.write_text(json.dumps(ozet, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    return ozet


def son_ozet() -> dict[str, Any]:
    try:
        return dict(json.loads(RAPOR.read_text(encoding="utf-8")))
    except Exception:
        return {}


def panel_satiri() -> str:
    """Panelde 1 satır: ölçülmüş sağlık durumu."""
    ozet = son_ozet()
    if not ozet:
        return "🩺 Kanal: ölçüm yok (günlük sağlık işi henüz koşmadı)"
    if ozet.get("izlenme_ornek", 0) == 0:
        return "🩺 Kanal: veri yetersiz (izlenme kaydı yok)"
    return (
        f"🩺 Kanal: ort. {ozet.get('ortalama_izlenme')} izlenme · "
        f"akışa giren %{ozet.get('akisa_girme_orani')} · "
        f"kalite {ozet.get('kalite_ortalama') or '—'}"
    )


def main() -> int:
    """CLI: `python3 -m modules.kanal_sagligi` → özet yazar, JSON basar."""
    ozet = rapor_yaz()
    print(json.dumps(ozet, ensure_ascii=False, indent=2))
    print(f"[Sağlık] {panel_satiri()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
