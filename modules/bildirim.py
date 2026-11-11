"""BOBİ TV — Akıllı bildirim motoru (TODO 23 + 24, Burak).

Kullanıcı kararı (2026-11-11): "Bot sana yazsın, sen botu aramayasın."
Panel bir kontrol arayüzü; asıl iş bildirimde. Bu modül bildirimi üç
seviyeye ayırır ve kullanıcıyı GEREKSİZ mesajla dövmez.

SEVİYELER
---------
KRİTİK : hemen gönderilir, SESSİZ SAATİ DELER (sistem gerçekten bozuk).
    poller uzun süre sessiz, ardışık yükleme hatası, silme kuralı video
    sildi, secret eksik.
NORMAL : hemen gönderilir, sessiz saatte BEKLER. Yükleme başarılı, kota
    doldu/açıldı.
ÖZET   : hemen GÖNDERİLMEZ; günlük özet saatinde tek mesaja toplanır.
    QC düşüşleri, rutin istatistik, kuyruk durumu.

KURALLAR (mevcut felsefe korunur)
---------------------------------
1. Sessiz saat: varsayılan 00:00–08:00 Europe/Istanbul. KRİTİK deler.
2. Sessiz saatte biriken NORMAL/ÖZET olaylar pencere bitince TEK mesajda
   gelir (N ayrı bildirim spam'i yok).
3. Sustur (`sustur_until`): kullanıcı bilinçli olarak her şeyi keser —
   KRİTİK dahil. Ayarlar SİLİNMEZ, yalnız ertelenir.
4. Saat dilimi sabittir: Europe/Istanbul (kullanıcı Türkiye'de).
5. Secret değeri asla loglanmaz/gösterilmez.

Durum dosyası: bobi_tv/state/bildirim.json — kuyruk + sustur + son özet.
Bu dosya GIT'e commit edilir (workflow arşiv adımı), böylece bir sonraki
koşu bekleyen olayları görür (GitHub Actions her koşuda temiz checkout).
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Istanbul")

DURUM_YOLU = Path(os.environ.get("BILDIRIM_STATE_YOLU", "bobi_tv/state/bildirim.json"))

#: Ayar varsayılanları (state'te yoksa bunlar geçerli).
SESSIZ_BASLANGIC = "00:00"
SESSIZ_BITIS = "08:00"
OZET_SAATI = "09:00"

#: Seviye sabitleri — yazım hatası imkânsız olsun.
KRITIK = "kritik"
NORMAL = "normal"
OZET = "ozet"
SEVIYELER = (KRITIK, NORMAL, OZET)

#: Emoji (panel ile aynı dil).
IKON = {KRITIK: "🔴", NORMAL: "🔔", OZET: "📋"}


# ---------------------------------------------------------------------------
# Durum okuma/yazma
# ---------------------------------------------------------------------------

def durum_oku() -> dict[str, Any]:
    """Bildirim durumu; dosya bozuksa boş yapı döner (çökme yok)."""
    try:
        veri = json.loads(DURUM_YOLU.read_text(encoding="utf-8"))
        if isinstance(veri, dict):
            veri.setdefault("bekleyen", [])
            veri.setdefault("sustur_until", None)
            veri.setdefault("son_ozet", None)
            return veri
    except Exception:
        pass
    return {"bekleyen": [], "sustur_until": None, "son_ozet": None}


def durum_yaz(veri: dict[str, Any]) -> None:
    try:
        DURUM_YOLU.parent.mkdir(parents=True, exist_ok=True)
        DURUM_YOLU.write_text(json.dumps(veri, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[Bildirim] durum yazılamadı: {str(e)[:80]}")


def _saat_parse(metin: str, varsayilan: time) -> time:
    try:
        saat, dakika = str(metin).strip().split(":")[:2]
        return time(int(saat), int(dakika))
    except Exception:
        return varsayilan


def _ayar(ad: str, varsayilan: str) -> str:
    """Ayar değeri: env → state → varsayılan. Uydurma yok."""
    env = os.environ.get(ad, "").strip()
    if env:
        return env
    try:
        depo = Path("bobi_tv/state/ayarlar.json")
        veri = json.loads(depo.read_text(encoding="utf-8"))
        ayarlar = veri.get("ayarlar", veri) if isinstance(veri, dict) else {}
        deger = ayarlar.get(ad)
        if deger is not None and str(deger).strip():
            return str(deger).strip()
    except Exception:
        pass
    return varsayilan


# ---------------------------------------------------------------------------
# Zaman penceresi
# ---------------------------------------------------------------------------

def sessiz_saatte_mi(simdi: datetime | None = None) -> bool:
    """Şu an sessiz saatte miyiz? Gece yarısını aşan aralık desteklenir."""
    simdi = (simdi or datetime.now(UTC)).astimezone(TZ)
    bas = _saat_parse(_ayar("SESSIZ_BASLANGIC", SESSIZ_BASLANGIC), time(0, 0))
    bit = _saat_parse(_ayar("SESSIZ_BITIS", SESSIZ_BITIS), time(8, 0))
    suan = simdi.time()
    if bas == bit:
        return False
    if bas < bit:
        return bas <= suan < bit
    # 22:00–08:00 gibi gece yarısını aşan pencere
    return suan >= bas or suan < bit


def susturulmus_mu(simdi: datetime | None = None) -> bool:
    simdi = simdi or datetime.now(UTC)
    veri = durum_oku()
    bitis = veri.get("sustur_until")
    if not bitis:
        return False
    try:
        return datetime.fromisoformat(str(bitis)) > simdi
    except Exception:
        return False


def sustur(saat: int = 1) -> str:
    """Bildirimleri N saat sustur (ayarlar SİLİNMEZ, ertelenir)."""
    bitis = datetime.now(UTC) + timedelta(hours=saat)
    veri = durum_oku()
    veri["sustur_until"] = bitis.isoformat()
    durum_yaz(veri)
    return bitis.astimezone(TZ).strftime("%H:%M")


def susturu_kaldir() -> None:
    veri = durum_oku()
    veri["sustur_until"] = None
    durum_yaz(veri)


# ---------------------------------------------------------------------------
# Gönderim
# ---------------------------------------------------------------------------

def _gonder(metin: str) -> bool:
    """Gerçek Telegram gönderimi (telegram_notify üzerinden — tek çıkış noktası)."""
    try:
        from modules.telegram_notify import send_message

        return send_message(metin)
    except Exception as e:
        print(f"[Bildirim] gönderim hatası: {str(e)[:100]}")
        return False


def _olay_metni(olay: dict[str, Any]) -> str:
    ikon = IKON.get(str(olay.get("seviye", NORMAL)), "🔔")
    baslik = str(olay.get("baslik", "Bildirim"))
    govde = str(olay.get("govde", "")).strip()
    return f"{ikon} <b>{baslik}</b>" + (f"\n{govde}" if govde else "")


def bildir(
    baslik: str,
    govde: str = "",
    seviye: str = NORMAL,
    simdi: datetime | None = None,
) -> dict[str, str]:
    """Bildirim gönderir veya kuyruğa alır.

    Döner: {"durum": "gonderildi" | "kuyruk" | "susturuldu"} — çağıran
    gerçekten ne olduğunu bilir (sessiz yutma yok).
    """
    simdi = simdi or datetime.now(UTC)
    if seviye not in SEVIYELER:
        seviye = NORMAL

    # Sustur: kullanıcı bilinçli kesti — KRİTİK dahil kuyruğa girer.
    if susturulmus_mu(simdi):
        _kuyruga_ekle(baslik, govde, seviye, simdi)
        return {"durum": "susturuldu"}

    # KRİTİK her zaman anında (sessiz saati deler).
    if seviye == KRITIK:
        _gonder(_olay_metni({"baslik": baslik, "govde": govde, "seviye": seviye}))
        return {"durum": "gonderildi"}

    # Günlük özet olayları: hemen gönderilmez, özet saatini bekler.
    if seviye == OZET:
        _kuyruga_ekle(baslik, govde, seviye, simdi)
        return {"durum": "kuyruk"}

    # NORMAL: sessiz saatte bekler, dışında anında gider.
    if sessiz_saatte_mi(simdi):
        _kuyruga_ekle(baslik, govde, seviye, simdi)
        return {"durum": "kuyruk"}

    # Sessiz saatte birikmiş olanlar da bu bildirimle birlikte gitsin
    # (kullanıcı tek mesaj görsün — "N ayrı bildirim" olmasın).
    birikmis = _kuyruktan_al(seviyeler=(NORMAL,))
    parcalar = [_olay_metni({"baslik": baslik, "govde": govde, "seviye": seviye})]
    if birikmis:
        parcalar.append(_birlesik_metin(birikmis))
    _gonder("\n\n".join(parcalar))
    return {"durum": "gonderildi"}


#: Aynı olay TAZE penceresi (saniye): bu süre içinde birebir aynı başlık tekrar
#: gelirse kuyruğa İKİNCİ kez yazılmaz (kota hatası fırtınasında 50 satır spam'i).
TEKRAR_PENCERESI_SN = 30 * 60


def _kuyruga_ekle(baslik: str, govde: str, seviye: str, simdi: datetime | None = None) -> int:
    """Bekleyen kuyruğa olay ekler. Döner: 1 = eklendi, 0 = tekrar (yutuldu).

    Aynı (başlık, seviye) TAZE penceresi içinde tekrar gelirse yutulur —
    kullanıcı aynı hatayı 50 kez okumaz. Özet metni yine "bekleyen:" der.
    """
    simdi = simdi or datetime.now(UTC)
    veri = durum_oku()
    bekleyen = veri.setdefault("bekleyen", [])
    for o in reversed(bekleyen):
        if str(o.get("baslik", "")) != baslik or str(o.get("seviye", "")) != seviye:
            continue
        try:
            once = datetime.fromisoformat(str(o.get("zaman", "")))
        except (TypeError, ValueError):
            continue
        if once.tzinfo is None:
            once = once.replace(tzinfo=UTC)
        if (simdi - once).total_seconds() <= TEKRAR_PENCERESI_SN:
            return 0
    bekleyen.append(
        {
            "baslik": baslik,
            "govde": govde,
            "seviye": seviye,
            "zaman": simdi.isoformat(),
        }
    )
    # Kuyruğu şişirmemek için en fazla 50 olay tutulur (eskiler düşer).
    veri["bekleyen"] = bekleyen[-50:]
    durum_yaz(veri)
    return 1


def _kuyruktan_al(seviyeler: tuple[str, ...] | None = None) -> list[dict[str, Any]]:
    veri = durum_oku()
    bekleyen = veri.get("bekleyen") or []
    if seviyeler is None:
        alinan, kalan = bekleyen, []
    else:
        alinan = [o for o in bekleyen if o.get("seviye") in seviyeler]
        kalan = [o for o in bekleyen if o.get("seviye") not in seviyeler]
    veri["bekleyen"] = kalan
    durum_yaz(veri)
    return alinan


def _birlesik_metin(olaylar: list[dict[str, Any]]) -> str:
    if not olaylar:
        return ""
    satirlar = [f"📥 <b>Bekleyen {len(olaylar)} bildirim</b>"]
    for o in olaylar[-10:]:  # en fazla 10 satır (Telegram mesaj sınırı)
        satirlar.append(f"• {o.get('baslik', '')}")
    if len(olaylar) > 10:
        satirlar.append(f"… ve {len(olaylar) - 10} tane daha")
    return "\n".join(satirlar)


# ---------------------------------------------------------------------------
# Günlük özet
# ---------------------------------------------------------------------------

def ozet_vakti_mi(simdi: datetime | None = None) -> bool:
    """Özet saati geçti mi ve bugün henüz özet gönderilmedi mi?"""
    simdi = (simdi or datetime.now(UTC)).astimezone(TZ)
    hedef = _saat_parse(_ayar("OZET_SAATI", OZET_SAATI), time(9, 0))
    if simdi.time() < hedef:
        return False
    son = durum_oku().get("son_ozet")
    if not son:
        return True
    try:
        return datetime.fromisoformat(str(son)).astimezone(TZ).date() < simdi.date()
    except Exception:
        return True


def gunluk_ozet_gonder(simdi: datetime | None = None) -> dict[str, Any]:
    """Günlük özeti gönderir (bekleyen ÖZET/NORMAL olayları toplar)."""
    simdi = simdi or datetime.now(UTC)
    bekleyen = _kuyruktan_al(seviyeler=(OZET, NORMAL))

    uretilen, yayinda = _gunun_sayilari(simdi)
    kuyruk = _kuyruk_sayisi()
    satirlar = [
        "📋 <b>BOBİ TV — Günlük Özet</b>",
        f"🎥 Dün/bugün üretilen: {uretilen}",
        f"🚀 Yayında: {yayinda}",
        f"📦 Stokta bekleyen: {kuyruk}",
    ]
    if bekleyen:
        satirlar.append("")
        satirlar.append(f"<b>Bekleyen olaylar ({len(bekleyen)}):</b>")
        for o in bekleyen[-8:]:
            satirlar.append(f"• {IKON.get(str(o.get('seviye')), '•')} {o.get('baslik', '')}")
    else:
        satirlar.append("")
        satirlar.append("✅ Bekleyen uyarı yok.")

    metin = "\n".join(satirlar)
    gonderildi = _gonder(metin)
    if gonderildi:
        veri = durum_oku()
        veri["son_ozet"] = simdi.isoformat()
        durum_yaz(veri)
    return {"gonderildi": gonderildi, "olay_sayisi": len(bekleyen), "metin": metin}


def _gunun_sayilari(simdi: datetime) -> tuple[int, int]:
    arsiv = Path("bobi_tv/archive/videos.json")
    gun = simdi.astimezone(TZ).strftime("%Y-%m-%d")
    try:
        veri = json.loads(arsiv.read_text(encoding="utf-8"))
        kayitlar = list(veri.values()) if isinstance(veri, dict) else list(veri)
        bugun = [k for k in kayitlar if str(k.get("tarih", ""))[:10] == gun]
        return len(bugun), sum(1 for k in bugun if k.get("durum") == "yayinda")
    except Exception:
        return 0, 0


def _kuyruk_sayisi() -> int:
    kuyruk = Path("bobi_tv/queue")
    try:
        return len(list(kuyruk.glob("*.json")))
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Tur başına tek giriş noktası (workflow çağırır)
# ---------------------------------------------------------------------------

def tur_bildirimleri(simdi: datetime | None = None) -> dict[str, Any]:
    """Her koşunun sonunda çağrılır: sessiz saat bittiyse birikmişleri
    boşaltır, özet saati geldiyse günlük özeti gönderir."""
    simdi = simdi or datetime.now(UTC)
    sonuc: dict[str, Any] = {"birikmis_gonderildi": 0, "ozet": False}

    if susturulmus_mu(simdi):
        return sonuc

    # Sessiz saat bitti ve bekleyen NORMAL olaylar var → TEK mesaj.
    if not sessiz_saatte_mi(simdi):
        bekleyen = _kuyruktan_al(seviyeler=(NORMAL,))
        if bekleyen:
            _gonder("📥 <b>Gece biriken bildirimler</b>\n\n" + _birlesik_metin(bekleyen).split("\n", 1)[-1])
            sonuc["birikmis_gonderildi"] = len(bekleyen)

    if ozet_vakti_mi(simdi):
        ozet = gunluk_ozet_gonder(simdi)
        sonuc["ozet"] = ozet["gonderildi"]

    return sonuc
