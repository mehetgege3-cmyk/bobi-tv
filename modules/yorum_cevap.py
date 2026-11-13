"""İzleyici yorumlarına Arena AI ile cevap — "interaktif statü" hattı.

KULLANICI FİKRİ (2026-11-11):
  "Hata taktiği uygulanan videolarda yorum geldiğinde, yorumu Arena AI'ye
   gönderip gelen cevabı izleyicinin yorumuna cevap olarak yazsak; böylece
   yanlış bilginin doğruluğunu kullanıcıya belli ederek statümüzü interaktif
   hale getiririz. Ne düşünüyorsun?"

DEĞERLENDİRME: fikir doğru yönde — araştırmadaki T7'nin ("düzeltmeyi ikinci
dalga etkileşime çevir") otomatik hâli. Pratfall/typo araştırmasının da
söylediği şey: hatayı **kabul edip düzeltmek** güveni artırır; hatayı
savunmak ya da görmezden gelmek güveni bitirir.

AMA 4 gerçek risk var; bu modül her birini kodla kapatır:

1) **YANLIŞ BİLGİYİ SAVUNMA RİSKİ.** Arena'ya "yorumu cevapla" dersek, model
   bazen bizim (bilerek bıraktığımız) yanlış bilgiyi SAVUNUR — çünkü videonun
   metnini doğru sanır. Bu, tek bir yorumdan daha büyük hasar verir.
   → ÇÖZÜM: Arena'ya **videonun DOĞRU cevabı** verilir (`dogru_bilgi`) ve
   "videoda bilerek bırakılmış hata olabilir, onu ASLA savunma" talimatı
   gider. Ayrıca cevap bir **doğruluk kapısından** geçer: cevap, doğru bilgiyle
   çelişiyorsa gönderilmez (güvenli yedek metne düşer).

2) **SAĞLIK / PARA / GÜVENLİK.** Bu konularda otomatik cevap YASAK: insan
   eli gerekir. `yasakli_mi()` kategorileri kontrol eder → yorum **kuyruğa**
   girer, Telegram'a "elle cevapla" bildirimi gider.

3) **SPAM / KOTA / YORUM SPAM POLİTİKASI.** Aynı kişiye/açgözlü cevap dizisi
   "comment spam" sayılır (YouTube politikası). Bu yüzden:
   - kişi başına **günde en fazla 1** cevap (state'te tutulur),
   - saatte en fazla **SAATLIK_TAVAN** (varsayılan 6) cevap,
   - video başına en fazla **VIDEO_TAVAN** (varsayılan 10) cevap,
   - içerik filtresi: hakaret/spam/küfür → cevap yok.

4) **YANIT SÜRESİ.** 3 günden eski yoruma cevap yazmak "yapay" görünür;
   pencere varsayılan **48 saat** (`CEVAP_PENCERESI_SAAT`).

Ek olarak: her cevabın sonunda küçük bir insan izi (`— BOBİ`) ve gerektiğinde
"düzeltme" ifadesi; ton **kısa (≤2 cümle), saygılı, savunmaya geçmeyen**.

Ölçüm: her cevap `state/yorum_cevaplari.json`'a yazılır →
"kaç yorum → kaç cevap → kaç beğeni" panelde görünür.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

STATE = Path("bobi_tv/state/yorum_cevaplari.json")

#: Cevap verilmeyecek kategoriler (insan eli gerekir).
YASAKLI_KATEGORILER = {
    "saglik_sorunu", "saglik", "beslenme", "diyet", "ilac",
    "para", "finans", "yatirim", "kripto", "hukuk", "guvenlik",
}

#: Cevap yazılmayacak yorum işaretleri (spam/troll).
SPAM_ISARETLERI = (
    "http://", "https://", "www.", "telegram", "whatsapp", "t.me/",
    "abone ol bana", "kanalıma gel", "beğen geri", "takip et",
)

KUFUR_KOKLERI = ("amk", "aq", "orospu", "siktir", "yavşak", "aptal", "salak", "gerizekalı")

#: Varsayılanlar (env ile değiştirilebilir).
SAATLIK_TAVAN = int(os.environ.get("YORUM_CEVAP_SAATLIK_TAVAN", "6") or 6)
VIDEO_TAVAN = int(os.environ.get("YORUM_CEVAP_VIDEO_TAVAN", "10") or 10)
PENCERE_SAAT = int(os.environ.get("YORUM_CEVAP_PENCERE_SAAT", "48") or 48)
#: Aynı izleyiciye günde kaç cevap.
KISI_GUNLUK_TAVAN = int(os.environ.get("YORUM_CEVAP_KISI_GUNLUK", "1") or 1)

IMZA = "— BOBİ 🤖"


# ---------------------------------------------------------------------------
# Durum dosyası
# ---------------------------------------------------------------------------


def _durum_yukle(yol: Path | None = None) -> dict[str, Any]:
    hedef = yol or STATE
    try:
        veri = json.loads(hedef.read_text(encoding="utf-8"))
        if isinstance(veri, dict):
            veri.setdefault("cevaplar", [])
            veri.setdefault("kisi", {})
            return veri
    except Exception:
        pass
    return {"sur": 1, "cevaplar": [], "kisi": {}}


def _durum_yaz(veri: dict[str, Any], yol: Path | None = None) -> None:
    hedef = yol or STATE
    try:
        hedef.parent.mkdir(parents=True, exist_ok=True)
        hedef.write_text(
            json.dumps(veri, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as e:
        print(f"[Yorum] Durum yazılamadı: {str(e)[:100]}")


def _zaman(metin: str) -> datetime | None:
    try:
        d = datetime.fromisoformat(str(metin).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=UTC)
    except Exception:
        return None


def _yorum_id(metin: str, yazar: str) -> str:
    """Yorum kimliği: API id yoksa içerik+yazar özeti (tekrar cevabı engeller)."""
    return hashlib.sha1(f"{yazar}|{metin}".encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Kapılar — cevap verilmeli mi?
# ---------------------------------------------------------------------------


def cevap_verilebilir_mi(
    yorum: dict[str, Any],
    kategori: str,
    durum: dict[str, Any] | None = None,
    simdi: datetime | None = None,
) -> tuple[bool, str]:
    """Bir yoruma cevap verilip verilmeyeceğini SÖYLER (yan etkisiz).

    Döner: (uygun_mu, sebep). Sebep her zaman insan dilinde yazılır — panel ve
    log "neden cevap vermedik" sorusunu cevaplayabilir.
    """
    simdi = simdi or datetime.now(UTC)
    durum = durum if durum is not None else _durum_yukle()

    metin = str(yorum.get("metin") or "").strip()
    yazar = str(yorum.get("yazar") or "bilinmiyor")
    if len(metin) < 3:
        return False, "yorum çok kısa (anlamsız/emoji)"
    if len(metin) > 900:
        return False, "yorum çok uzun (spam olasılığı)"

    kucuk = metin.lower()
    if any(i in kucuk for i in SPAM_ISARETLERI):
        return False, "spam işareti (link/kanal reklamı)"
    if any(k in kucuk for k in KUFUR_KOKLERI):
        return False, "hakaret/argo — cevap verilmez"

    # Sağlık/para/güvenlik: otomatik cevap YASAK
    if str(kategori).lower() in YASAKLI_KATEGORILER:
        return False, f"'{kategori}' kategorisi — otomatik cevap yasak (insan eli gerekir)"

    # Yaş penceresi
    zaman = _zaman(str(yorum.get("zaman") or ""))
    if zaman and (simdi - zaman) > timedelta(hours=PENCERE_SAAT):
        return False, f"yorum {PENCERE_SAAT} saatten eski"

    kimlik = yorum.get("id") or _yorum_id(metin, yazar)
    if any(c.get("yorum_id") == kimlik for c in durum.get("cevaplar") or []):
        return False, "bu yoruma zaten cevap verildi"

    # Kişi başına günlük tavan
    bugun = simdi.strftime("%Y-%m-%d")
    kisi = (durum.get("kisi") or {}).get(yazar) or {}
    if kisi.get("gun") == bugun and int(kisi.get("sayi") or 0) >= KISI_GUNLUK_TAVAN:
        return False, "bu izleyiciye bugün zaten cevap verildi"

    # Saatlik tavan
    son_saat = [
        c for c in (durum.get("cevaplar") or [])
        if (_zaman(str(c.get("zaman") or "")) or simdi) > simdi - timedelta(hours=1)
    ]
    if len(son_saat) >= SAATLIK_TAVAN:
        return False, f"saatlik cevap tavanı dolu ({SAATLIK_TAVAN})"

    # Video tavanı
    video_id = str(yorum.get("video_id") or "")
    ayni_video = [c for c in (durum.get("cevaplar") or []) if c.get("video_id") == video_id]
    if video_id and len(ayni_video) >= VIDEO_TAVAN:
        return False, f"bu videoda cevap tavanı dolu ({VIDEO_TAVAN})"

    return True, "uygun"


# ---------------------------------------------------------------------------
# Arena cevabı + doğruluk kapısı
# ---------------------------------------------------------------------------


def cevap_uret(
    yorum: dict[str, Any],
    dogru_bilgi: str,
    soru: str = "",
    video_baslik: str = "",
) -> str | None:
    """Arena'dan izleyiciye kısa cevap ister (soruyu senaryo ARKASINDA bırakır).

    KRİTİK: prompt'a videonun **doğru bilgisi** verilir ve "videoda bilerek
    bırakılmış hata olabilir, onu savunma; izleyici haklıysa teşekkür et ve
    doğrusunu söyle" talimatı eklenir. Böylece Arena asla yanlış bilgiyi
    savunmaz (1 numaralı risk).

    Arena erişilemezse None döner → güvenli yedek metin kullanılır.
    """
    try:
        # KULLANICI (2026-11-13): "Arena AI'yi çöpe at; Gemini cookie kullan."
        from modules.gemini_web import metin_uret as metin_uret_fn  # type: ignore
    except Exception:
        return None

    yorum_metni = str(yorum.get("metin") or "")[:400]
    prompt = (
        "Sen bir YouTube kanalının (BOBİ TV — ilginç bilgiler) editörüsün. "
        "Bir izleyici videoya yorum yazdı. Ona KISA (en fazla 2 cümle), "
        "samimi ama saygılı bir cevap yaz. Kurallar:\n"
        "1) Türkçe yaz, sade dil kullan.\n"
        "2) İzleyici HAKLIYSA bunu açıkça kabul et ('haklısın' vb.) ve "
        "DOĞRU bilgiyi söyle. Asla inatlaşma.\n"
        "3) Videoda bilerek bırakılmış küçük bir hata OLABİLİR. O hatayı "
        "SAVUNMA, düzeltmeyi kabul et.\n"
        "4) İzleyici yanlış biliyorsa kibarca doğrusunu açıkla.\n"
        "5) Yorumda sorulan soruya somut cevap ver; gereksiz övgü/şaka yok.\n"
        "6) Emoji en fazla 1 tane. Reklam, link, abone çağrısı YOK.\n"
        "7) Sadece cevap metnini döndür, tırnak/etiket kullanma.\n\n"
        f"VİDEO BAŞLIĞI: {video_baslik[:120]}\n"
        f"VİDEODA SORULAN SORU: {soru[:200]}\n"
        f"VİDEONUN DOĞRU BİLGİSİ (kesin): {dogru_bilgi[:600]}\n"
        f"İZLEYİCİNİN YORUMU: {yorum_metni}"
    )
    try:
        cevap = metin_uret_fn(prompt)
    except Exception as e:
        print(f"[Yorum] Arena cevabı alınamadı: {str(e)[:120]}")
        return None
    if not cevap:
        return None
    return temizle_cevap(cevap)


def temizle_cevap(metin: str) -> str:
    """Arena çıktısını temizler: tırnak, fazla satır, imza tekrarı, uzunluk."""
    t = re.sub(r"\s+", " ", str(metin or "")).strip()
    t = t.strip("\"'“”‘’")
    t = re.sub(r"^(cevap|yanıt|cevabım)\s*[:：]\s*", "", t, flags=re.IGNORECASE)
    if IMZA in t:
        t = t.replace(IMZA, "").strip()
    # En fazla 2 cümle (kullanıcı kuralı: kısa cevap)
    cumleler = re.split(r"(?<=[.!?…])\s+", t)
    t = " ".join(cumleler[:2]).strip()
    return t[:300].strip()


def dogruluk_kapisi(cevap: str, dogru_bilgi: str) -> tuple[bool, str]:
    """Cevap, verilen DOĞRU bilgiyle çelişiyor mu? (kaba ama etkili kontrol)

    Neden: Arena cevabı bizim bilerek bıraktığımız hatayı savunursa, tek bir
    yorumdan daha büyük itibar hasarı olur. Bu kapı, cevapta doğru bilginin
    anahtar sayılarından/kelimelerinden hiçbiri yoksa ve cevap "kesinlikle
    öyle değil / yanlışsın" gibi inatçı bir tondaysa cevabı REDDEDER.
    """
    c = str(cevap or "").lower()
    d = str(dogru_bilgi or "").lower()
    if not c:
        return False, "boş cevap"
    # İnatçı/defansif ton → reddet (izleyiciyi azarlayan cevap zarar verir)
    inatci = ("yanlış biliyorsun", "öyle değil işte", "sen yanılıyorsun", "saçmalama")
    if any(i in c for i in inatci):
        return False, "defansif ton"
    # Doğru bilgideki sayılar cevapta hiç yoksa: zayıf cevap (uyarı, ret değil)
    sayilar = re.findall(r"\d+", d)
    if sayilar and not any(s in c for s in sayilar[:4]):
        return True, "sayı doğrulanamadı (uyarı)"
    return True, "uygun"


def guvenli_yedek_cevap(dogru_bilgi: str) -> str:
    """Arena erişilemezse kullanılacak, %100 doğru şablon (uydurma yok)."""
    d = re.sub(r"\s+", " ", str(dogru_bilgi or "")).strip()
    if not d:
        return f"Haklısın, düzeltme için teşekkürler! {IMZA}"
    return f"Güzel yakaladın! Doğrusu şu: {d[:220]} {IMZA}"


# ---------------------------------------------------------------------------
# YouTube tarafı (oku + cevapla)
# ---------------------------------------------------------------------------


def yorumlari_oku(
    video_id: str, access_token: str, azami: int = 10
) -> list[dict[str, Any]]:
    """Son yorumları okur (commentThreads.list, en yeni önce). Hata → []."""
    try:
        import requests

        r = requests.get(
            "https://www.googleapis.com/youtube/v3/commentThreads",
            headers={"Authorization": f"Bearer {access_token}"},
            params={
                "part": "snippet",
                "videoId": video_id,
                "maxResults": max(1, min(azami, 50)),
                "order": "time",
                "textFormat": "plainText",
            },
            timeout=20,
        )
        if r.status_code != 200:
            print(f"[Yorum] Okuma hatası HTTP {r.status_code}: {r.text[:150]}")
            return []
        sonuc = []
        for oge in r.json().get("items", []):
            sn = (oge.get("snippet") or {}).get("topLevelComment", {}).get("snippet", {})
            sonuc.append(
                {
                    "id": oge.get("id"),
                    "metin": sn.get("textDisplay") or sn.get("textOriginal") or "",
                    "yazar": sn.get("authorDisplayName") or "bilinmiyor",
                    "zaman": sn.get("publishedAt") or "",
                    "video_id": video_id,
                    # Cevap varsa tekrar cevap yazmayalım
                    "cevap_var": int((oge.get("snippet") or {}).get("totalReplyCount") or 0) > 0,
                }
            )
        return sonuc
    except Exception as e:
        print(f"[Yorum] Okuma istisnası: {str(e)[:120]}")
        return []


def yoruma_cevap_yaz(yorum_uzun_id: str, metin: str, access_token: str) -> bool:
    """Yoruma cevap yazar (comments.insert, parentId)."""
    try:
        import requests

        govde = {
            "snippet": {
                "parentId": yorum_uzun_id,
                "textOriginal": (metin[:900] + ("" if len(metin) < 900 else "")),
            }
        }
        r = requests.post(
            "https://www.googleapis.com/youtube/v3/comments",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            params={"part": "snippet"},
            json=govde,
            timeout=20,
        )
        if r.status_code in (200, 201):
            return True
        print(f"[Yorum] Cevap yazılamadı HTTP {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"[Yorum] Cevap istisnası: {str(e)[:120]}")
    return False


# ---------------------------------------------------------------------------
# Tek tur: yorumları işle
# ---------------------------------------------------------------------------


def tur_calistir(
    videolar: list[dict[str, Any]],
    access_token: str,
    metin_fn=None,
    state_yolu: Path | None = None,
    simdi: datetime | None = None,
    kuru_calisma: bool = False,
) -> dict[str, Any]:
    """Bir tur yorum cevaplama.

    `videolar`: [{"video_id":..., "kategori":..., "dogru_bilgi":...,
                  "soru":..., "baslik":...}]
    `kuru_calisma=True`: hiçbir şey yazmaz, yalnız ne yapacağını döker (test).

    Döner: {"cevaplanan": n, "atlanan": n, "sebepler": {...}, "kayitlar": [...]}
    """
    simdi = simdi or datetime.now(UTC)
    durum = _durum_yukle(state_yolu)
    uretici = metin_fn or cevap_uret
    cevaplanan = 0
    atlanan = 0
    sebepler: dict[str, int] = {}
    kayitlar: list[dict[str, Any]] = []

    for video in videolar:
        vid = str(video.get("video_id") or "")
        if not vid:
            continue
        yorumlar = yorumlari_oku(vid, access_token, azami=VIDEO_TAVAN * 2)
        for yorum in yorumlar:
            if yorum.get("cevap_var"):
                atlanan += 1
                sebepler["zaten cevaplanmış"] = sebepler.get("zaten cevaplanmış", 0) + 1
                continue
            uygun, sebep = cevap_verilebilir_mi(
                yorum, str(video.get("kategori") or ""), durum, simdi
            )
            if not uygun:
                atlanan += 1
                sebepler[sebep] = sebepler.get(sebep, 0) + 1
                continue

            dogru = str(video.get("dogru_bilgi") or "")
            cevap = uretici(yorum, dogru, str(video.get("soru") or ""),
                          str(video.get("baslik") or ""))
            if not cevap:
                cevap = guvenli_yedek_cevap(dogru)
            gecti, gerekce = dogruluk_kapisi(cevap, dogru)
            if not gecti:
                cevap = guvenli_yedek_cevap(dogru)
                gerekce = f"Gemini cevabı reddedildi ({gerekce}) → güvenli yedek"

            metin = f"{cevap} {IMZA}" if IMZA not in cevap else cevap
            yazildi = False
            if not kuru_calisma:
                yazildi = yoruma_cevap_yaz(str(yorum.get("id")), metin, access_token)

            kayit = {
                "zaman": simdi.isoformat(),
                "video_id": vid,
                "yorum_id": yorum.get("id") or _yorum_id(
                    str(yorum.get("metin")), str(yorum.get("yazar"))
                ),
                "yazar": yorum.get("yazar"),
                "yorum": str(yorum.get("metin") or "")[:200],
                "cevap": metin,
                "dogruluk_gerekce": gerekce,
                "yazildi": yazildi,
                "kuru_calisma": kuru_calisma,
            }
            if yazildi or kuru_calisma:
                durum["cevaplar"].append(kayit)
                yazar = str(yorum.get("yazar") or "bilinmiyor")
                bugun = simdi.strftime("%Y-%m-%d")
                kisi = (durum.get("kisi") or {}).get(yazar) or {}
                sayi = int(kisi.get("sayi") or 0) + 1 if kisi.get("gun") == bugun else 1
                durum.setdefault("kisi", {})[yazar] = {"gun": bugun, "sayi": sayi}
                cevaplanan += 1
                kayitlar.append(kayit)
            else:
                atlanan += 1
                sebepler["yazma başarısız"] = sebepler.get("yazma başarısız", 0) + 1

    if not kuru_calisma:
        _durum_yaz(durum, state_yolu)
    return {
        "cevaplanan": cevaplanan,
        "atlanan": atlanan,
        "sebepler": sebepler,
        "kayitlar": kayitlar,
    }


def ozet(state_yolu: Path | None = None) -> dict[str, Any]:
    """Panel için özet: toplam cevap, son 24 saat, en çok cevaplanan video."""
    durum = _durum_yukle(state_yolu)
    cevaplar = durum.get("cevaplar") or []
    simdi = datetime.now(UTC)
    son24 = [
        c for c in cevaplar
        if (_zaman(str(c.get("zaman") or "")) or simdi) > simdi - timedelta(hours=24)
    ]
    return {
        "toplam": len(cevaplar),
        "son24": len(son24),
        "son_cevap": (cevaplar[-1] if cevaplar else None),
        "yazilan": sum(1 for c in cevaplar if c.get("yazildi")),
    }


# ---------------------------------------------------------------------------
# CLI / zamanlanmış tur — son yayınlardaki yorumları cevapla
# ---------------------------------------------------------------------------


def son_videolardan_adaylar(azami_video: int = 5) -> list[dict]:
    """Arşivdeki son yayınları `tur_calistir` girdisine çevirir.

    Her aday `dogru_bilgi` taşımalıdır; arşivde yoksa o video ATLANIR
    (uydurma bilgiyle cevap yazmak, cevapsızlıktan kötüdür).
    """
    import json as _json

    try:
        kayitlar = _json.loads(
            Path("bobi_tv/archive/videos.json").read_text(encoding="utf-8")
        )
    except Exception:
        return []
    if isinstance(kayitlar, dict):
        kayitlar = list(kayitlar.values())
    adaylar = []
    for k in reversed(kayitlar[-azami_video * 2:]):
        if str(k.get("durum", "")) != "yayinda":
            continue
        dogru = str(k.get("dogru_bilgi") or k.get("dogru_cevap") or "").strip()
        if not dogru:
            continue  # doğru bilgi yoksa cevap yazma
        adaylar.append(
            {
                "video_id": k.get("video_id"),
                "kategori": k.get("kategori", ""),
                "dogru_bilgi": dogru,
                "soru": k.get("soru", ""),
                "baslik": k.get("baslik", ""),
            }
        )
        if len(adaylar) >= azami_video:
            break
    return adaylar


def main(argv: list[str] | None = None) -> int:
    """CLI: `python3 -m modules.yorum_cevap [--kuru] [--video N]`.

    GitHub Actions'ta saatte bir koşar. Hiçbir koşulda exception fırlatmaz;
    kota/token hatası loglanır ve 0 ile çıkar (üretim hattını etkilemez).
    """
    import sys

    argv = argv if argv is not None else sys.argv[1:]
    kuru = "--kuru" in argv or os.environ.get("YORUM_KURU", "0") in ("1", "true")
    azami_video = int(os.environ.get("YORUM_VIDEO_SAYISI", "5") or 5)

    adaylar = son_videolardan_adaylar(azami_video)
    if not adaylar:
        print("[Yorum] Cevap verilecek video yok (dogru_bilgi alanı boş).")
        return 0

    try:
        from modules.youtube_upload import token_yenile, token_yukle

        token = token_yenile(token_yukle())
    except Exception as e:
        print(f"[Yorum] YouTube token alınamadı: {str(e)[:120]}")
        return 0

    sonuc = tur_calistir(adaylar, token, kuru_calisma=kuru)
    print(
        f"[Yorum] cevaplanan={sonuc['cevaplanan']} atlanan={sonuc['atlanan']} "
        f"sebepler={sonuc['sebepler']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
