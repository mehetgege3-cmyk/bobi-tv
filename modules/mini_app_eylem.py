"""BOBİ TV — Mini App YAZMA modu (TODO 31 v2 · onaylı yazma).

MİMARİ KARARI (2026-11-11, kullanıcı onayı: "Mini App yazma modunu aç"):

Mini App statik bir sayfadır (GitHub Pages). İçinde PAT/token tutmak, token'ın
tarayıcıda yaşaması demektir → token sızarsa kanal ele geçer. Bu yüzden yazma
şu yolla yapılır ve BAŞKA yolu yoktur:

    Mini App butonu  →  Telegram.WebApp.sendData(JSON)  →  bot poller
                     →  ONAY EKRANI (imzalı + süreli callback)
                     →  uygulama (denetim kaydıyla)

Yani Mini App **hiçbir şeyi doğrudan çalıştırmaz**: yalnız "niyet" gönderir.
Gerçek iş, var olan onay + imza + cool-off + denetim zincirinden geçer.

GÜVENLİK KURALLARI (bu modülde zorlanır):
1. Eylem ADI beyaz listede olmalı (`EYLEMLER`). Bilinmeyen eylem REDDEDİLİR.
2. Payload boyutu sınırlı (`AZAMI_PAYLOAD`) — Telegram `web_app_data` zaten
   ~4 KB ile sınırlı; biz daha da dar tutuyoruz.
3. Payload içinde token/URL/sekme yok: yalnız `{"e": "<eylem>", "v": <sürüm>}`.
4. Her yazma eylemi `onay_gerekli=True` ile işaretli → panel onay ekranı açar.
5. Bilinmeyen/bozuk payload SESSİZCE yutulmaz: kullanıcıya "YAPILMADI" denir.
"""
from __future__ import annotations

import json
from typing import Any

#: Payload sürümü — Mini App ile bot aynı sürümü konuşur.
SURUM = 1

#: Telegram web_app_data pratikte ~4 KB; biz 512 baytta tutuyoruz.
AZAMI_PAYLOAD = 512

BILINMIYOR = "bilinmiyor"

#: Beyaz liste: eylem adı → (etiket, onay_gerekli, panel callback'i, risk).
#: `callback` var olan panel akışına bağlanır; Mini App yeni bir yol AÇMAZ.
EYLEMLER: dict[str, dict[str, Any]] = {
    "uret": {
        "etiket": "Üretimi başlat",
        "onay_gerekli": True,
        "callback": "uret_baslat",
        "risk": "yuksek",
        "aciklama": "Üretim + YouTube yüklemesi başlatır (tavan yok).",
    },
    "render_test": {
        "etiket": "Render testi",
        "onay_gerekli": True,
        "callback": "uret_render_test",
        "risk": "orta",
        "aciklama": "Yükleme YAPMADAN üretim zincirini test eder.",
    },
    "kuyruk_bosalt": {
        "etiket": "Stoğu boşalt",
        "onay_gerekli": True,
        "callback": "kuyruk_at_onay",
        "risk": "yuksek",
        "aciklama": "Stoktaki paketleri archive/atilan'a taşır (geri alınabilir).",
    },
    "durum": {
        "etiket": "Durumu göster",
        "onay_gerekli": False,
        "callback": "menu_main",
        "risk": "dusuk",
        "aciklama": "Salt okuma: panoyu ana ekrana getirir.",
    },
    "denetim": {
        "etiket": "Denetim kaydı",
        "onay_gerekli": False,
        "callback": "denetim_goster",
        "risk": "dusuk",
        "aciklama": "Salt okuma: son geri alınamaz işlemler.",
    },
}


def eylem_listesi() -> list[str]:
    return sorted(EYLEMLER)


def gecerli_mi(eylem: str) -> bool:
    return str(eylem) in EYLEMLER


def onay_gerekli(eylem: str) -> bool:
    """Bilinmeyen eylem GÜVENLİ tarafta kalır: onay gerekli sayılır."""
    kayit = EYLEMLER.get(str(eylem))
    return True if kayit is None else bool(kayit["onay_gerekli"])


def payload_uret(eylem: str) -> str:
    """Mini App'in göndereceği payload (bot tarafı da aynı biçimi üretir/test eder)."""
    return json.dumps({"e": str(eylem), "v": SURUM}, separators=(",", ":"))


def payload_coz(ham: Any) -> tuple[dict[str, Any] | None, str]:
    """Payload'ı doğrular. Döner: (kayıt, sebep). Hata sebebi TÜRKÇE ve açık.

    Reddetme sebepleri: boş, çok büyük, JSON değil, sözlük değil, sürüm uyumsuz,
    eylem beyaz listede yok.
    """
    if ham is None:
        return None, "boş payload"
    if isinstance(ham, (bytes, bytearray)):
        try:
            ham = ham.decode("utf-8")
        except UnicodeDecodeError:
            return None, "payload UTF-8 değil"
    if isinstance(ham, str):
        if not ham.strip():
            return None, "boş payload"
        if len(ham.encode("utf-8")) > AZAMI_PAYLOAD:
            return None, f"payload çok büyük (> {AZAMI_PAYLOAD} bayt)"
        try:
            veri = json.loads(ham)
        except ValueError:
            return None, "payload JSON değil"
    elif isinstance(ham, dict):
        veri = ham
    else:
        return None, "payload biçimi tanınmadı"

    if not isinstance(veri, dict):
        return None, "payload sözlük değil"
    eylem = str(veri.get("e", "")).strip()
    if not eylem:
        return None, "eylem adı yok"
    if not gecerli_mi(eylem):
        return None, f"bilinmeyen eylem: {eylem[:20]}"
    surum = veri.get("v", SURUM)
    if str(surum) != str(SURUM):
        return None, f"sürüm uyumsuz ({surum} ≠ {SURUM})"
    return dict(EYLEMLER[eylem], eylem=eylem), ""


def niyet_metni(kayit: dict[str, Any]) -> str:
    """Onay ekranının ÜSTÜNE eklenen "Mini App'ten geldi" bilgisi."""
    return (
        "📱 <b>Mini App'ten gelen istek</b>\n"
        f"▶️ {kayit['etiket']}\n"
        f"ℹ️ {kayit['aciklama']}\n\n"
        "Aşağıdaki onay ekranından geçmeden HİÇBİR ŞEY çalışmaz."
    )


def red_metni(sebep: str) -> str:
    """Reddedilen payload için dürüst mesaj (sessiz yutma yok)."""
    return (
        "⛔ <b>Mini App isteği uygulanmadı</b>\n"
        f"Sebep: {sebep or BILINMIYOR}\n\n"
        "Hiçbir işlem başlatılmadı."
    )
