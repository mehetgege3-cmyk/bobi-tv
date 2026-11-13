"""KAPAK HATTI — tek yol (2026-11-12 kullanıcı kararı).

KULLANICI: "Mevcut tüm kuralları çöpe at… Arena AI'ye videonun tam metnini ver,
metni okusun, tıklamaya/izlemeye/etkileşime teşvik eden profesyonel bir Short
kapağı ÜRETSİN. Oluşturduğu resmi indir, videonun İLK KARESİNE yerleştir ve
seçilsin. Diğer tüm saçmalıkları çöpe at."

ESKİ HAT (SİLİNDİ): A/B/C/D adayları, okunabilirlik skoru, sınır testleri,
"sok_baslik/vurgu_kelime/renk" JSON şeması, 1. kareden kapak türetme, yerel
VS/Clash kapak üreticisi (kapak_uret), Arena şok başlık JSON önerisi
(arena_kapak_onerisi_al). `modules/kapak_arena.py` artık YALNIZ mekanik
yardımcıları taşır (kare çıkarma / başlık bindirme / 1. kareye yerleştirme).

YENİ HAT:
  1) Arena'ya videonun TAM metni gider → Arena kapak GÖRSELİ üretir.
  2) Görsel indirilir, 1080x1920'ye kırpılır.
  3) Görsel final videonun 1. KARESİNE yerleştirilir (kapak = 1. kare).
  4) Arena görsel üretemezse: video karesi + videonun kendi başlığı (tek kapak).
     Üretim durmaz, uydurma yok, sessiz yalan yok.
"""

from __future__ import annotations

import os

from pathlib import Path
from typing import Any

from modules import calisma_dizinleri


