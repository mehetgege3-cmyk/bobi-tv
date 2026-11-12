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

            # ------------------------------------------------------------------
            # SÜREÇ ZİNCİRİ (2026-11-11 canlı koşu bulgusu): yeni hat yalnız
            # senaryo paketi üretiyordu; seslendirme/render yapılmadığı için
            # main_pipeline "final_video yok → üretim başarısız" diyordu ve
            # HİÇ video yayınlanmadı (run 43111414945: "0 yayınlandı").
            # Burada seslendirme + render + kapak adımları çalıştırılır.
            # ------------------------------------------------------------------
            from modules.tts_engine import senaryo_seslendir
            from modules.video_render import video_render, video_kalite_kontrol

            paket = senaryo_seslendir(paket)
            video_yolu = video_render(paket)
            paket["final_video"] = video_yolu

            # Kapak: 1. kare + Arena/yerel şok başlık (otomatik seçim)
            try:
                from modules.kapak_arena import kapak_sec_ve_hazirla

                kapak_sec_ve_hazirla(paket)
            except Exception as kapak_hatasi:
                print(f"[İlginçBilgi] ⚠️ Kapak hattı: {str(kapak_hatasi)[:120]} (yerel üretici)")
                from modules.kapak_uret import kapak_uret

                kapak_uret(paket)

            try:
                qc = video_kalite_kontrol(video_yolu)
                paket["video_suresi"] = qc.get("sure", 0)
                print(
                    f"[İlginçBilgi] 🎬 Render tamam: {qc.get('sure')}sn | "
                    f"{os.path.getsize(video_yolu)//1024} KB"
                )
            except Exception as qc_hatasi:
                print(f"[İlginçBilgi] ⚠️ QC uyarısı: {str(qc_hatasi)[:150]}")
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
