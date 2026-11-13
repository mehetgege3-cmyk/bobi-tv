"""BOBİ TV — Arena çerezi uyarısı (TODO dosyası madde 3 = Seçenek C).

SEÇENEK C NEDİR
---------------
Çerez düştüğünde (smoke test exit 2 / verdict `oturum-gecersiz`) SİSTEM
HİÇBİR ŞEYİ OTOMATİK DEĞİŞTİRMEZ: secret yazmaz, tarayıcı açmaz. Yalnız
Telegram'dan "çerezi yenile" uyarısı gönderir ve 30 dakikada bir tekrarlar
(spam yok). Yenileme işini kullanıcı elle yapar.

NEDEN BÖYLE
-----------
Seçenek B (GitHub App ile `gh secret set`) daha "otomatik" görünür ama
pipeline'ın yazdığı çerezi okuyabildiğini kanıtlayan bir format testi yok;
yanlış format yazmak çalışan bir secret'ı bozar. Ayrıca secret yazma izni
kaza riskini büyütür. Önce ölçüm + uyarı, sonra (istenirse) B.

KURALLAR
--------
- Uyarı METNİNDE çerez/token YOK (yalnız verdict + zaman).
- Aynı uyarı 30 dakikada bir defadan sık gönderilmez (state'te damga tutulur).
- Bildirim susturulmuşsa (mevcut `modules.bildirim.susturulmus_mu`) uyarı
  gönderilmez — kullanıcı susturduysa susar.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

STATE = Path("bobi_tv/state/arena_cerez_uyari.json")

#: Aynı uyarılar arasındaki en kısa süre (dakika).
TEKRAR_ARALIGI_DK = 30

#: Kullanıcıya gösterilen eylem adımları (doküman: docs/GITHUB_APP_TOKEN.md
#: değil — çerez yenileme adımları README/Cerez bölümünde).
ADIMLAR = [
    "1) Tarayıcıda arena.ai'ye gir (oturum açık olsun)",
    "2) Cookie-Editor → Export → JSON kopyala",
    "3) GitHub → Settings → Secrets → ARENA_COOKIES_JSON → güncelle",
    "4) Actions → Arena Smoke Test → Run workflow → exit 0 gör",
]


def _oku() -> dict[str, Any]:
    try:
        return dict(json.loads(STATE.read_text(encoding="utf-8")))
    except Exception:
        return {}


def _yaz(veri: dict[str, Any]) -> bool:
    try:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(veri, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception:
        return False


def uyari_gerekli_mi(verdict: str, simdi: datetime | None = None) -> tuple[bool, str]:
    """Bu verdict için uyarı gönderilmeli mi? (True, sebep) / (False, sebep)."""
    simdi = simdi or datetime.now(UTC)
    if verdict not in {"oturum-gecersiz", "cookie-yapilandirma-hatasi"}:
        return False, f"uyarı gerektiren verdict değil: {verdict or 'yok'}"

    durum = _oku()
    if durum.get("verdict") != verdict:
        return True, "yeni durum"
    try:
        onceki = datetime.fromisoformat(str(durum.get("zaman")))
    except Exception:
        return True, "önceki damga okunamadı"
    fark = simdi - onceki
    if fark >= timedelta(minutes=TEKRAR_ARALIGI_DK):
        return True, f"son uyarıdan {int(fark.total_seconds() // 60)} dk geçti"
    kalan = TEKRAR_ARALIGI_DK - int(fark.total_seconds() // 60)
    return False, f"tekrar aralığı dolmadı ({kalan} dk kaldı)"


def uyari_metni(verdict: str, zaman: datetime | None = None) -> str:
    """Telegram'a gidecek metin — çerez/token İÇERMEZ."""
    zaman = zaman or datetime.now(UTC)
    baslik = (
        "⛔ <b>Arena oturumu düştü</b>"
        if verdict == "oturum-gecersiz"
        else "⚠️ <b>Arena çerezi yapılandırma hatası</b>"
    )
    return "\n".join(
        [
            baslik,
            f"│ Tespit: {zaman.strftime('%Y-%m-%d %H:%M')} UTC",
            f"│ Tanılama sonucu: <code>{verdict}</code>",
            "",
            "<b>Ne yapmalı:</b>",
            *ADIMLAR,
            "",
            "<i>Otomatik secret yazma YOK — çerez yalnızca senin elinle değişir.</i>",
        ]
    )


def uyari_gonder(verdict: str, simdi: datetime | None = None, gonderici: Any = None) -> dict[str, Any]:
    """Gerekliyse Telegram uyarısı gönderir. Döner: sonuç sözlüğü (dürüst)."""
    simdi = simdi or datetime.now(UTC)
    gerekli, sebep = uyari_gerekli_mi(verdict, simdi)
    if not gerekli:
        return {"gonderildi": False, "sebep": sebep}

    # Susturma saygı görür (kullanıcı kararı).
    try:
        from modules.bildirim import susturulmus_mu

        if susturulmus_mu():
            return {"gonderildi": False, "sebep": "bildirimler susturulmuş"}
    except Exception:
        pass

    if gonderici is None:
        from modules.telegram_notify import send_message

        gonderici = send_message
    metin = uyari_metni(verdict, simdi)
    try:
        ok = bool(gonderici(metin))
    except Exception as e:
        return {"gonderildi": False, "sebep": f"gönderim hatası: {str(e)[:80]}"}
    if not ok:
        return {"gonderildi": False, "sebep": "Telegram gönderimi başarısız"}

    _yaz({"verdict": verdict, "zaman": simdi.isoformat(), "metin_ozeti": metin.splitlines()[0]})
    return {"gonderildi": True, "sebep": sebep}


if __name__ == "__main__":
    import sys

    verdict = sys.argv[1] if len(sys.argv) > 1 else ""
    sonuc = uyari_gonder(verdict)
    print(f"[ÇerezUyarı] {json.dumps(sonuc, ensure_ascii=False)}")
