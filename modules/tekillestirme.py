"""BOBİ TV — Callback/update tekilleştirme (TODO 29).

SORUN: Poller uzun süre susup yeniden başladığında Telegram aynı update'i
tekrar teslim edebilir; kullanıcı da aynı düğmeye iki kez hızlıca basabilir.
Sonuç: İKİ üretim tetiklemesi, iki yükleme, iki panel düzenlemesi.

ÇÖZÜM: `update_id` (ve varsa `callback_query.id`) için TTL'li bir "görüldü"
kümesi. Süreç içi (sözlük) tutulur — state dosyası YOK, commit üretmez.

KURALLAR:
- Yalnızca tekrar eden update YUTULUR; ilk geliş her zaman işlenir.
- Pencere (varsayılan 10 dk) dolunca kayıt düşer: bellek sınırsız büyümez.
- Tekilleştirme kararı LOGLANIR (sessiz yutma yok).
"""
from __future__ import annotations

import time
from typing import Any

#: Aynı update'in bu süre içinde tekrar gelmesi "tekrar" sayılır (saniye).
TTL_SN = 600
#: Bellekte tutulacak azami kayıt — taşarsa en eskiler atılır.
AZAMI_KAYIT = 2000

#: anahtar → (ilk görülme zamanı, kaç kez görüldü)
_GORULEN: dict[str, tuple[float, int]] = {}
#: eylem → kilit zamanı ("uçuş" kilidi; aynı işi iki kez başlatmamak için)
_UCUSTA: dict[str, float] = {}


def anahtar(update: dict[str, Any]) -> str:
    """Update için tekilleştirme anahtarı; update_id yoksa callback id'ye düşer."""
    if not isinstance(update, dict):
        return ""
    uid = update.get("update_id")
    if uid is not None:
        return f"u:{uid}"
    cq = update.get("callback_query")
    if isinstance(cq, dict) and cq.get("id"):
        return f"c:{cq['id']}"
    msg = update.get("message")
    if isinstance(msg, dict) and msg.get("message_id"):
        return f"m:{msg['message_id']}"
    return ""


def _temizle(simdi: float) -> None:
    bayat = [k for k, (z, _) in _GORULEN.items() if simdi - z > TTL_SN]
    for k in bayat:
        _GORULEN.pop(k, None)
    if len(_GORULEN) > AZAMI_KAYIT:
        # En eski kayıtları at (sözlük ekleme sırasını korur).
        fazla = len(_GORULEN) - AZAMI_KAYIT
        for k in list(_GORULEN)[:fazla]:
            _GORULEN.pop(k, None)


def tekrar_mi(update: dict[str, Any], simdi: float | None = None) -> bool:
    """True = bu update kısa süre önce İŞLENDİ (yutulmalı).

    İlk gelişte False döner ve kaydı oluşturur.
    """
    simdi = time.time() if simdi is None else simdi
    k = anahtar(update)
    if not k:
        return False
    _temizle(simdi)
    kayit = _GORULEN.get(k)
    if kayit and (simdi - kayit[0]) <= TTL_SN:
        _GORULEN[k] = (kayit[0], kayit[1] + 1)
        return True
    _GORULEN[k] = (simdi, 1)
    # Ekleme sonrası da kırp: sözlük AZAMI_KAYIT'ı aşmasın.
    while len(_GORULEN) > AZAMI_KAYIT:
        _GORULEN.pop(next(iter(_GORULEN)), None)
    return False


def gorulme_sayisi(update: dict[str, Any]) -> int:
    """Kaç kez görüldü (test/log için)."""
    kayit = _GORULEN.get(anahtar(update))
    return kayit[1] if kayit else 0


def sifirla() -> None:
    """Test ve uzun koşu arası temizlik (görülen + uçuş kilitleri)."""
    _GORULEN.clear()
    _UCUSTA.clear()


#: Aynı gerçek işi iki kez başlatmamak için kısa süreli "uçuş" kilidi:
#: tetikleme sürerken gelen ikinci dokunuş bekletilmez, reddedilir.
UCUS_TTL_SN = 120


def ucusa_izin(eylem: str, simdi: float | None = None) -> bool:
    """Eylem şu an 'uçuşta' değilse True döner ve kilidi alır."""
    simdi = time.time() if simdi is None else simdi
    son = _UCUSTA.get(eylem)
    if son is not None and (simdi - son) <= UCUS_TTL_SN:
        return False
    _UCUSTA[eylem] = simdi
    return True


def ucustan_cikar(eylem: str) -> None:
    _UCUSTA.pop(eylem, None)


def ucusta_mi(eylem: str, simdi: float | None = None) -> bool:
    simdi = time.time() if simdi is None else simdi
    son = _UCUSTA.get(eylem)
    return son is not None and (simdi - son) <= UCUS_TTL_SN
