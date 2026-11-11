"""BOBİ TV — Denetim kaydı (TODO 27).

AMAÇ: "Bunu kim, ne zaman, nereden yaptı?" sorusunun kalıcı cevabı. Özellikle
GERİ ALINAMAZ işlemlerde (video silme, üretim tetikleme, ayar değişikliği)
kayıt tutulmadan işlem yapılmaz.

TASARIM
-------
- Tek dosya, satır başına bir JSON nesnesi (JSONL) → `bobi_tv/logs/denetim.jsonl`.
- Her satır: zaman (UTC ISO), olay, sonuc, kullanici_id, ayrinti, iz (özet hash).
- **Secret/token asla yazılmaz**: kayıt önce `_maskele` ile temizlenir.
- Dosya büyürse döndürülür (`denetim.jsonl.1`), sınırsız büyüme yok.
- Okuma tarafı ASLA çökmez: bozuk satır atlanır, sayısı raporlanır.

NEDEN state değil log: state dosyaları workflow tarafından commit edilir ve
küçük kalmalı; denetim kaydı insan içindir ve git geçmişini şişirmemeli.
"""
from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DENETIM_YOLU = Path(os.environ.get("DENETIM_YOLU", "bobi_tv/logs/denetim.jsonl"))

#: Satır sayısı bu eşiği geçince dosya döndürülür (tek yedek tutulur).
AZAMI_SATIR = 5000

#: Bu olaylar GERİ ALINAMAZ → kayıt zorunlu (çağıran atlarsa test yakalar).
GERI_ALINAMAZ_OLAYLAR = {
    "video_sil",
    "stok_at",
    "uretim_tetikle",
    "ayar_degistir",
    "force_uret",
}

#: Kayıtta asla görünmemesi gereken anahtar parçaları.
GIZLI_ANAHTARLAR = ("token", "secret", "pat", "cookie", "password", "sifre", "şifre", "key")

MASKE = "***"


def _maskele(veri: Any) -> Any:
    """Sözlük/liste içindeki gizli alanları maskeler (derin kopya üretir)."""
    if isinstance(veri, dict):
        temiz: dict[str, Any] = {}
        for k, v in veri.items():
            if any(g in str(k).lower() for g in GIZLI_ANAHTARLAR):
                temiz[k] = MASKE
            else:
                temiz[k] = _maskele(v)
        return temiz
    if isinstance(veri, list):
        return [_maskele(x) for x in veri]
    return veri


def _satir_sayisi(yol: Path) -> int:
    try:
        with yol.open(encoding="utf-8") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def _dondur(yol: Path) -> None:
    """Eşik aşıldıysa dosyayı `.1` yedeğine taşır (tek yedek, sınırsız büyüme yok)."""
    if _satir_sayisi(yol) < AZAMI_SATIR:
        return
    try:
        yedek = yol.with_suffix(yol.suffix + ".1")
        if yedek.exists():
            yedek.unlink()
        yol.rename(yedek)
    except OSError:
        pass


def kaydet(
    olay: str,
    sonuc: str = "ok",
    kullanici_id: int | str | None = None,
    ayrinti: dict[str, Any] | None = None,
    simdi: datetime | None = None,
    yol: Path | None = None,
) -> bool:
    """Tek denetim satırı yazar. Döner: yazıldı mı?

    Yazma hatası İŞLEMİ DÜŞÜRMEZ (denetim kaydı işlemin önkoşulu değil,
    kanıtıdır) ama çağıran `False` görürse kullanıcıya "kayıt yazılamadı"
    diyebilir.
    """
    yol = yol or DENETIM_YOLU
    simdi = simdi or datetime.now(UTC)
    kayit = {
        "zaman": simdi.isoformat(),
        "olay": str(olay),
        "sonuc": str(sonuc),
        "kullanici_id": kullanici_id if kullanici_id is not None else "bilinmiyor",
        "ayrinti": _maskele(ayrinti or {}),
    }
    try:
        yol.parent.mkdir(parents=True, exist_ok=True)
        _dondur(yol)
        with yol.open("a", encoding="utf-8") as f:
            f.write(json.dumps(kayit, ensure_ascii=False) + "\n")
    except OSError:
        return False
    return True


def oku(azami: int = 20, yol: Path | None = None) -> dict[str, Any]:
    """Son N kaydı okur (en yeni önce). Bozuk satır atlanır ve sayılır."""
    yol = yol or DENETIM_YOLU
    if not yol.exists():
        return {"kayitlar": [], "bozuk": 0, "var": False}
    kayitlar: list[dict[str, Any]] = []
    bozuk = 0
    try:
        satirlar = yol.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {"kayitlar": [], "bozuk": 0, "var": False}
    for satir in satirlar:
        if not satir.strip():
            continue
        try:
            veri = json.loads(satir)
        except ValueError:
            bozuk += 1
            continue
        if isinstance(veri, dict):
            kayitlar.append(veri)
        else:
            bozuk += 1
    return {"kayitlar": kayitlar[::-1][: max(0, azami)], "bozuk": bozuk, "var": True}


def son_kayitlar(azami: int = 10, yol: Path | None = None) -> list[dict[str, Any]]:
    return oku(azami, yol)["kayitlar"]


def ozet(yol: Path | None = None) -> dict[str, Any]:
    """Olay tipine göre sayım (en yeni kayıtlar üzerinden)."""
    kayitlar = oku(10000, yol)["kayitlar"]
    sayim: dict[str, int] = {}
    for k in kayitlar:
        olay = str(k.get("olay") or "bilinmiyor")
        sayim[olay] = sayim.get(olay, 0) + 1
    return {"toplam": len(kayitlar), "olay_sayimi": sayim}


def panel_satiri(kayit: dict[str, Any]) -> str:
    """Tek kaydı panelde gösterilecek tek satıra çevirir (secret yok, kısa)."""
    zaman = str(kayit.get("zaman", ""))[:16].replace("T", " ")
    olay = str(kayit.get("olay", "?"))
    sonuc = str(kayit.get("sonuc", "?"))
    ikon = "✅" if sonuc == "ok" else "⚠️"
    return f"{ikon} {zaman} · {olay} · {sonuc}"


def panel_metni(azami: int = 8, yol: Path | None = None) -> str:
    """📋 Denetim kaydı ekranı — ≈15 satır, uydurma kayıt yok."""
    veri = oku(azami, yol)
    satirlar = ["📋 <b>Denetim Kaydı</b>", ""]
    if not veri["kayitlar"]:
        satirlar.append("Kayıt yok (henüz geri alınamaz işlem yapılmadı).")
        return "\n".join(satirlar)
    for k in veri["kayitlar"]:
        satirlar.append(panel_satiri(k))
    if veri["bozuk"]:
        satirlar.append(f"⚠️ {veri['bozuk']} bozuk satır atlandı.")
    satirlar.append("")
    satirlar.append("<i>Secret değerleri kayda yazılmaz.</i>")
    return "\n".join(satirlar)
