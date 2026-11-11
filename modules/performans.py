"""BOBİ TV — Performans analizi + izlenme snapshot'ı (TODO 17 + 18, Hakan/Kaan).

NEDEN SNAPSHOT
--------------
YouTube Analytics API günlük çözünürlük verir; SAATLİK veri yalnızca
YouTube Studio'da vardır ve sayılar ~3 gün gecikmeyle oturur. Bu yüzden
"hangi saatte yüklenen video daha iyi" sorusunu API'ye soramayız.
Kendi verimizi üretiyoruz: yükleme sonrası +1 sa, +24 sa, +72 sa
izlenme sayısı arşive yazılır (`izlenme_snapshots`).

KURALLAR (mevcut felsefe)
-------------------------
1. Uydurma sayı YOK: veri yoksa ekran "bilinmiyor"/"veri yetersiz" der.
2. Outlier skoru = video izlenmesi ÷ kanal medyanı. Kanal medyanı 0 ise
   skor hesaplanmaz (bölme yok, uydurma yok).
3. `videos.list` 50 id'ye kadar TEK çağrıda okunur = ~1 kota birimi.
4. Kota/hata durumunda çökme yok; (None, sebep) döner.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from statistics import median
from typing import Any

ARSIV = Path("bobi_tv/archive/videos.json")

#: Snapshot yaşları (saat) — kullanıcı kararı: +1 sa, +24 sa, +72 sa.
SNAPSHOT_SAATLERI: tuple[int, ...] = (1, 24, 72)

#: YouTube yükleme saati analizi için gereken asgari örnek sayısı.
ASGARI_ORNEK = 5


# ---------------------------------------------------------------------------
# Arşiv okuma / yazma
# ---------------------------------------------------------------------------

def _arsiv_oku() -> list[dict[str, Any]]:
    try:
        veri = json.loads(ARSIV.read_text(encoding="utf-8"))
        return list(veri.values()) if isinstance(veri, dict) else list(veri)
    except Exception:
        return []


def _arsiv_yaz(kayitlar: list[dict[str, Any]]) -> bool:
    try:
        ARSIV.parent.mkdir(parents=True, exist_ok=True)
        ARSIV.write_text(json.dumps(kayitlar, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception as e:
        print(f"[Performans] arşiv yazılamadı: {str(e)[:80]}")
        return False


# ---------------------------------------------------------------------------
# YouTube okuma (tek çağrı, 50 id)
# ---------------------------------------------------------------------------

def izlenmeleri_oku(video_idler: list[str]) -> tuple[dict[str, int] | None, str]:
    """YouTube'dan izlenme sayıları — 50 id'ye kadar TEK çağrı (~1 birim).

    Döner: ({video_id: izlenme}, "") veya (None, sebep).
    """
    if not video_idler:
        return {}, ""
    if not os.environ.get("YOUTUBE_TOKEN", "").strip():
        return None, "YOUTUBE_TOKEN yok"
    try:
        import requests

        from modules.youtube_upload import VIDEOS_URI, token_yenile, token_yukle

        erisim = token_yenile(token_yukle())
        sonuc: dict[str, int] = {}
        # 50'lik gruplar: API tek istekte en fazla 50 id kabul eder.
        for bas in range(0, len(video_idler), 50):
            grup = video_idler[bas : bas + 50]
            yanit = requests.get(
                f"{VIDEOS_URI}?part=statistics&id={','.join(grup)}",
                headers={"Authorization": f"Bearer {erisim}"},
                timeout=20,
            )
            if yanit.status_code != 200:
                return None, f"YouTube API {yanit.status_code}"
            for oge in yanit.json().get("items", []):
                try:
                    sonuc[str(oge["id"])] = int(oge["statistics"]["viewCount"])
                except (KeyError, TypeError, ValueError):
                    continue
        return sonuc, ""
    except Exception as e:
        return None, str(e)[:80]


# ---------------------------------------------------------------------------
# Snapshot (TODO 18)
# ---------------------------------------------------------------------------

def _saat_farki(simdi: datetime, damga: str) -> float | None:
    try:
        an = datetime.fromisoformat(str(damga).replace("Z", "+00:00"))
        return (simdi - an).total_seconds() / 3600
    except Exception:
        return None


def snapshot_gerekenler(kayitlar: list[dict[str, Any]], simdi: datetime | None = None) -> list[dict[str, Any]]:
    """Hangi kayıt için hangi snapshot zamanı GELMİŞ ve HENÜZ alınmamış."""
    simdi = simdi or datetime.now(UTC)
    gereken: list[dict[str, Any]] = []
    for k in kayitlar:
        if k.get("durum") != "yayinda" or not k.get("video_id"):
            continue
        fark = _saat_farki(simdi, str(k.get("tarih", "")))
        if fark is None:
            continue
        # DİKKAT: `globals()` üzerinden okunur ki testler eşikleri
        # monkeypatch ile değiştirebilsin (sabit kopyalama tuzak olur).
        alinmis = k.setdefault("izlenme_snapshots", {})
        for saat in globals()["SNAPSHOT_SAATLERI"]:
            anahtar = f"+{saat}h"
            # Zamanı geldi (+%10 tolerans) ve daha önce alınmadı
            if fark >= saat and anahtar not in alinmis:
                gereken.append({"kayit": k, "anahtar": anahtar})
    return gereken


def snapshotlari_guncelle(simdi: datetime | None = None) -> dict[str, Any]:
    """Zamanı gelen snapshot'ları YouTube'dan okuyup arşive yazar.

    Kota dostu: tüm gereken idler TEK videos.list çağrısında okunur.
    """
    simdi = simdi or datetime.now(UTC)
    kayitlar = _arsiv_oku()
    gereken = snapshot_gerekenler(kayitlar, simdi)
    if not gereken:
        return {"yazilan": 0, "sebep": "gereken snapshot yok"}

    idler = list({str(g["kayit"]["video_id"]) for g in gereken})
    izlenmeler, hata = izlenmeleri_oku(idler)
    if izlenmeler is None:
        return {"yazilan": 0, "sebep": hata}

    yazilan = 0
    for g in gereken:
        vid = str(g["kayit"]["video_id"])
        if vid not in izlenmeler:
            continue
        g["kayit"].setdefault("izlenme_snapshots", {})[g["anahtar"]] = {
            "izlenme": izlenmeler[vid],
            "zaman": simdi.isoformat(),
        }
        yazilan += 1
    if yazilan:
        _arsiv_yaz(kayitlar)
    return {"yazilan": yazilan, "sebep": ""}


# ---------------------------------------------------------------------------
# Performans ekranı (TODO 17)
# ---------------------------------------------------------------------------

def performans_ozeti(azami: int = 10, simdi: datetime | None = None) -> dict[str, Any]:
    """Son N yayındaki videonun izlenmesi + outlier skoru.

    Döner: {"videolar": [...], "medyan": int|None, "hata": str}
    `hata` boşsa veri gerçektir; doluysa ekran "bilinmiyor" yazar.
    """
    kayitlar = [k for k in _arsiv_oku() if k.get("durum") == "yayinda" and k.get("video_id")]
    if not kayitlar:
        return {"videolar": [], "medyan": None, "hata": "yayında video yok"}
    kayitlar.sort(key=lambda k: str(k.get("tarih", "")), reverse=True)
    son = kayitlar[:azami]

    izlenmeler, hata = izlenmeleri_oku([str(k["video_id"]) for k in son])
    if izlenmeler is None:
        return {"videolar": [], "medyan": None, "hata": hata}

    degerler = [izlenmeler[str(k["video_id"])] for k in son if str(k["video_id"]) in izlenmeler]
    medyan = int(median(degerler)) if degerler else None

    videolar: list[dict[str, Any]] = []
    for k in son:
        vid = str(k["video_id"])
        if vid not in izlenmeler:
            continue
        izlenme = izlenmeler[vid]
        # Kanal medyanı 0 ise skor HESAPLANMAZ (bölme yok, uydurma yok).
        skor = round(izlenme / medyan, 2) if medyan else None
        videolar.append(
            {
                "video_id": vid,
                "baslik": str(k.get("baslik", ""))[:45],
                "izlenme": izlenme,
                "skor": skor,
                "tarih": str(k.get("tarih", ""))[:16],
            }
        )
    return {"videolar": videolar, "medyan": medyan, "hata": ""}


def en_iyi_en_kotu(videolar: list[dict[str, Any]], adet: int = 3) -> tuple[list, list]:
    """En iyi / en kötü N video (skor varsa skora, yoksa izlenmeye göre)."""
    if not videolar:
        return [], []
    sirali = sorted(videolar, key=lambda v: v["izlenme"], reverse=True)
    return sirali[:adet], list(reversed(sirali[-adet:]))


# ---------------------------------------------------------------------------
# Yükleme saati analizi (TODO 18)
# ---------------------------------------------------------------------------

def saat_analizi() -> dict[str, Any]:
    """Hangi yükleme saati daha iyi? Yeterli örnek yoksa 'veri yetersiz'.

    Saat, TÜRKİYE saatine (UTC+3) göre gruplanır — kullanıcı TR'de.
    """
    kayitlar = [
        k for k in _arsiv_oku()
        if k.get("durum") == "yayinda" and k.get("izlenme_snapshots")
    ]
    if len(kayitlar) < ASGARI_ORNEK:
        return {
            "yeterli": False,
            "sebep": f"veri yetersiz ({len(kayitlar)}/{ASGARI_ORNEK} video snapshot'lı)",
            "gruplar": {},
        }
    gruplar: dict[int, list[int]] = {}
    for k in kayitlar:
        try:
            an = datetime.fromisoformat(str(k.get("tarih", "")).replace("Z", "+00:00"))
            saat_tr = (an.hour + 3) % 24
            # En son snapshot izlenmesi (en olgun veri)
            snaps = k.get("izlenme_snapshots") or {}
            if not snaps:
                continue
            son = snaps[sorted(snaps)[-1]]
            gruplar.setdefault(saat_tr, []).append(int(son.get("izlenme", 0)))
        except Exception:
            continue
    if len(gruplar) < 2:
        return {
            "yeterli": False,
            "sebep": "tek saat diliminde veri var — karşılaştırma yapılamaz",
            "gruplar": {},
        }
    ozet = {s: round(sum(v) / len(v), 1) for s, v in gruplar.items()}
    return {"yeterli": True, "sebep": "", "gruplar": ozet}
