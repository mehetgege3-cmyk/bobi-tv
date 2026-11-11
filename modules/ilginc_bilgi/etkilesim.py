"""Etkileşim taktik motoru — 7 güvenli taktik + rotasyon + kod seviyesinde yasaklar.

Kaynak: `docs/ETKILESIM_TAKTIKLERI.md` (araştırma + YouTube politika tablosu).

KULLANICI TALEBİ (2026-11-11): "Küçük aptalca hatacıklar yap; izleyici tepki
verip 'hayır bu böyle değil, doğrusu şöyle' diye etkileşime girsin. Yanlış
bilgi vermek değil; bilinçli, her zaman değil, arasıra."

ARAŞTIRMANIN KARARI: düzeltilmemiş yanlış olgu = YouTube "deceptive
practices" riski + güven erozyonu (Coors Light: 5 gönderide 5 hata = güven
bitiyor). Bu yüzden "yanlış bırakma" yerine 7 GÜVENLİ taktik. Kullanıcının
fikri T3 olarak korunur — ama **aynı videoda düzeltme şartıyla**.

ROTASYON (doküman): video# mod 10 →
  0,5 → T1 · 1,6 → T2 · 2,7 → T5 · 3,8 → T4 · 4,9 → T6
  ayrıca 20'de bir → T3 (T1'in yerine geçer)
Bir videoda **en fazla 1 taktik**; aynı taktik art arda gelmez.

KOD SEVİYESİNDE YASAKLAR:
  • Sağlık/para/güvenlik kategorilerinde T3 (sürçme) ve T4 (ters psikoloji) YASAK.
  • T3 yalnız kanal yetkinliği kanıtlandıktan sonra (>= T3_MIN_VIDEO yayın).
  • T3'te düzeltme, sürçmeden en fazla T3_DUZELTME_SN saniye sonra gelmeli.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

#: Taktik kodları ve adları.
TAKTIKLER = {
    "T1": "yaygın yanlış inanış (çürütme)",
    "T2": "cevabı boşluk bırak, sonda kapat",
    "T3": "sürçme + aynı videoda düzeltme",
    "T4": "ters psikoloji (izleyiciyi geri itme)",
    "T5": "paradoksal gerçek",
    "T6": "iki cevap / hangisi doğru",
    "T7": "düzeltme videosu / sabitlenmiş yorum",
}

#: 10'luk rotasyon (video sırası mod 10).
ROTASYON_10 = ("T1", "T2", "T5", "T4", "T6", "T1", "T2", "T5", "T4", "T6")

#: T3 ne sıklıkta? (20 videoda 1)
T3_SIKLIK = 20
#: T3 için gereken kanıtlanmış yayın sayısı (pratfall: yetkinlik ön koşulu).
T3_MIN_VIDEO = 20
#: T3'te düzeltmenin sürçmeden sonraki azami gecikmesi (saniye).
T3_DUZELTME_SN = 4.0
#: Aynı taktiğin art arda gelmesini engelleyen pencere.
TEKRAR_PENCERE = 3

#: Bu kategorilerde T3 ve T4 YASAK (sağlık/para/güvenlik).
HASSAS_KATEGORILER = {
    "saglik", "saglik_sorunu", "insan_vucudu", "beslenme", "yiyecekler",
    "para", "finans", "yatirim", "kripto", "hukuk", "guvenlik", "gunluk_yasam",
}

STATE_VARSAYILAN = Path("bobi_tv/state/etkilesim_gecmisi.json")


@dataclass
class TaktikSecimi:
    """Seçilen taktik + uygulama talimatı (Arena prompt'u için)."""

    kod: str
    ad: str
    talimat: str
    uyarilar: list[str] = field(default_factory=list)
    alternatif: str | None = None


#: Arena'ya verilen taktik talimatları. Hepsi "yanlış bilgi bırakmadan"
#: yazılmıştır; T3 istisnası kendi içinde düzeltme şartı taşır.
TALIMATLAR = {
    "T1": (
        "İzleyicinin muhtemelen YANLIŞ bildiği yaygın bir inanışla başla "
        "('çoğumuz ... sanırız, oysa gerçek bambaşka'). Sonra doğrusunu "
        "açıkla. Yanlış inanışı gerçek gibi sunma; yalnız insanların öyle "
        "bildiğini söyle."
    ),
    "T2": (
        "Merak uyandıran soruyu sor, cevabı HEMEN verme; araya 2-3 cümle "
        "ipucu koy ve cevabı bölümün SONUNDA mutlaka ver. Açık döngü "
        "kapatılmadan bitirmek YASAK."
    ),
    "T3": (
        "Bilinçli küçük bir sürçme yap: bir tarih/sayıyı yanlış söyle, "
        "hemen ardından 'pardon, ...' diyerek DOĞRUSUNU söyle "
        f"(en fazla {int(T3_DUZELTME_SN)} saniye sonra). Sürçme asla "
        "düzeltilmeden bırakılmaz. Sürçme konuşma akışını bozmayacak kadar "
        "küçük olmalı (isim/tarih/sayı); ana bilgi yanlış olamaz."
    ),
    "T4": (
        "Ters psikoloji kullan: 'bu video işine yaramayabilir, izlemeyi "
        "bırakabilirsin' gibi izleyiciyi hafifçe geri it, sonra neden "
        "yararlı olduğunu göster. Suçlayıcı/aşağılayıcı dil YASAK."
    ),
    "T5": (
        "Paradoksal bir gerçeği vurgula ('ne kadar X yaparsan o kadar Y "
        "azalır' gibi) ve nedenini açıkla."
    ),
    "T6": (
        "İki olası cevabı sun ('A mı B mi?') ve hangisinin doğru olduğunu "
        "sonda açıkla. İzleyiciyi yoruma davet et ama abartma: tek cümle."
    ),
    "T7": (
        "Bu video bir önceki videodaki küçük hatayı düzeltir: hatayı açıkça "
        "kabul et, doğrusunu ver, izleyiciye teşekkür et."
    ),
}


def _durum_yukle(yol: Path | None = None) -> dict:
    hedef = yol or STATE_VARSAYILAN
    try:
        veri = json.loads(hedef.read_text(encoding="utf-8"))
        if isinstance(veri, dict):
            veri.setdefault("gecmis", [])
            return veri
    except Exception:
        pass
    return {"sur": 1, "gecmis": []}


def _durum_yaz(veri: dict, yol: Path | None = None) -> None:
    hedef = yol or STATE_VARSAYILAN
    try:
        hedef.parent.mkdir(parents=True, exist_ok=True)
        hedef.write_text(json.dumps(veri, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:  # pragma: no cover
        print(f"[Etkileşim] Durum yazılamadı: {str(e)[:100]}")


def taktik_sec(
    video_no: int,
    kategori: str,
    yayin_sayisi: int = 0,
    yol: Path | None = None,
    *,
    onceki_taktikler: list[str] | None = None,
) -> TaktikSecimi:
    """Video numarasına göre taktiği seçer (deterministik, ölçülebilir).

    `yayin_sayisi`: kanalın bugüne kadar yayınladığı video sayısı. T3
    (sürçme) için >= T3_MIN_VIDEO şartı buradan kontrol edilir (pratfall:
    yetkinlik kanıtlanmadan gaf = itibar kaybı).

    `onceki_taktikler`: son videoların taktikleri (en yeniden eskiye).
    Verilmezse state dosyasından okunur.
    """
    kategori = str(kategori or "").lower()
    uyarilar: list[str] = []

    if onceki_taktikler is None:
        # Yalnız açıkça yol verildiğinde veya üretim akışında (STATE varsa)
        # geçmiş okunur; birim testleri makinenin durumundan etkilenmez.
        if yol is not None or STATE_VARSAYILAN.exists():
            gecmis = _durum_yukle(yol).get("gecmis") or []
            onceki_taktikler = [str(k.get("taktik")) for k in reversed(gecmis[-5:])]
        else:
            onceki_taktikler = []

    # 1) T3 adayı mı? (20'de bir)
    aday = "T3" if video_no % T3_SIKLIK == 0 and video_no > 0 else None
    if aday:
        if kategori in HASSAS_KATEGORILER:
            uyarilar.append(f"T3 '{kategori}' kategorisinde yasak → güvenli taktiğe düşüldü")
            aday = None
        elif yayin_sayisi < T3_MIN_VIDEO:
            uyarilar.append(
                f"T3 için yetkinlik kanıtı yetersiz ({yayin_sayisi} yayın < "
                f"{T3_MIN_VIDEO}) → güvenli taktiğe düşüldü"
            )
            aday = None
        elif onceki_taktikler and "T3" in onceki_taktikler[:5]:
            uyarilar.append("son 5 videoda T3 vardı → güvenli taktiğe düşüldü")
            aday = None

    kod = aday or ROTASYON_10[video_no % len(ROTASYON_10)]

    # 2) Hassas kategori: T4 de yasak
    if kod == "T4" and kategori in HASSAS_KATEGORILER:
        uyarilar.append(f"T4 '{kategori}' kategorisinde yasak → T1'e düşüldü")
        kod = "T1"

    # 3) Art arda gelme koruması
    # "Art arda gelme" yasağı yalnız BİR ÖNCEKİ videoya bakar. Daha uzun
    # pencere rotasyonu eziyordu (T1'e kilitleniyordu); 10'luk rotasyon aynı
    # taktiğin 5 video arayla gelmesini zaten garanti eder.
    if onceki_taktikler and kod == onceki_taktikler[0]:
        # T3'e geri dönme (yetkinlik/hassas kategori kapılarını atlamamak için)
        alternatif = next(
            k for k in ("T1", "T2", "T5", "T6")
            if k not in onceki_taktikler[:2]
        )
        uyarilar.append(f"{kod} son videolarda vardı → {alternatif}'e döndürüldü")
        kod = alternatif

    talimat = TALIMATLAR[kod]
    if kod == "T3":
        uyarilar.append(
            f"T3 AKTİF: sürçme en fazla {int(T3_DUZELTME_SN)} sn içinde düzeltilecek "
            "(kalite kapısı bunu denetler)"
        )
    return TaktikSecimi(kod=kod, ad=TAKTIKLER[kod], talimat=talimat, uyarilar=uyarilar)


def kaydet(
    video_no: int,
    taktik: str,
    kategori: str,
    yayin_tarihi: str = "",
    yol: Path | None = None,
    ek: dict | None = None,
) -> dict:
    """Taktik seçimini geçmişe yazar (rotasyon + ölçüm için)."""
    durum = _durum_yukle(yol)
    kayit = {"video_no": video_no, "taktik": taktik, "kategori": kategori,
             "tarih": yayin_tarihi}
    kayit.update(ek or {})
    durum["gecmis"].append(kayit)
    durum["gecmis"] = durum["gecmis"][-500:]  # sınırsız büyümeyi engelle
    _durum_yaz(durum, yol)
    return kayit


def t3_duzeltme_dogrula(metin: str, duzeltme_sn: float | None = None) -> tuple[bool, str]:
    """T3 uygulanmış bir metinde düzeltme gerçekten var mı?

    Kod seviyesinde kilit: sürçme varsa mutlaka 'pardon/afedersiniz/yanlış
    söyledim/doğrusu' gibi bir düzeltme izi olmalı. Yoksa içerik REDDEDİLİR
    (düzeltilmemiş yanlış olgu = YouTube deceptive practices riski).
    """
    m = str(metin or "").lower()
    izler = ("pardon", "afedersiniz", "yanlış söyledim", "doğrusu", "düzeltiyorum",
             "yanlış oldu", "şey değil", "yani şöyle", "baştan söyleyeyim")
    if not any(i in m for i in izler):
        return False, "T3: düzeltme izi yok (sürçme düzeltilmeden bırakılmış)"
    if duzeltme_sn is not None and duzeltme_sn > T3_DUZELTME_SN:
        return False, (
            f"T3: düzeltme çok geç ({duzeltme_sn:.1f} sn > {T3_DUZELTME_SN:.0f} sn)"
        )
    return True, "uygun"


def performans_ozeti(yol: Path | None = None) -> dict:
    """Taktik bazında kaç video yapıldı (ölçüm paneli girdisi)."""
    gecmis = _durum_yukle(yol).get("gecmis") or []
    sayac: dict[str, int] = {}
    for k in gecmis:
        t = str(k.get("taktik"))
        sayac[t] = sayac.get(t, 0) + 1
    return {"toplam": len(gecmis), "taktik_bazinda": sayac}
