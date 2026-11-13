"""Yayınlanmış videoların kapaklarını Gemini ile YENİDEN üret ve YouTube'a yükle.

NEDEN (2026-11-13, kullanıcı: "Tüm mevcut videoların kapak fotoğrafını güncelle
gemini ile"):
  • Kapak hattı `..._kapakli.mp4` üretiyordu ama `paket["final_video"]`
    güncellenmediği için YouTube'a KAPAKSIZ video gidiyordu (kök neden #1).
  • Kapak 33 ms görünüyordu (kök neden #2).
  • Bu araç, geçmiş videoların kapaklarını YouTube'da DÜZELTİR:
    `thumbnails.set` ile gerçek görsel yüklenir (video yeniden yüklenmez).

ÖNEMLİ — YouTube Shorts GERÇEĞİ (docs/KAPAK_TESHIS.md §3):
  YouTube her Short için İKİ görsel tutar:
    1) `maxresdefault`/`hqdefault` → `thumbnails.set` ile DEĞİŞTİRİLEBİLİR
    2) `oar2.jpg` → Shorts rafında görünen; **API dokunamaz**, YouTube seçer.
  Yani kanal "Shorts" sekmesinde yine YouTube'un karesi görünebilir. Kanalın
  normal video listesinde ve aramada `thumbnails.set` kapağı görünür.

KULLANIM (GitHub Actions içinde; token'lar secret'tan gelir):
    PYTHONPATH=. python3 tools/kapak_yenile.py --azami 5
    PYTHONPATH=. python3 tools/kapak_yenile.py --azami 60 --kuru
    PYTHONPATH=. python3 tools/kapak_yenile.py --video-id EQPd1GlVCMw

ÇIKIŞ: her video için tek satır — `video_id | durum | kaynak | ayrıntı`
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ARSIV = Path("bobi_tv/archive/videos.json")


def arsiv_oku() -> list[dict]:
    """Yayınlanmış kayıtları okur (video_id + baslik)."""
    if not ARSIV.exists():
        print(f"❌ Arşiv yok: {ARSIV}")
        return []
    try:
        veri = json.loads(ARSIV.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"❌ Arşiv okunamadı: {e}")
        return []
    kayitlar = []
    for k in veri if isinstance(veri, list) else []:
        vid = str(k.get("video_id") or k.get("id") or "").strip()
        if not vid:
            continue
        kayitlar.append(
            {
                "video_id": vid,
                "baslik": str(k.get("baslik") or k.get("title") or "").strip(),
                "durum": str(k.get("durum") or ""),
            }
        )
    return kayitlar


def main() -> int:
    ap = argparse.ArgumentParser(description="Mevcut videoların kapağını Gemini ile yenile")
    ap.add_argument("--azami", type=int, default=5, help="bu koşuda işlenecek video sayısı")
    ap.add_argument("--video-id", help="yalnız bu videoyu işle")
    ap.add_argument("--kuru", action="store_true", help="üret ama yükleme")
    ap.add_argument("--cikti", default="/tmp/yeni_kapaklar", help="üretilen kapak klasörü")
    a = ap.parse_args()

    from modules import gemini_web, youtube_upload
    from modules.kapak_gorsel import gorseli_karesine_oturt

    if not gemini_web.hazir_mi():
        print("❌ GEMINI_COOKIES yok — kapak üretilemez")
        return 2

    kayitlar = arsiv_oku()
    if a.video_id:
        kayitlar = [k for k in kayitlar if k["video_id"] == a.video_id]
    else:
        # Yalnız yayında olanlar
        kayitlar = [k for k in kayitlar if not k["durum"] or k["durum"] == "yayinda"]
    kayitlar = kayitlar[: max(1, a.azami)]
    if not kayitlar:
        print("❌ İşlenecek video bulunamadı")
        return 1

    print(f"[KapakYenile] {len(kayitlar)} video işlenecek (kuru={a.kuru})")
    cikti = Path(a.cikti)
    cikti.mkdir(parents=True, exist_ok=True)

    tok = youtube_upload.token_yukle()
    access = youtube_upload.token_yenile(tok)
    if not access:
        print("❌ YouTube erişim jetonu alınamadı")
        return 2

    basarili = basarisiz = 0
    for k in kayitlar:
        vid = k["video_id"]
        baslik = k["baslik"]
        # KULLANICININ TEK İSTEMİ (K8) — ek kural yok
        istem = (
            f"{baslik} İsimli short video için kapak fotoğrafı istiyorum; etkileşim "
            "ve izlenme rekorları kırması için profesyonel şekilde tasarla. Kapak "
            "fotoğrafını gören merak edip tıklasın."
        )
        ham = gemini_web.gorsel_uret(istem, str(cikti / f"{vid}_ham.jpg"))
        if not ham:
            print(f"{vid} | URETIM_YOK | - | {gemini_web.durum().get('hata')}")
            basarisiz += 1
            continue
        kapak = gorseli_karesine_oturt(Path(ham), cikti / f"{vid}_kapak.jpg")
        if not kapak:
            print(f"{vid} | KIRPMA_HATASI | - | {ham}")
            basarisiz += 1
            continue
        if a.kuru:
            print(f"{vid} | KURU | gemini_web | {Path(kapak).name}")
            basarili += 1
            continue
        ok = youtube_upload._kapak_yukle(vid, str(kapak), access)
        print(
            f"{vid} | {'YUKLENDI' if ok else 'YUKLENEMEDI'} | gemini_web | "
            f"{Path(kapak).name} ({Path(kapak).stat().st_size // 1024} KB)"
        )
        if ok:
            basarili += 1
        else:
            basarisiz += 1

    print(f"=== Bitti: {basarili} başarılı, {basarisiz} başarısız ===")
    return 0 if basarili else 1


if __name__ == "__main__":
    raise SystemExit(main())
