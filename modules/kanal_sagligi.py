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
#: Günlük ölçümlerin kalıcı geçmişi (etki ölçümü için — bkz. ozeti_birlestir).
GECMIS = Path("bobi_tv/state/kanal_sagligi_gecmis.json")

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


def kanca_formu_performansi(gun: int = 7, simdi: datetime | None = None) -> dict[str, Any]:
    """Kanca FORM bazında izlenme karşılaştırması (A/B/C öğrenmesi).

    Neden: kanca motoru her videoda farklı form deniyor (soru/sahne/iddia/
    itiraf). Hangi formun daha iyi çalıştığını ANCAK kayıt tutarsak biliriz.
    Arşivde `kanca_formu` alanı + izlenme varsa form bazında ortalama verilir.

    Döner: {"form_verisi": {"soru": {"video": 3, "ortalama": 12.5}, ...},
            "en_iyi_form": "soru" | "" , "ornek": int}
    """
    simdi = simdi or datetime.now(UTC)
    esik = simdi - timedelta(days=gun)
    kova: dict[str, list[int]] = {}
    for kayit in _arsiv():
        if (_tarih(kayit) or simdi) < esik:
            continue
        form = str(kayit.get("kanca_formu") or "").strip()
        izlenme = _izlenme(kayit)
        if not form or izlenme is None:
            continue
        kova.setdefault(form, []).append(izlenme)

    form_verisi = {
        form: {"video": len(degerler), "ortalama": round(mean(degerler), 1)}
        for form, degerler in kova.items()
    }
    en_iyi = ""
    if form_verisi:
        # En az 2 video görmüş formlar arasından seç (tek video yanıltıcı)
        adaylar = {f: v for f, v in form_verisi.items() if v["video"] >= 2}
        if adaylar:
            en_iyi = max(adaylar.items(), key=lambda kv: kv[1]["ortalama"])[0]
    return {
        "form_verisi": form_verisi,
        "en_iyi_form": en_iyi,
        "ornek": sum(v["video"] for v in form_verisi.values()),
    }


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
    kanca = kanca_formu_performansi(gun, simdi)
    ozet["kanca"] = kanca
    if kanca.get("en_iyi_form"):
        ozet["kanca_onerisi"] = (
            f"{kanca['en_iyi_form']} formu daha iyi "
            f"({kanca['form_verisi'][kanca['en_iyi_form']]['ortalama']} ort. izlenme)"
        )
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


def ozeti_birlestir(ozet: dict[str, Any], dosya: Path | None = None) -> None:
    """Bugünün özetini kalıcı geçmişe ekler (kadans değişikliğinin ETKİSİ ölçülsün).

    Neden: günlük iş her koşuda son 7 günün penceresini yazar. Geçmiş
    saklanmazsa "8 saatlik kadans işe yaradı mı?" sorusu bir daha
    cevaplanamaz (pencere kayar, eski ölçüm kaybolur).

    Dosya: `bobi_tv/state/kanal_sagligi_gecmis.json` → {"gunler": [{...}]}
    Aynı gün ikinci kez koşarsa o günün kaydı GÜNCELLENİR (çift satır yok).
    """
    hedef = dosya or GECMIS
    try:
        veri = json.loads(hedef.read_text(encoding="utf-8"))
    except Exception:
        veri = {}
    gunler = list(veri.get("gunler") or [])
    bugun = str(ozet.get("zaman", ""))[:10]
    kayit = {
        anahtar: ozet.get(anahtar)
        for anahtar in (
            "zaman", "gun", "uretilen", "silinen", "izlenme_ornek",
            "ortalama_izlenme", "medyan_izlenme", "en_yuksek_izlenme",
            "akisa_giren", "akisa_girme_orani", "kalite_ornek",
            "kalite_ortalama", "yorum",
        )
    }
    kayit["kanca_en_iyi_form"] = (ozet.get("kanca") or {}).get("en_iyi_form", "")
    eski_indeks = next(
        (i for i, k in enumerate(gunler) if str(k.get("zaman", ""))[:10] == bugun), None
    )
    if eski_indeks is None:
        gunler.append(kayit)
    else:
        gunler[eski_indeks] = kayit
    # Son 120 günü tut (dosya şişmesin)
    gunler = gunler[-120:]
    try:
        hedef.parent.mkdir(parents=True, exist_ok=True)
        hedef.write_text(
            json.dumps({"sur": 1, "gunler": gunler}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


def rapor_yaz(simdi: datetime | None = None, gun: int = 7) -> dict[str, Any]:
    """Özeti hesapla + state'e yaz (panel ve günlük rapor buradan okur)."""
    ozet = saglik_ozeti(gun, simdi)
    try:
        RAPOR.parent.mkdir(parents=True, exist_ok=True)
        RAPOR.write_text(json.dumps(ozet, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    ozeti_birlestir(ozet)
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
    kanca = ozet.get("kanca") or {}
    kanca_eki = ""
    if kanca.get("en_iyi_form"):
        kanca_eki = f" · 🪝 {kanca['en_iyi_form']}"
    return (
        f"🩺 Kanal: ort. {ozet.get('ortalama_izlenme')} izlenme · "
        f"akışa giren %{ozet.get('akisa_girme_orani')} · "
        f"kalite {ozet.get('kalite_ortalama') or '—'}{kanca_eki}"
    )


def main() -> int:
    """CLI: `python3 -m modules.kanal_sagligi` → özet yazar, JSON basar."""
    ozet = rapor_yaz()
    print(json.dumps(ozet, ensure_ascii=False, indent=2))
    print(f"[Sağlık] {panel_satiri()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
