"""BOBİ TV — Cron cadans gözlemi (TODO dosyası madde 4).

NEDEN
-----
`hourly_production.yml` `*/10 * * * *` diyor ama GitHub scheduler fiilen çok
daha seyrek çalışıyor (ölçüm 2026-11-10: günde 2 koşu, aralarında 168 dk;
2026-11-11: poller 3 saat susunca kullanıcı cevap alamadı). Cron ifadesine
bakarak "10 dakikada bir çalışıyor" demek YANLIŞ.

BU MODÜL NE YAPAR
-----------------
GitHub Actions koşu geçmişini okur ve ÖLÇÜLMÜŞ sayıları verir:
- son 24 saatte kaç koşu oldu (gerçek),
- koşular arası medyan/tipik boşluk,
- beklenen (cron) ile gerçekleşen oranı.

Panelde ve günlük raporda bu sayılar kullanılır. Veri okunamazsa
"bilinmiyor" der — sayı uydurulmaz (mevcut felsefe).
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from statistics import median
from typing import Any

#: Ölçüm raporu (son koşunun özeti).
RAPOR_YOLU = Path("bobi_tv/state/cadans_olcumu.json")

#: İzlenen workflow dosyaları ve cron'dan BEKLENEN koşu aralığı (dakika).
IZLENEN: dict[str, int] = {
    "hourly_production.yml": 10,
    "telegram_bot.yml": 5,
}

#: Koşu geçmişi okunamazsa kullanılan dürüst değer.
BILINMIYOR = "bilinmiyor"


def _github_get(yol: str) -> dict[str, Any] | None:
    """GitHub API'den JSON okur (token varsa yetkili, yoksa anonim)."""
    import requests

    basliklar = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
    if token:
        basliklar["Authorization"] = f"Bearer {token}"
    try:
        r = requests.get(f"https://api.github.com/{yol}", headers=basliklar, timeout=10)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception:
        return None


def _zaman(ham: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(str(ham).replace("Z", "+00:00"))
    except Exception:
        return None


def kosulari_oku(
    workflow: str, repo: str = "mehetgege3-cmyk/bobi-tv", adet: int = 100
) -> list[datetime] | None:
    """Workflow'un son `adet` koşusunun başlangıç zamanları (yeniden eskiye).

    `None` = okunamadı (ağ/izin hatası) — çağıran "bilinmiyor" der.
    """
    veri = _github_get(f"repos/{repo}/actions/workflows/{workflow}/runs?per_page={adet}")
    if veri is None:
        return None
    kosular = (veri or {}).get("workflow_runs")
    if kosular is None:
        return None
    zamanlar: list[datetime] = []
    for k in kosular:
        z = _zaman(k.get("created_at") or k.get("run_started_at"))
        if z is not None:
            zamanlar.append(z)
    return sorted(zamanlar, reverse=True)


def cadans_olc(
    workflow: str,
    beklenen_dk: int,
    simdi: datetime | None = None,
    zamanlar: list[datetime] | None = None,
) -> dict[str, Any]:
    """Ölçüm: son 24 saatte kaç koşu, aralar kaç dakika, beklentiye oranı.

    ÖNEMLİ: "koşu sayısı" ile "koşu aralığı" ayrı şeylerdir. 5.5 saat ayakta
    kalan uzun koşular (poller) sayıyı düşük gösterir; bu yüzden oran hesabı
    yalnızca BİTEN koşuların aralığına bakar ve panelde iki sayı ayrı yazılır.
    """
    simdi = simdi or datetime.now(UTC)
    if zamanlar is None:
        zamanlar = kosulari_oku(workflow)
    if zamanlar is None:
        return {
            "workflow": workflow,
            "durum": BILINMIYOR,
            "sebep": "koşu geçmişi okunamadı (ağ/izin)",
            "beklenen_dk": beklenen_dk,
        }
    if not zamanlar:
        return {
            "workflow": workflow,
            "durum": BILINMIYOR,
            "sebep": "hiç koşu kaydı yok",
            "beklenen_dk": beklenen_dk,
        }
    esik = simdi - timedelta(hours=24)
    son_24 = [z for z in zamanlar if z >= esik]
    araliklar = [
        round((yenisi - eskisi).total_seconds() / 60, 1)
        for yenisi, eskisi in zip(zamanlar, zamanlar[1:], strict=False)
    ]
    araliklar = [a for a in araliklar if a > 0]
    medyan = round(median(araliklar), 1) if araliklar else None
    return {
        "workflow": workflow,
        "durum": "olculdu",
        "beklenen_dk": beklenen_dk,
        "son_24saat_kosu": len(son_24),
        "toplam_kosu": len(zamanlar),
        "medyan_aralik_dk": medyan,
        "en_uzun_aralik_dk": max(araliklar) if araliklar else None,
        "beklenen_24saat_kosu": round(24 * 60 / beklenen_dk, 1),
        "oran": (round(len(son_24) / (24 * 60 / beklenen_dk), 2) if beklenen_dk else None),
        "son_kosu_yas_dk": round((simdi - zamanlar[0]).total_seconds() / 60, 1),
    }


def tumunu_olc(simdi: datetime | None = None) -> dict[str, Any]:
    """Bilinen tüm workflow'lar için ölçüm + state'e yaz."""
    simdi = simdi or datetime.now(UTC)
    rapor = {
        "zaman": simdi.isoformat(),
        "olcumler": {w: cadans_olc(w, d, simdi) for w, d in IZLENEN.items()},
    }
    try:
        RAPOR_YOLU.parent.mkdir(parents=True, exist_ok=True)
        RAPOR_YOLU.write_text(json.dumps(rapor, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    return rapor


def panel_satiri() -> str:
    """Panelde gösterilecek TEK satırlık dürüst özet."""
    try:
        rapor = json.loads(RAPOR_YOLU.read_text(encoding="utf-8"))
    except Exception:
        return f"📉 Cadans: {BILINMIYOR} (ölçüm yok)"
    uretim = (rapor.get("olcumler") or {}).get("hourly_production.yml") or {}
    if uretim.get("durum") != "olculdu":
        return f"📉 Cadans: {BILINMIYOR}"
    oran = uretim.get("oran")
    if oran is None:
        return f"📉 Cadans: {uretim.get('son_24saat_kosu', '?')} koşu/24sa"
    yuzde = round(float(oran) * 100)
    ikon = "✅" if yuzde >= 70 else ("⚠️" if yuzde >= 30 else "⛔")
    return (
        f"📉 Cadans: {ikon} %{yuzde} (24sa: {uretim.get('son_24saat_kosu')} koşu, "
        f"medyan {uretim.get('medyan_aralik_dk')} dk)"
    )


if __name__ == "__main__":
    rapor = tumunu_olc()
    for w, o in rapor["olcumler"].items():
        print(f"[Cadans] {w}: {json.dumps(o, ensure_ascii=False)}")
    print(f"[Cadans] panel: {panel_satiri()}")