def kapak_uret_ve_yerlestir(paket: dict[str, Any]) -> dict[str, Any]:
    """Kapak üretir ve videonun 1. karesine yerleştirir (pipeline tek çağrı)."""
    video = str(paket.get("final_video") or "")
    dosya_adi = str(paket.get("dosya_adi") or "video")
    cikis = calisma_dizinleri.OUTPUT_YOLU
    cikis.mkdir(parents=True, exist_ok=True)

    sonuc: dict[str, Any] = {"kapak": "", "kaynak": "yok", "video": video, "ilk_kare": False}

    # --- 1) Arena: tam metni oku → kapak GÖRSELİ üret -----------------------
    ham: Path | None = None
    try:
        from modules.kapak_gorsel import arena_kapak_gorseli_uret, gorseli_karesine_oturt

        ham = arena_kapak_gorseli_uret(paket)
        if ham:
            kapak_yolu = cikis / f"{dosya_adi}_kapak.jpg"
            kırpılmış = gorseli_karesine_oturt(ham, kapak_yolu)
            if kırpılmış:
                sonuc.update(kapak=str(kırpılmış), kaynak="arena_gorsel")
    except Exception as e:
        print(f"[Kapak] Arena görsel hattı hatası: {str(e)[:140]}")

    # --- 1a) GEMINI WEB görseli (ÇEREZ) — EN GÜVENİLİR YOL ------------------
    # CANLI KANIT (2026-11-13): GEMINI_COOKIES ile StreamGenerate →
    # HTTP 200, 238.200 bayt JPEG, 1408×768 (kanit/gemini/modul_test.png).
    # API anahtarı DEĞİL, web oturum çerezi; abonelik kotasını kullanır.
    if not sonuc["kapak"]:
        try:
            from modules import gemini_web

            if gemini_web.hazir_mi():
                from modules.kapak_gorsel import gorsel_promptu

                from pathlib import Path as _P

                # KULLANICI (2026-11-13): "A olsun. Eski kuralları çöpe atıyoruz."
                # İsteme HİÇBİR ek yapılmaz — ne dikey zorlaması ne "yazı koyma".
                # Görsel, kullanıcının cümlesinin doğal sonucu olarak üretilir
                # (yazı eklemesi serbest). Dikey kırpma yine yapılır (Shorts
                # kapağı 1080×1920 olmak zorunda) ama istem yönlendirilmez.
                ham_w = gemini_web.gorsel_uret(
                    gorsel_promptu(paket), str(cikis / f"{dosya_adi}_gemini_web.jpg")
                )
                if ham_w:
                    from modules.kapak_gorsel import gorseli_karesine_oturt

                    kirp = gorseli_karesine_oturt(_P(ham_w), _P(cikis) / f"{dosya_adi}_kapak.jpg")
                    if kirp:
                        sonuc.update(kapak=str(kirp), kaynak="gemini_web")
                else:
                    print(f"[Kapak] Gemini web görsel vermedi: {gemini_web.durum().get('hata')}")
        except Exception as e:
            print(f"[Kapak] Gemini web yolu hatası: {str(e)[:120]}")

    # --- 1b) GEMINI API görsel yedeği (kota varsa) --------------------------
    # Ölçüm 2026-11-13: görsel modelleri "limit: 0" (ücretsiz katmanda yok).
    # Kota açılırsa bu yol OTOMATİK devreye girer; ek kod gerekmez.
    if not sonuc["kapak"]:
        try:
            from modules import gemini_api

            if gemini_api.anahtar():
                from modules.kapak_gorsel import gorsel_promptu

                ham_g = gemini_api.gorsel_uret(
                    gorsel_promptu(paket),
                    str(cikis / f"{dosya_adi}_gemini_ham.png"),
                )
                if ham_g:
                    from modules.kapak_gorsel import gorseli_karesine_oturt

                    from pathlib import Path as _P2

                    kirp = gorseli_karesine_oturt(_P2(ham_g), _P2(cikis) / f"{dosya_adi}_kapak.jpg")
                    if kirp:
                        sonuc.update(kapak=str(kirp), kaynak="gemini_gorsel")
                else:
                    print(f"[Kapak] Gemini görsel vermedi: {gemini_api.durum().get('hata')}")
        except Exception as e:
            print(f"[Kapak] Gemini yolu hatası: {str(e)[:120]}")

    # --- 2) Yedek: video karesi + videonun kendi başlığı --------------------
    if not sonuc["kapak"] and video:
        try:
            from modules import kapak_arena

            kare = cikis / f"{dosya_adi}_kare0.jpg"
            if kapak_arena.ilk_kare_cikar(video, str(kare)):
                hedef = cikis / f"{dosya_adi}_kapak.jpg"
                baslik = str(
                    (paket.get("senaryo") or {}).get("kapak_baslik")
                    or (paket.get("senaryo") or {}).get("baslik")
                    or paket.get("baslik")
                    or ""
                )
                # KUSUR DÜZELTMESİ (2026-11-13, koşu 43325201001):
                # Animasyon 1. kareye başlığı ZATEN basıyor (sarı rozet).
                # Üstüne ikinci bant basılınca başlık çakışıyordu:
                #   "EKMEK NEDEN FIRINDAN ÇIKINCA BU KA" iki kez üst üste.
                # Video karesinde başlık varsa TEKRAR BASMA; Arena görselinde
                # (yazısız) basmaya devam et.
                if baslik.strip() and os.environ.get("KAPAK_BASLIK_BINDIR", "0") == "1":
                    if kapak_arena.baslik_kaplama_jpg(str(kare), str(hedef), baslik):
                        sonuc.update(kapak=str(hedef), kaynak="video_karesi")
                else:
                    import shutil as _sh

                    _sh.copyfile(kare, hedef)
                    sonuc.update(kapak=str(hedef), kaynak="video_karesi")
        except Exception as e:
            print(f"[Kapak] Yedek kapak hatası: {str(e)[:140]}")

    # --- 3) Kapağı videonun 1. karesine yerleştir ---------------------------
    if sonuc["kapak"] and video:
        try:
            from modules import kapak_arena

            yeni_video = kapak_arena.ilk_kareye_yerlestir(video, sonuc["kapak"])
            if yeni_video and Path(yeni_video).exists():
                paket["final_video"] = yeni_video
                sonuc["video"] = yeni_video
                sonuc["ilk_kare"] = True
                paket["kapak_ilk_kare"] = True
                print(f"[Kapak] ✅ Kapak videonun 1. karesine yerleştirildi: {Path(yeni_video).name}")
        except Exception as e:
            print(f"[Kapak] 1. kareye yerleştirme hatası: {str(e)[:140]}")

    if sonuc["kapak"]:
        # YouTube yüklemesi ve log bu alanları okur (kapak_dosyasi = JPEG)
        paket["kapak_dosyasi"] = sonuc["kapak"]
        paket["kapak_yolu"] = sonuc["kapak"]
        paket["kapak_kaynagi"] = sonuc["kaynak"]
        paket.setdefault("kapak_ilk_kare", False)
        print(f"[Kapak] Seçilen: {Path(sonuc['kapak']).name} | kaynak={sonuc['kaynak']}")
    else:
        print("[Kapak] ⚠️ Kapak üretilemedi — video kapaksız yüklenecek (üretim sürer)")
    return sonuc
