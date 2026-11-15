"""NotebookLM defter temizliği — SADECE hattın açtığı defterler.

KULLANICI KARARI (2026-11-08):
    "otomatik silme olsun ama benim eski defterlere dönmeden"

Yani: hattın ürettiği defterler otomatik silinir; kullanıcının kendi eliyle
açtığı 22 eski deftere DOKUNULMAZ.

GÜVENLİK — üç kilit:
  1. **Kayıt listesi**: yalnız `bobi_tv/state/notebook_kayit.json` içindeki
     kimlikler adaydır. Listede olmayan defter asla silinmez.
  2. **Yaş**: kayıttan en az `MIN_SAAT` saat geçmiş olmalı (yanlışlıkla yeni
     üretilmiş defteri uçurmamak için).
  3. **Korunan kimlikler**: `bobi_tv/state/notebook_korunan.json` — elle
     eklenen kimlikler her zaman korunur.

Kota: NotebookLM API'si toplu silme sunmuyor; her defter tek tek siliniyor.
Bu yüzden tur başına en fazla `TUR_TAVANI` defter silinir.

KULLANIM:
    python3 tools/notebook_temizle.py --kuru      # ne silinecek, gösterecek
    python3 tools/notebook_temizle.py             # gerçekten sil
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import notebook_kayit as kayit  # noqa: E402

#: Bu saatten yeni defter silinmez.
MIN_SAAT = 24

#: Bir koşuda en fazla kaç defter silinir (API'yi yormamak için).
TUR_TAVANI = 15

#: Korunan defter kimlikleri (elle eklenir).
KORUNAN = (Path(__file__).resolve().parent.parent
           / "bobi_tv" / "state" / "notebook_korunan.json")


def _korunan() -> set[str]:
    try:
        veri = json.loads(KORUNAN.read_text(encoding="utf-8"))
        return set(veri if isinstance(veri, list) else veri.get("idler", []))
    except Exception:
        return set()


def _yas_saat(iso: str) -> float:
    try:
        t = datetime.fromisoformat(iso)
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - t).total_seconds() / 3600
    except Exception:
        return 0.0


def adaylar() -> tuple[list[dict], list[dict]]:
    """(silinecekler, korunanlar) — karar gerekçeleriyle."""
    korunan_id = _korunan()
    sil, tut = [], []
    for k in kayit.kayitlilar():
        d_id = k.get("id")
        if not d_id:
            continue
        yas = _yas_saat(k.get("tarih", ""))
        if d_id in korunan_id:
            tut.append({**k, "sebep": "korunan listesinde"})
        elif yas < MIN_SAAT:
            tut.append({**k, "sebep": f"çok yeni ({yas:.1f} sa < {MIN_SAAT} sa)"})
        else:
            sil.append({**k, "yas_saat": round(yas, 1)})
    sil.sort(key=lambda x: x.get("tarih", ""))          # en eski önce
    return sil[:TUR_TAVANI], tut


def _kimlik_kur() -> None:
    """Hat ile aynı kimlik kurulumu (master token veya tazelenmiş çerez)."""
    from tools.notebook_video import _depo_hazirla

    taze = Path("/tmp/nb_state.json")
    if taze.exists():
        try:
            if json.loads(taze.read_text(encoding="utf-8")).get("cookies"):
                os.environ["NOTEBOOKLM_AUTH_JSON"] = taze.read_text(encoding="utf-8")
                return
        except Exception:
            pass
    profil = (Path(os.environ.get("NOTEBOOKLM_HOME") or (Path.home() / ".notebooklm"))
              / "profiles" / (os.environ.get("NOTEBOOKLM_PROFILE") or "default")
              / "storage_state.json")
    if profil.exists():
        os.environ["NOTEBOOKLM_AUTH_JSON"] = profil.read_text(encoding="utf-8")
        return
    os.environ["NOTEBOOKLM_AUTH_JSON"] = json.dumps(_depo_hazirla())


def calistir(kuru: bool = False) -> dict:
    sil, tut = adaylar()
    rapor = {"silinecek": sil, "korunan": len(tut), "silinen": [], "hata": None}
    print(f"→ kayıtlı defter: {kayit.sayi()} | silinecek: {len(sil)} | "
          f"korunan: {len(tut)}")
    for s in sil:
        print(f"   • {s['id'][:8]}  {s.get('baslik', '')[:45]}  "
              f"({s['yas_saat']} sa)")
    if kuru or not sil:
        if kuru:
            print("(kuru koşu — hiçbir şey silinmedi)")
        return rapor

    _kimlik_kur()
    from notebooklm import NotebookLMClient
    import asyncio

    async def _sil() -> list[str]:
        gitti = []
        async with NotebookLMClient.from_storage() as c:
            for s in sil:
                try:
                    await c.notebooks.delete(s["id"])
                    kayit.silindi(s["id"])
                    gitti.append(s["id"])
                    print(f"   🗑️ silindi: {s['id'][:8]} {s.get('baslik','')[:40]}")
                except Exception as e:
                    print(f"   ⚠️ silinemedi {s['id'][:8]}: "
                          f"{type(e).__name__}: {e}")
        return gitti

    try:
        rapor["silinen"] = asyncio.run(_sil())
    except Exception as e:
        rapor["hata"] = f"{type(e).__name__}: {e}"
    return rapor


def main() -> int:
    ap = argparse.ArgumentParser(description="Hat defterlerini temizle")
    ap.add_argument("--kuru", action="store_true")
    a = ap.parse_args()

    if not os.environ.get("NOTEBOOKLM_AUTH_JSON") and not (
            os.environ.get("NOTEBOOK_GOOGLE")
            or os.environ.get("NOTEBOOKLM_MASTER_TOKEN_JSON")):
        print("❌ kimlik yok (NOTEBOOK_GOOGLE / NOTEBOOKLM_MASTER_TOKEN_JSON)")
        return 2

    r = calistir(a.kuru)
    print(json.dumps({k: (len(v) if isinstance(v, list) else v)
                      for k, v in r.items()}, ensure_ascii=False))
    return 0 if not r.get("hata") else 1


if __name__ == "__main__":
    sys.exit(main())
