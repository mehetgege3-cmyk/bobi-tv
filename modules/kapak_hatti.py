"""KAPAK HATTI — tek yol: GEMINI WEB ÇEREZİ (2026-11-13 kullanıcı kararı).

KULLANICI: "Bu sorunsuz çalışıyor; Arena AI'yi ve Gemini API'yi çöpe at. Artık
bunu kullanalım, Gemini cookie işimize yarar."

SIRA (tek yol + iki yedek):
  1) **Gemini WEB** (GEMINI_COOKIES) → `kaynak=gemini_web`   ← ANA YOL
  2) video karesi (Gemini erişilemezse) → `kaynak=video_karesi`
     Üretim DURMAZ; uydurma yok, sessiz yalan yok.

ÇÖPE ATILANLAR (kullanıcı talimatı, 2026-11-13):
  • Arena AI kapak yolu (`arena_kapak_gorseli_uret`) — Arena'nın çerezi ölü,
    görsel hattı çalışmıyor.
  • Gemini API (`GEMINI_API_KEY`) yolu — görsel kotası `limit: 0`
    (`docs/GEMINI_ENTEGRASYON.md` §9: ücretsiz katmanda görsel üretimi YOK).

İSTEM: `kapak_gorsel.gorsel_promptu` = `<video başlığı>` + kullanıcının tek
cümlesi. Ek kural YOK (K8).

Görsel 1080×1920'ye kırpılır ve videonun 1. KARESİNE yerleştirilir.
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

    sonuc: dict[str, Any] = {
        "kapak": "", "kaynak": "yok", "video": video, "ilk_kare": False,
    }

    # --- 1) GEMINI WEB (çerez) — ANA YOL ------------------------------------
    # CANLI KANIT: koşu 43378192358 → kaynak=gemini_web, 1080×1920,
    # https://www.youtube.com/shorts/pQOvBWcegNc
    if not sonuc["kapak"]:
        try:
            from modules import gemini_web

            if gemini_web.hazir_mi():
                from modules.kapak_gorsel import gorsel_promptu, gorseli_karesine_oturt

                ham_w = gemini_web.gorsel_uret(
                    gorsel_promptu(paket), str(cikis / f"{dosya_adi}_gemini_web.jpg")
                )
                if ham_w:
                    kirp = gorseli_karesine_oturt(
                        Path(ham_w), cikis / f"{dosya_adi}_kapak.jpg"
                    )
                    if kirp:
                        sonuc.update(kapak=str(kirp), kaynak="gemini_web")
                else:
                    print(
                        f"[Kapak] Gemini web görsel vermedi: "
                        f"{gemini_web.durum().get('hata')}"
                    )
            else:
                print("[Kapak] GEMINI_COOKIES yok — video karesine düşülecek")
        except Exception as e:
            print(f"[Kapak] Gemini web yolu hatası: {str(e)[:120]}")

    # --- 2) YEDEK: video karesi (Gemini erişilemezse üretim DURMAZ) ---------
    if not sonuc["kapak"]:
        try:
            from modules import kapak_arena

            kare = kapak_arena.ilk_kare_cikar(video, str(cikis / f"{dosya_adi}_kare0.jpg"))
            if kare:
                hedef = cikis / f"{dosya_adi}_kapak.jpg"
                import shutil as _sh

                _sh.copyfile(kare, hedef)
                sonuc.update(kapak=str(hedef), kaynak="video_karesi")
                print("[Kapak] Gemini yok — video karesi kullanıldı (yedek)")
        except Exception as e:
            print(f"[Kapak] Video karesi yedeği hatası: {str(e)[:120]}")

    # --- 3) Kapağı videonun 1. karesine göm ---------------------------------
    if sonuc["kapak"] and video:
        try:
            from modules import kapak_arena

            kapakli = kapak_arena.ilk_kareye_yerlestir(video, sonuc["kapak"])
            if kapakli:
                sonuc.update(video=str(kapakli), ilk_kare=True)
                print(f"[Kapak] ✅ Kapak videonun 1. karesine yerleştirildi: "
                      f"{Path(kapakli).name}")
        except Exception as e:
            print(f"[Kapak] 1. kareye yerleştirme hatası: {str(e)[:120]}")

    # --- 4) Paket alanlarını doldur (YouTube yüklemesi bunları okur) --------
    # CANLI HATA (43266695264): kapak üretildi ama YouTube'a "Kapak dosyası
    # yok: (boş)" dedi — çünkü paket alanları doldurulmuyordu. Sözleşme:
    # kapak üretildiyse paket kapak_dosyasi/kapak_yolu/kapak_kaynagi/
    # kapak_ilk_kare alanlarıyla işaretlenir.
    if sonuc["kapak"]:
        paket["kapak_dosyasi"] = sonuc["kapak"]
        paket["kapak_yolu"] = sonuc["kapak"]
        paket["kapak_kaynagi"] = sonuc["kaynak"]
        paket["kapak_ilk_kare"] = bool(sonuc["ilk_kare"])

    return sonuc
