"""BOBİ TV — Stok (kuyruk) yönetimi + kuyruk ekranı (TODO 20, Kaan).

AMAÇ: Kuyruk artık bir "kara kutu" değil. Panelden görülür, sebebe göre
ayrılır, tek tek veya toplu atılabilir; hiçbir işlem ONAYSIZ yıkıcı değildir
ve hiçbir sayı uydurulmaz (okunamayan dosya "bilinmiyor" olur).

KURALLAR (değişmez):
- Yalnızca `bobi_tv/queue/*.json` okunur/yazılır; `videos.json`'a kuyruk
  durumu YAZILMAZ (orada sadece geçerli video kaydı olur).
- Silme iki aşamalıdır: plan (yalnız OKUR) → uygula (dosyayı `arsiv/atilan/`
  altına TAŞIR, geri alınabilir; diskten kalıcı silme YOK).
- Secret/URL/token panelde gösterilmez.

Kota notu (2026-11-11): günlük yükleme tavanı YOK. Kuyruk yalnızca YouTube'un
KENDİ 403 quotaExceeded hatasında (veya geçici/kalıcı yükleme hatasında) oluşur.
"""
from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

#: Kuyruk dizini (pipeline ile aynı yol).
KUYRUK_DIZINI = Path("bobi_tv/queue")
#: Atılan kayıtların gittiği dizin (geri alınabilir çöp kutusu).
ATILAN_DIZINI = Path("bobi_tv/archive/atilan")

BILINMIYOR = "bilinmiyor"

#: Stok sebebi → kullanıcıya gösterilecek kısa etiket.
SEBEP_ETIKETI: dict[str, str] = {
    "kota": "🚫 YouTube kotası",
    "gecici": "🔁 Geçici hata",
    "kalici": "⛔ Kalıcı hata",
    "": BILINMIYOR,
}

#: Bir kaydın "bayat" sayılması için varsayılan yaş (gün). Kendi kendine
#: kaybolmaz; yalnız uyarı verir (veri kaybı yok).
BAYAT_GUN = 7

#: Toplu işlemde tek seferde dokunulacak azami kayıt (panel yavaşlamasın).
TOPLU_AZAMI = 50


def _sebep_normalize(ham: Any) -> str:
    """Bilinmeyen/boş sebep → "" (ekranda 'bilinmiyor' yazar, sayı uydurulmaz)."""
    s = str(ham or "").strip().lower()
    return s if s in SEBEP_ETIKETI else ""


def _deneme_sayisi(ham: Any) -> int:
    try:
        return max(0, int(ham))
    except (TypeError, ValueError):
        return 0


