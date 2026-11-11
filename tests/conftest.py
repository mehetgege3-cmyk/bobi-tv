"""Test ortamı izolasyonu (2026-11-11).

NEDEN: Bazı testler panel fonksiyonlarını çağırıyor; bu fonksiyonlar kendi
varsayılan YOL sabitlerini kullanırsa GERÇEK `bobi_tv/state/` dosyalarını
kirletiyordu (ölçüldü: `uretim_iptal.json`, `render_test.json` test koşusunda
oluştu). Kirli state = canlı panelde yanlış "İptal (9 dk)" düğmesi.

ÇÖZÜM: Testler başlamadan tüm state/log yolları geçici dizine çevrilir.
Modüller `Path` sabitlerini import sırasında okuduğu için bu env ayarı
conftest'te (modül import'undan ÖNCE) yapılır.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

_GECICI = Path(tempfile.mkdtemp(prefix="bobi-test-"))

#: Panelin kendi yol sabitleri import sırasında sabitleniyor; her testte
#: otomatik olarak geçici dizine çevrilir (gerçek state'e yazma YOK).
_IZOLE_EDILECEK = (
    "AYARLAR_STATE_YOLU",
    "GECMIS_YOLU",
    "BEKLEYEN_YOLU",
    "MENU_STATE_YOLU",
    "KOTA_YOLU",
)


def pytest_configure(config):  # noqa: ARG001
    """Modüller import edildikten sonra yol sabitlerini geçici dizine yönlendir."""
    import modules.telegram_bot as tb

    for ad in _IZOLE_EDILECEK:
        if hasattr(tb, ad):
            setattr(tb, ad, _GECICI / f"{ad.lower()}.json")
    # Denetim/kuyruk modülleri de kendi yollarını sabitleyebilir.
    import modules.denetim as dn
    import modules.render_karti as rk

    dn.DENETIM_YOLU = _GECICI / "denetim.jsonl"
    rk.DURUM_YOLU = _GECICI / "render_test.json"

for _ad, _yol in {
    "BILDIRIM_STATE_YOLU": _GECICI / "bildirim.json",
    "DENETIM_YOLU": _GECICI / "denetim.jsonl",
    "BOBI_COOLDOWN_YOLU": _GECICI / "uretim_cooldown.json",
    "BOBI_IPTAL_YOLU": _GECICI / "uretim_iptal.json",
}.items():
    os.environ[_ad] = str(_yol)
