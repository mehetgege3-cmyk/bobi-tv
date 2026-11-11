"""BOBİ TV — Arşiv ↔ kanal periyodik eşitleme (TODO dosyası madde 5).

NEDEN
-----
`videos.json` ile YouTube kanalı zamanla ayrışır: bir video telif/kural
nedeniyle kanaldan düşebilir ama arşivde "yayında" görünmeye devam eder.
Panelde "🚀 Yayında" sayısı şişer, kullanıcı olmayan videoyu var sanır.

KURALLAR (mevcut felsefe)
-------------------------
1. SİLME YOK: kanaldan düşen kayıt arşivden silinmez, `durum: "kaldirildi"`
   olarak işaretlenir (+ `kaldirilma_tespit` zaman damgası ve kaynak bilgisi).
2. UYDURMA YOK: oembed "kesin yok" demeden hiçbir kayıt işaretlenmez. Ağ
   hatası / 429 / 5xx = "bilinmiyor" → o kayıt ATLANIR, ertesi koşuda
   yeniden denenir.
3. Kalıcı 404 tek başına yeterli DEĞİL: video gizli/özel olabilir. İki
   bağımsız kontrol (oembed + watch sayfası) aynı sonucu vermezse kayıt
   "şüpheli" sayılır, `durum` DEĞİŞMEZ (yanlış işaretleme veri kaybıdır).
4. Kanal toplu kapanması (aynı koşuda çok sayıda 404) durdurucudur:
   kanal askıya alınmışsa tüm arşivi "kaldirildi" yapmak istemeyiz.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ARSIV = Path("bobi_tv/archive/videos.json")
DURUM_RAPORU = Path("bobi_tv/state/arsiv_esitleme.json")

#: oembed/watch sonucu: video YOK (kesin).
YOK = "yok"
#: Video VAR.
VAR = "var"
#: Karar verilemedi (ağ hatası, 429, 5xx, gizli video şüphesi).
BILINMIYOR = "bilinmiyor"

#: Toplu kayıp koruması (iki bağımsız eşik):
#: (a) HEPSİ: kontrol edilenlerin TAMAMI yoksa (≥5 kayıt) → kanal askıya
#:     alınmış kapanmış olabilir; arşiv değiştirilmez, insan bakar;
#: (b) SAYI: tek koşuda 25'ten fazla kayıt yoksa → insan onayı gerekir.
#: Kısmi kayıplar (telif dalgası, tek tek silinenler) NORMAL işaretlenir —
#: oran eşiği koymak gerçek kayıpları görmezden gelmek olurdu (ölçüm
#: 2026-11-11: 13 canlı kaydın 8'i kanalda yoktu, hepsi 404/404).
KITLE_ESIGI = 25

#: "Hepsi yok" sayılması için gereken asgari kayıt (tek kayıtlı arşivde
#: yanlış alarm olmasın).
HEPSI_ESIGI = 5

#: Kanalda OLMAMASI beklenen durumlar: bunlar kontrol edilmez.
#: `silindi_dusuk_izlenme` = kanaldan zaten kaldırılmış (düşük izlenme
#: temizliği) — yeniden işaretlemek gereksiz ve gürültü olur.
KONTROL_DISI_DURUMLAR = {"kaldirildi", "silindi_dusuk_izlenme"}


@dataclass
class EsitlemeSonucu:
    """Eşitleme koşusunun dürüst özeti (panel ve rapor buradan okur)."""

    kontrol_edilen: int = 0
    kaldirildi_isaretli: list[str] = field(default_factory=list)
    #: Durdurma nedeniyle BU KOŞUDA işaretlenmeyenler (sonraki koşuda denenir).
    bekleyen: list[str] = field(default_factory=list)
    zaten_isaretli: int = 0
    supheli: list[str] = field(default_factory=list)
    bilinmeyen: list[str] = field(default_factory=list)
    durduruldu: str = ""
    yazildi: bool = False

    def ozet_metni(self) -> str:
        if self.durduruldu:
            return f"⛔ eşitleme durduruldu: {self.durduruldu}"
        return (
            f"🔎 {self.kontrol_edilen} kayıt kontrol edildi · "
            f"🗑 {len(self.kaldirildi_isaretli)} yeni kaldırıldı · "
            f"❔ {len(self.bilinmeyen)} bilinmiyor"
        )


# ---------------------------------------------------------------------------
# Arşiv okuma / yazma
# ---------------------------------------------------------------------------


def _arsiv_oku() -> list[dict[str, Any]]:
    try:
        veri = json.loads(ARSIV.read_text(encoding="utf-8"))
        return list(veri.values()) if isinstance(veri, dict) else list(veri)
    except Exception:
        return []


def _arsiv_yaz(kayitlar: list[dict[str, Any]]) -> bool:
    try:
        ARSIV.parent.mkdir(parents=True, exist_ok=True)
        ARSIV.write_text(json.dumps(kayitlar, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"[Eşitleme] arşiv yazılamadı: {str(e)[:80]}")
        return False


def _onceki_durumlari_geri_al(kayitlar: list[dict[str, Any]]) -> None:
    """Durdurulan koşuda bellekte yapılan işaretlemeleri geri alır (disk zaten
    yazılmadı; bu yalnız çağıranın gördüğü listeyi tutarlı yapar)."""
    for k in kayitlar:
        if k.get("kaldirilma_kaynagi") == "arsiv_esitleme" and "kaldirilma_tespit" in k:
            k.pop("kaldirilma_kaynagi", None)
            k.pop("kaldirilma_tespit", None)
            k["durum"] = "yayinda"


# ---------------------------------------------------------------------------
# Kanal kontrolü — iki bağımsız yol
# ---------------------------------------------------------------------------


def oembed_kontrol(video_id: str, zaman_asimi: float = 8.0) -> str:
    """`oembed` ucu (API anahtarı GEREKMEZ, kota harcamaz).

    404 → YOK. 401/403 → video gizli/özel olabilir → BILINMIYOR (silinmiş
    demek için yeterli kanıt değil). Diğer her şey → BILINMIYOR.
    """
    import requests

    url = "https://www.youtube.com/oembed"
    try:
        r = requests.get(
            url,
            params={"url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"},
            timeout=zaman_asimi,
        )
    except Exception:
        return BILINMIYOR
    if r.status_code == 200:
        return VAR
    if r.status_code == 404:
        return YOK
    return BILINMIYOR


def izleme_sayfasi_kontrol(video_id: str, zaman_asimi: float = 8.0) -> str:
    """İkinci kontrol: watch sayfasında videonun gerçekten gömülü olup olmadığı.

    Kanal kaldırma dışındaki nedenler (yaş kısıtı, ülke kısıtı) sayfayı
    oynatılamaz gösterir ama video DURUR → bu yüzden yalnızca "video yok"
    cevabı YOK sayılır; "oynatılamıyor" BILINMIYOR'dur.
    """
    import requests

    try:
        r = requests.get(
            f"https://www.youtube.com/watch?v={video_id}",
            timeout=zaman_asimi,
            headers={"User-Agent": "Mozilla/5.0 (compatible; bobi-tv/1.0)"},
        )
    except Exception:
        return BILINMIYOR
    if r.status_code == 404:
        return YOK
    if r.status_code != 200:
        return BILINMIYOR
    govde = r.text or ""
    if '"playabilityStatus":{"status":"ERROR"' in govde.replace(" ", ""):
        return YOK
    if "videoDetails" in govde:
        return VAR
    return BILINMIYOR


def video_var_mi(video_id: str) -> str:
    """İki bağımsız kontrolü birleştirir.

    YOK yalnızca İKİSİ de "yok" derse kesinleşir (yanlış işaretleme = veri
    kaybı). Biri VAR derse VAR, aksi hâlde BILINMIYOR.
    """
    if not video_id:
        return BILINMIYOR
    a = oembed_kontrol(video_id)
    b = izleme_sayfasi_kontrol(video_id)
    if a == YOK and b == YOK:
        return YOK
    if YOK in (a, b) and VAR in (a, b):
        # Çelişki: oembed yok diyor ama sayfa videoyu gösteriyor (gizli/yaş
        # kısıtlı). Kesin karar verme — kaydı işaretlemek veri kaybıdır.
        return BILINMIYOR
    if VAR in (a, b):
        return VAR
    return BILINMIYOR


# ---------------------------------------------------------------------------
# Eşitleme
# ---------------------------------------------------------------------------


def esitle(
    simdi: datetime | None = None,
    kontrol: Any = None,
    yaz: bool = True,
    kitle_esigi: int = KITLE_ESIGI,
) -> EsitlemeSonucu:
    """Arşivdeki kayıtları kanalla karşılaştırır.

    `kontrol`: test için enjekte edilebilir fonksiyon (video_id → YOK/VAR/
    BILINMIYOR). Varsayılan `video_var_mi`.
    `yaz=False`: yalnız ölçer, arşivi değiştirmez (dry-run).
    """
    simdi = simdi or datetime.now(UTC)
    kontrol = kontrol or video_var_mi
    sonuc = EsitlemeSonucu()
    kayitlar = _arsiv_oku()
    if not kayitlar:
        sonuc.durduruldu = "arşiv okunamadı veya boş"
        return sonuc

    degisti = False
    yok_sayaci = 0
    yok_idler: list[str] = []
    for k in kayitlar:
        if str(k.get("durum", "")) in KONTROL_DISI_DURUMLAR:
            sonuc.zaten_isaretli += 1
            continue
        vid = str(k.get("video_id") or "")
        if not vid:
            continue
        sonuc.kontrol_edilen += 1
        durum = kontrol(vid)
        if durum == VAR:
            continue
        if durum == BILINMIYOR:
            sonuc.bilinmeyen.append(vid)
            continue
        # durum == YOK
        yok_sayaci += 1
        yok_idler.append(vid)
        if yok_sayaci > kitle_esigi:
            sonuc.durduruldu = (
                f"{yok_sayaci} video birden yok göründü (> {kitle_esigi}) — "
                "kanal askıya alınmış olabilir; arşiv DEĞİŞTİRİLMEDİ"
            )
            sonuc.bekleyen = list(yok_idler)
            sonuc.kaldirildi_isaretli.clear()
            _onceki_durumlari_geri_al(kayitlar)
            sonuc.yazildi = False
            rapor_yaz(sonuc, simdi)
            return sonuc
        k["durum"] = "kaldirildi"
        k["kaldirilma_kaynagi"] = "arsiv_esitleme"
        k["kaldirilma_tespit"] = simdi.isoformat()
        sonuc.kaldirildi_isaretli.append(vid)
        degisti = True

    if (
        sonuc.kontrol_edilen >= HEPSI_ESIGI
        and yok_sayaci == sonuc.kontrol_edilen
    ):
        sonuc.durduruldu = (
            "kontrol edilen kayıtların TAMAMI yok göründü — kanal kapanmış/askıya "
            "alınmış olabilir; arşiv DEĞİŞTİRİLMEDİ"
        )
        sonuc.bekleyen = list(yok_idler)
        sonuc.kaldirildi_isaretli.clear()
        _onceki_durumlari_geri_al(kayitlar)
        sonuc.yazildi = False
        rapor_yaz(sonuc, simdi)
        return sonuc

    if degisti and yaz:
        sonuc.yazildi = _arsiv_yaz(kayitlar)
    elif degisti:
        sonuc.yazildi = False

    rapor_yaz(sonuc, simdi)
    return sonuc


def rapor_yaz(sonuc: EsitlemeSonucu, simdi: datetime | None = None) -> bool:
    """Son eşitleme koşusunu state'e yazar (panel "son eşitleme" gösterir)."""
    try:
        DURUM_RAPORU.parent.mkdir(parents=True, exist_ok=True)
        DURUM_RAPORU.write_text(
            json.dumps(
                {
                    "zaman": (simdi or datetime.now(UTC)).isoformat(),
                    "kontrol_edilen": sonuc.kontrol_edilen,
                    "isaretlenen": sonuc.kaldirildi_isaretli,
                    "supheli": sonuc.supheli,
                    "bilinmeyen": sonuc.bilinmeyen,
                    "durduruldu": sonuc.durduruldu,
                    "ozet": sonuc.ozet_metni(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return True
    except Exception:
        return False


def son_esitleme() -> dict[str, Any]:
    """Panel için son eşitleme özeti (yoksa 'bilinmiyor' — uydurma yok)."""
    try:
        return dict(json.loads(DURUM_RAPORU.read_text(encoding="utf-8")))
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# CLI — haftalık workflow bu komutu çağırır
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """`python3 -m modules.arsiv_esitleme [--kuru]` → 0 başarı, 2 durduruldu."""
    import sys

    argv = argv if argv is not None else sys.argv[1:]
    kuru = "--kuru" in argv
    sonuc = esitle(yaz=not kuru)
    print(f"[Eşitleme] {sonuc.ozet_metni()}")
    if sonuc.kaldirildi_isaretli:
        print(f"[Eşitleme] işaretlenen: {', '.join(sonuc.kaldirildi_isaretli)}")
    if sonuc.bilinmeyen:
        print(f"[Eşitleme] kararsız (sonraki koşuda yeniden denenecek): {len(sonuc.bilinmeyen)}")
    return 2 if sonuc.durduruldu else 0


if __name__ == "__main__":
    raise SystemExit(main())