def _olusturuldu(ham: Any) -> datetime | None:
    """ISO damgasını UTC datetime'a çevirir; okunamazsa None (uydurma yok)."""
    if not ham:
        return None
    try:
        d = datetime.fromisoformat(str(ham).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return d if d.tzinfo else d.replace(tzinfo=UTC)


def _yas_gun(olusturuldu: datetime | None, simdi: datetime) -> int | None:
    if olusturuldu is None:
        return None
    return max(0, int((simdi - olusturuldu).total_seconds() // 86400))


def _video_var_mi(yol: Any) -> bool | None:
    """MP4 diskte duruyor mu? Yolu boşsa None (bilinmiyor — uydurma yok)."""
    s = str(yol or "").strip()
    if not s:
        return None
    try:
        return Path(s).exists()
    except OSError:
        return None


def kayitlari_oku(simdi: datetime | None = None) -> dict[str, Any]:
    """Kuyruktaki TÜM paketleri okur (yalnız okuma — hiçbir şey silmez/taşımaz).

    Döner:
        {"kayitlar": [...], "bozuk": [dosya adları], "dizin_var": bool,
         "simdi": datetime}

    Her kayıt: dosya_adi, baslik, sebep, deneme, yas_gun, video_var,
    kategori, olusturuldu, dosya_yolu. Bozuk JSON kaydı silinmez; adı
    `bozuk` listesine düşer ve panelde görünür.
    """
    simdi = simdi or datetime.now(UTC)
    kayitlar: list[dict[str, Any]] = []
    bozuk: list[str] = []
    if not KUYRUK_DIZINI.exists():
        return {"kayitlar": [], "bozuk": [], "dizin_var": False, "simdi": simdi}

    for dosya in sorted(KUYRUK_DIZINI.glob("*.json")):
        try:
            veri = json.loads(dosya.read_text(encoding="utf-8"))
            if not isinstance(veri, dict):
                raise ValueError("kayıt sözlük değil")
        except Exception:
            bozuk.append(dosya.stem)
            continue
        olusturuldu = _olusturuldu(veri.get("olusturuldu"))
        kayitlar.append(
            {
                "dosya_adi": str(veri.get("dosya_adi") or dosya.stem),
                "baslik": str(veri.get("baslik") or BILINMIYOR),
                "sebep": _sebep_normalize(veri.get("stok_sebep")),
                "deneme": _deneme_sayisi(veri.get("deneme")),
                "yas_gun": _yas_gun(olusturuldu, simdi),
                "video_var": _video_var_mi(veri.get("final_video")),
                "kategori": str(veri.get("kategori") or ""),
                "olusturuldu": olusturuldu,
                "dosya_yolu": dosya,
            }
        )
    return {"kayitlar": kayitlar, "bozuk": bozuk, "dizin_var": True, "simdi": simdi}


def ozet(simdi: datetime | None = None) -> dict[str, Any]:
    """Sayısal özet: toplam, sebebe göre dağılım, bayat/boş-video sayısı."""
    veri = kayitlari_oku(simdi)
    kayitlar = veri["kayitlar"]
    sebep_dagilimi: dict[str, int] = {}
    for k in kayitlar:
        anahtar = k["sebep"] or "bilinmiyor"
        sebep_dagilimi[anahtar] = sebep_dagilimi.get(anahtar, 0) + 1
    bayat = [k for k in kayitlar if (k["yas_gun"] or 0) >= BAYAT_GUN]
    mpsiz = [k for k in kayitlar if k["video_var"] is False]
    return {
        "toplam": len(kayitlar),
        "sebep_dagilimi": sebep_dagilimi,
        "bayat": len(bayat),
        "video_yok": len(mpsiz),
        "bozuk": len(veri["bozuk"]),
        "kayitlar": kayitlar,
        "simdi": veri["simdi"],
    }


def _guvenli_dosya(kayit: Any) -> Path | None:
    """Kaydın YOLUNU doğrular: kuyruk dizininde ve .json olmalı (path traversal yok)."""
    yol = kayit.get("dosya_yolu") if isinstance(kayit, dict) else kayit
    if not isinstance(yol, Path):
        yol = Path(str(yol))
    try:
        kok = KUYRUK_DIZINI.resolve()
        hedef = yol.resolve()
    except OSError:
        return None
    if hedef.parent != kok or hedef.suffix != ".json":
        return None
    return yol


def atma_plani(dosya_adlari: list[str] | None = None, simdi: datetime | None = None) -> dict[str, Any]:
    """NE atılacağını hesaplar — HİÇBİR ŞEY SİLMEZ (onay ekranı bunu gösterir).

    Args:
        dosya_adlari: None → tüm kuyruk. Boş liste → hiçbir şey (yanlışlıkla
            "hepsini at" tetiklenmesin).

    Döner: {"adet": n, "basliklar": [...], "toplam": kuyruktaki toplam, "hedef": [...]}
    """
    veri = kayitlari_oku(simdi)
    kayitlar = veri["kayitlar"]
    if dosya_adlari is None:
        hedef = kayitlar[:TOPLU_AZAMI]
    else:
        istenen = {str(a) for a in dosya_adlari if str(a).strip()}
        hedef = [k for k in kayitlar if k["dosya_adi"] in istenen][:TOPLU_AZAMI]
    return {
        "adet": len(hedef),
        "basliklar": [k["baslik"] for k in hedef],
        "toplam": len(kayitlar),
        "hedef": hedef,
    }


def at(kayit: dict[str, Any], simdi: datetime | None = None) -> bool:
    """Tek kaydı `arsiv/atilan/` altına TAŞIR (kalıcı silme yok).

    Döner: taşındıysa True. Kuyruk dışı yol / bozuk kayıt → False (sessiz
    veri kaybı olmaz, çağıran `YAPILMADI` diye raporlar).
    """
    yol = _guvenli_dosya(kayit)
    if yol is None or not yol.exists():
        return False
    simdi = simdi or datetime.now(UTC)
    ATILAN_DIZINI.mkdir(parents=True, exist_ok=True)
    hedef = ATILAN_DIZINI / f"{simdi.strftime('%Y%m%d_%H%M%S')}_{yol.name}"
    try:
        shutil.move(str(yol), str(hedef))
    except OSError:
        return False
    return True


def toplu_at(dosya_adlari: list[str] | None = None, simdi: datetime | None = None) -> dict[str, Any]:
    """Planı uygular: her kaydı tek tek taşır, sonucu dürüstçe raporlar.

    Döner: {"atilan": n, "basarisiz": n, "toplam": n}
    """
    plan = atma_plani(dosya_adlari, simdi)
    atilan = 0
    for kayit in plan["hedef"]:
        if at(kayit, simdi):
            atilan += 1
    return {"atilan": atilan, "basarisiz": plan["adet"] - atilan, "toplam": plan["toplam"]}


def geri_al(azami: int = 1) -> dict[str, Any]:
    """`arsiv/atilan/` içindeki EN SON kaydı kuyruğa geri koyar (yanlış tıklama telafisi)."""
    if not ATILAN_DIZINI.exists():
        return {"geri_alinan": 0, "sebep": "atılan kayıt yok"}
    adaylar = sorted(ATILAN_DIZINI.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not adaylar:
        return {"geri_alinan": 0, "sebep": "atılan kayıt yok"}
    geri_alinan = 0
    KUYRUK_DIZINI.mkdir(parents=True, exist_ok=True)
    for kaynak in adaylar[: max(1, azami)]:
        # Dosya adındaki zaman damgası önekini at: "20260101_120000_x.json" -> "x.json"
        parcalar = kaynak.name.split("_", 2)
        hedef_adi = parcalar[2] if len(parcalar) == 3 else kaynak.name
        hedef = KUYRUK_DIZINI / hedef_adi
        if hedef.exists():
            continue
        try:
            shutil.move(str(kaynak), str(hedef))
        except OSError:
            continue
        geri_alinan += 1
    return {"geri_alinan": geri_alinan, "sebep": "" if geri_alinan else "taşınamadı"}


# ---------------------------------------------------------------------------
# Panel metni (telegram_bot.ekran_kuyruk bunu kullanır)
# ---------------------------------------------------------------------------


def _kisa(baslik: str, sinir: int = 28) -> str:
    b = " ".join(str(baslik).split())
    return b if len(b) <= sinir else b[: sinir - 1] + "…"


def panel_metni(simdi: datetime | None = None, azami_satir: int = 6) -> str:
    """Kuyruk ekranı metni — en fazla ~15 satır, uydurma sayı yok."""
    o = ozet(simdi)
    satirlar = ["📦 <b>Stok (Kuyruk)</b>", ""]
    if not o["toplam"] and not o["bozuk"]:
        satirlar.append("✅ Stok boş — bekleyen video yok.")
        satirlar.append("")
        satirlar.append("Yükleme tavanı YOK: üretilen her video hemen yüklenir.")
        satirlar.append("Stok yalnız YouTube'un kendi 403 kotasında oluşur.")
        return "\n".join(satirlar)

    satirlar.append(f"📊 Bekleyen: {o['toplam']} video")
    for sebep, adet in sorted(o["sebep_dagilimi"].items(), key=lambda x: -x[1]):
        satirlar.append(f"• {SEBEP_ETIKETI.get(sebep, BILINMIYOR)}: {adet}")
    if o["bozuk"]:
        satirlar.append(f"⚠️ Bozuk kayıt: {o['bozuk']} dosya (silinmedi)")
    uyarilar = []
    if o["bayat"]:
        uyarilar.append(f"⏳ {o['bayat']} kayıt {BAYAT_GUN}+ gündür bekliyor")
    if o["video_yok"]:
        uyarilar.append(f"🎞️ {o['video_yok']} kaydın MP4'ü diskte yok (yeniden render gerekir)")
    if uyarilar:
        satirlar.extend(uyarilar)
    satirlar.append("")
    for k in o["kayitlar"][:azami_satir]:
        yas = f"{k['yas_gun']}g" if k["yas_gun"] is not None else BILINMIYOR
        satirlar.append(f"• {_kisa(k['baslik'])} — {yas} · {k['deneme']} deneme")
    if o["toplam"] > azami_satir:
        satirlar.append(f"… +{o['toplam'] - azami_satir} kayıt daha")
    return "\n".join(satirlar)


def onay_metni(dosya_adlari: list[str] | None = None, simdi: datetime | None = None) -> str:
    """Atma onayı: kaç kayıt, hangileri, geri alınabilir mi — hepsi açık yazılır."""
    plan = atma_plani(dosya_adlari, simdi)
    if plan["adet"] == 0:
        return "⚠️ <b>Atılacak kayıt yok</b>\n\nKuyruk boş veya seçim boş."
    satirlar = [
        "⚠️ <b>ONAY GEREKİYOR</b>",
        "",
        f"🗑️ Stoktan atılacak: <b>{plan['adet']}</b> / {plan['toplam']} kayıt",
        "",
    ]
    for b in plan["basliklar"][:4]:
        satirlar.append(f"• {_kisa(b, 34)}")
    if plan["adet"] > 4:
        satirlar.append(f"… +{plan['adet'] - 4} daha")
    satirlar += [
        "",
        "Kayıtlar SİLİNMEZ: <code>archive/atilan/</code> altına taşınır, "
        "'↩️ Geri al' ile döner.",
        "",
        "Onaylamadan hiçbir dosyaya dokunulmaz.",
    ]
    return "\n".join(satirlar)


def yas_esigi_asildi(dosya_adi: str, gun: int = BAYAT_GUN, simdi: datetime | None = None) -> bool:
    """Tek kaydın bayat olup olmadığı (panellerde işaret için)."""
    simdi = simdi or datetime.now(UTC)
    for k in kayitlari_oku(simdi)["kayitlar"]:
        if k["dosya_adi"] == dosya_adi:
            return k["yas_gun"] is not None and k["yas_gun"] >= gun
    return False


#: Testlerin zamanı enjekte edebilmesi için dışa açık sabit (kullanılmıyorsa
#: ruff uyarısı vermesin diye tanım burada durur).
VARSAYILAN_BAYATLIK = timedelta(days=BAYAT_GUN)
