"""Notebook kaydı — hattın açtığı defterleri hatırlar.

NİÇİN: Otomatik silme yalnızca **hattın kendi açtığı** defterlere dokunmalı.
Kullanıcının kendi eliyle açtığı eski defterler KORUNUR (kullanıcı kararı
2026-11-08: "otomatik silme olsun ama benim eski defterlerime dokunmadan").

YÖNTEM: Her yeni defter bu dosyaya yazılır. Silme aracı SADECE bu listedeki
kimlikleri siler. Listede olmayan bir defter — ne kadar eski olursa olsun —
asla silinmez. Böylece "yanlış defteri uçurma" riski kalkar.

DOSYA: bobi_tv/state/notebook_kayit.json — repoya commit edilir (CI'da
koşular arası hafıza). Silinen kayıtlar listeden düşer.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

KAYIT = (Path(__file__).resolve().parent.parent
         / "bobi_tv" / "state" / "notebook_kayit.json")


def _oku() -> list[dict]:
    try:
        veri = json.loads(KAYIT.read_text(encoding="utf-8"))
    except Exception:
        return []
    return veri if isinstance(veri, list) else veri.get("defterler", [])


def _yaz(kayitlar: list[dict]) -> None:
    KAYIT.parent.mkdir(parents=True, exist_ok=True)
    KAYIT.write_text(json.dumps(kayitlar, ensure_ascii=False, indent=1),
                     encoding="utf-8")


def kaydet(defter_id: str, baslik: str, durum: str = "olusturuldu") -> None:
    """Yeni defteri kayda geçir. Aynı kimlik varsa günceller (tekrar yazmaz)."""
    if not defter_id:
        return
    kayitlar = _oku()
    for k in kayitlar:
        if k.get("id") == defter_id:
            k["durum"] = durum
            k["guncelleme"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            _yaz(kayitlar)
            return
    kayitlar.append({
        "id": defter_id,
        "baslik": baslik,
        "durum": durum,
        "tarih": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
    _yaz(kayitlar)
    print(f"[kayıt] defter kaydedildi: {defter_id}")


def silindi(defter_id: str) -> None:
    """Silinen defteri listeden düşür."""
    kayitlar = [k for k in _oku() if k.get("id") != defter_id]
    _yaz(kayitlar)


def kayitlilar() -> list[dict]:
    return _oku()


def sayi() -> int:
    return len(_oku())
