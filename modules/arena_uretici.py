"""
BOBİ TV — Arena AI Üretim Wrapper
arena_api.py'nin sync wrapper'ı + İLGİNÇ BİLGİ HATTI (yeni format).

FORMAT DEVRİMİ (2026-11-11, kullanıcı):
  "Bu kategorileri, formatı ve konuların hepsini çöpe at."
  Yeni format: 🧠 Günün Merak Uyandıran Sorusu / 🔍 Cevabı Biliyor Muydun?
  (200-300 kelime) / 💡 Şaşırtıcı Sonuç — 8 kategori, tek anlatıcı.

ANAHTAR: `ILGINC_BILGI_AKTIF` (varsayılan "1"). "0" yapılırsa eski VS/diyalog
hattı çalışır (geri dönüş sigortası). Yeni hat Arena'yı kullanır; Arena
erişilemezse doğrulanmış bilgi bankasına düşer (üretim durmaz).
"""
import asyncio
import os

from modules.arena_api import arena_video_uret


def ilginc_bilgi_aktif() -> bool:
    """Yeni içerik hattı açık mı? (env: ILGINC_BILGI_AKTIF=0 → eski hat)"""
    return os.environ.get("ILGINC_BILGI_AKTIF", "1").strip().lower() not in ("0", "false", "hayir", "hayır")


def arena_tam_uretim(video_no: int) -> dict | None:
    """
    Sync wrapper: Arena video üretimi.
    Döner: {baslik, aciklama, final_video, ...} veya None
    """
    if ilginc_bilgi_aktif():
        try:
            from modules.ilginc_bilgi import uretici

            sonuc = uretici.uret(video_no)
            paket = sonuc["paket"]
            print(
                f"[İlginçBilgi] ✅ #{video_no} {sonuc['kategori']} | {sonuc['taktik']} | "
                f"skor {sonuc['rapor'].skor} | {sonuc['kaynak_turu']} | "
                f"{paket['senaryo']['kelime_sayisi']} kelime"
            )
            for uyari in sonuc["uyarilar"]:
                print(f"[İlginçBilgi] ℹ️ {uyari}")
            return paket
        except Exception as e:
            print(f"[İlginçBilgi] Üretim hatası: {str(e)[:200]}")
            return None

    # --- Geri dönüş yolu: eski VS / iki karakterli diyalog hattı ---
    try:
        return asyncio.run(arena_video_uret(video_no))
    except Exception as e:
        print(f"[Arena] Üretim hatası: {e}")
        return None
