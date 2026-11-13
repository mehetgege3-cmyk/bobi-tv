"""
BOBİ TV — Arena AI Üretim Wrapper
İLGİNÇ BİLGİ HATTI (tek üretim yolu). Arena tamamen KALDIRILDI; içerik
Gemini web çerezinden gelir (`modules/gemini_web.py`).

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



def ilginc_bilgi_aktif() -> bool:
    """Yeni içerik hattı açık mı? (env: ILGINC_BILGI_AKTIF=0 → eski hat)"""
    return os.environ.get("ILGINC_BILGI_AKTIF", "1").strip().lower() not in ("0", "false", "hayir", "hayır")


def uretim_hatti_calistir(video_no: int) -> dict | None:
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

            # KAPAK (2026-11-12): Arena tam metni okur → GÖRSEL üretir →
            # indirilir → videonun 1. karesine yerleşir. Aday/skor hattı SİLİNDİ.
            try:
                from modules.kapak_hatti import kapak_uret_ve_yerlestir

                kapak_sonuc = kapak_uret_ve_yerlestir(paket)
                # KÖK NEDEN (2026-11-13, yt-dlp + artifact kanıtı): kapak
                # `..._kapakli.mp4` dosyasına gömülüyordu ama `paket["final_video"]`
                # GÜNCELLENMİYORDU → YouTube'a KAPAKSIZ orijinal gidiyordu.
                # Kanıt: YouTube'daki videonun 1. karesi boş şablon ({ karakterleri),
                # artifact'taki `_kapakli.mp4` 1. karesi ise kapak görseli.
                video_yolu = kapak_sonuc.get("video") or video_yolu
                paket["final_video"] = video_yolu
                if kapak_sonuc.get("kapak"):
                    paket["kapak_dosyasi"] = kapak_sonuc["kapak"]
                    paket["kapak_yolu"] = kapak_sonuc["kapak"]
                    paket["kapak_ilk_kare"] = bool(kapak_sonuc.get("ilk_kare"))
                    paket["kapak_kaynagi"] = kapak_sonuc.get("kaynak", "")
                    senaryo = paket.setdefault("senaryo", {})
                    senaryo["kapak_dosyasi"] = kapak_sonuc["kapak"]
                    senaryo["kapak_yolu"] = kapak_sonuc["kapak"]
            except Exception as kapak_hatasi:
                print(f"[İlginçBilgi] ⚠️ Kapak hattı: {str(kapak_hatasi)[:120]}")

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

    # ESKİ DİYALOG HATTI SİLİNDİ (2026-11-13): arena_api'ye bağlıydı ve Arena
    # tamamen çöpe atıldı. `ILGINC_BILGI_AKTIF=0` artık desteklenmiyor —
    # tek içerik hattı ilginç-bilgi (Gemini web çerezi).
    print("[Üretim] ILGINC_BILGI_AKTIF=0: eski diyalog hattı kaldırıldı")
    return None
