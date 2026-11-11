"""BOBİ TV — Render testi CANLI kart (TODO 21, Kaan).

AMAÇ: "🧪 Render testi" düğmesine basan kullanıcı 2-4 dakika boyunca kör
kalmasın. Kart, GitHub Actions koşusunun GERÇEK durumunu gösterir:

    ⏳ Sırada → 🔄 Çalışıyor (dk) → ✅ Tamamlandı / ❌ Başarısız

KURALLAR (değişmez):
- Uydurma ilerleme yüzdesi YOK. Yüzde yalnızca GitHub'ın `steps` dizisinden
  hesaplanır; adım bilgisi yoksa "bilinmiyor" yazılır.
- Kart, panelin TEK MESAJ kuralına uyar: edit-in-place ile güncellenir
  (`panel_goster`), yeni mesaj üretmez.
- GitHub okunamaz / token yok / koşu bulunamaz → dürüst mesaj, panel çökmez.
- Disk kirliliği yok: durum `bobi_tv/state/render_test.json`'da tutulur
  (kuyruk/arşiv dosyalarına dokunulmaz).
"""
from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

#: Kart durumunun tutulduğu dosya (repo state dizini).
DURUM_YOLU = Path("bobi_tv/state/render_test.json")

BILINMIYOR = "bilinmiyor"

#: GitHub koşu durumu → kullanıcıya gösterilecek metin.
DURUM_METNI: dict[str, str] = {
    "queued": "⏳ Sırada",
    "in_progress": "🔄 Çalışıyor",
    "completed": "✅ Tamamlandı",
    "waiting": "⏳ Sırada",
    "requested": "⏳ Sırada",
    "pending": "⏳ Sırada",
}
SONUC_METNI: dict[str, str] = {
    "success": "✅ Başarılı",
    "failure": "❌ Başarısız",
    "cancelled": "⚪ İptal",
    "skipped": "⚪ Atlandı",
    "timed_out": "⌛ Zaman aşımı",
    "action_required": "⚠️ Müdahale gerekli",
}
#: Bu durumlarda kart artık "canlı" değildir (yenileme gerekmez).
BITMIS_DURUMLAR = {"completed"}


def simdi_utc() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Yerel durum dosyası (koşu kimliği + başlangıç zamanı)
# ---------------------------------------------------------------------------


def durum_yaz(veri: dict[str, Any], yol: Path | None = None) -> bool:
    """Kart durumunu yazar. Yazamazsa False (çağıran dürüst mesaj verir)."""
    yol = yol or DURUM_YOLU
    try:
        yol.parent.mkdir(parents=True, exist_ok=True)
        yol.write_text(json.dumps(veri, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except OSError:
        return False


def durum_oku(yol: Path | None = None) -> dict[str, Any]:
    """Kart durumunu okur; dosya yok/bozuksa boş sözlük (çökme yok)."""
    yol = yol or DURUM_YOLU
    try:
        veri = json.loads(yol.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return veri if isinstance(veri, dict) else {}


def tetikleme_kaydet(simdi: datetime | None = None, yol: Path | None = None, **ek: Any) -> dict[str, Any]:
    """Render testi tetiklendiğinde çağrılır: zaman damgası + yükleme yok işareti."""
    simdi = simdi or simdi_utc()
    veri = {
        "tetiklendi": simdi.isoformat(),
        "yukleme_atla": True,
        "durum": "tetiklendi",
        **ek,
    }
    durum_yaz(veri, yol)
    return veri


# ---------------------------------------------------------------------------
# GitHub koşu verisinden kart üretimi (saf fonksiyonlar — test edilebilir)
# ---------------------------------------------------------------------------


def _iso(ham: Any) -> datetime | None:
    if not ham:
        return None
    try:
        d = datetime.fromisoformat(str(ham).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return d if d.tzinfo else d.replace(tzinfo=UTC)


def gecen_sure_dk(kosu: dict[str, Any], simdi: datetime | None = None) -> int | None:
    """Koşunun süresi (dk): bitmişse start→updated, sürüyorsa start→şimdi."""
    simdi = simdi or simdi_utc()
    bas = _iso(kosu.get("run_started_at") or kosu.get("created_at"))
    if bas is None:
        return None
    if str(kosu.get("status")) in BITMIS_DURUMLAR:
        bit = _iso(kosu.get("updated_at"))
        if bit is None:
            return None
        return max(0, int((bit - bas).total_seconds() // 60))
    return max(0, int((simdi - bas).total_seconds() // 60))


def ilerleme(kosu: dict[str, Any]) -> dict[str, Any]:
    """Adım sayacı: kaç adım bitti / toplam. Bilinmiyorsa None (uydurma yok).

    GitHub `steps` dizisi yalnız koşu detayında gelir; yoksa yüzde ÜRETİLMEZ.
    """
    adimlar = kosu.get("steps")
    if not isinstance(adimlar, list) or not adimlar:
        return {"biliniyor": False, "biten": None, "toplam": None, "yuzde": None}
    toplam = len(adimlar)
    biten = sum(1 for a in adimlar if isinstance(a, dict) and a.get("status") == "completed")
    return {
        "biliniyor": True,
        "biten": biten,
        "toplam": toplam,
        "yuzde": int(round(biten / toplam * 100)) if toplam else None,
    }


def _cubuk(yuzde: int | None, genislik: int = 10) -> str:
    if yuzde is None:
        return ""
    dolu = int(round(yuzde / 100 * genislik))
    return "▰" * dolu + "▱" * (genislik - dolu)


def kart_metni(kosu: dict[str, Any] | None, simdi: datetime | None = None, hata: str = "") -> str:
    """Canlı kart metni. Her durumda dürüst: bilinmeyen sayı yazılmaz."""
    satirlar = ["🧪 <b>Render testi (canlı)</b>", ""]
    if not kosu:
        satirlar.append(f"⛔ Koşu bilgisi okunamadı: {hata or BILINMIYOR}")
        satirlar.append("")
        satirlar.append("✅ YouTube'a <b>yükleme yapılmadı</b> — test koşusu (canlı kanal etkilenmez).")
        return "\n".join(satirlar)

    durum = str(kosu.get("status") or "")
    sonuc = str(kosu.get("conclusion") or "")
    satirlar.append(f"Durum: {DURUM_METNI.get(durum, durum or BILINMIYOR)}")
    if sonuc:
        satirlar.append(f"Sonuç: {SONUC_METNI.get(sonuc, sonuc)}")

    sure = gecen_sure_dk(kosu, simdi)
    satirlar.append(f"⏱️ Süre: {sure} dk" if sure is not None else f"⏱️ Süre: {BILINMIYOR}")

    il = ilerleme(kosu)
    if il["biliniyor"]:
        cubuk = _cubuk(il["yuzde"])
        satirlar.append(
            f"📊 Adım: {il['biten']}/{il['toplam']} <code>{cubuk}</code> (%{il['yuzde']})"
        )
    else:
        satirlar.append(f"📊 Adım: {BILINMIYOR} (adım bilgisi gelmedi — yüzde uydurulmaz)")

    numara = kosu.get("run_number")
    if numara:
        satirlar.append(f"🔢 Koşu: #{numara}")
    satirlar.append("")
    satirlar.append("✅ YouTube'a <b>yükleme yapılmadı</b> — test koşusu.")
    if durum not in BITMIS_DURUMLAR:
        satirlar.append("<i>Kart 30 sn'de bir '🔄 Yenile' ile tazelenir.</i>")
    else:
        satirlar.append("<i>Koşu bitti — sonuç yukarıda.</i>")
    return "\n".join(satirlar)


def canli_mi(kosu: dict[str, Any] | None) -> bool:
    """Kart hâlâ canlı mı (yenileme düğmesi anlamlı mı)?"""
    if not kosu:
        return False
    return str(kosu.get("status") or "") not in BITMIS_DURUMLAR


def kosu_ozeti(kosu: dict[str, Any] | None) -> dict[str, Any]:
    """Kısa makine-okur özet (log/test için)."""
    if not kosu:
        return {"var": False}
    return {
        "var": True,
        "id": kosu.get("id"),
        "numara": kosu.get("run_number"),
        "durum": kosu.get("status"),
        "sonuc": kosu.get("conclusion"),
        "url": kosu.get("html_url"),
        "yukleme_atla": bool(os.environ.get("YUKLEME_ATLA") == "1") or None,
    }
