"""Hat çıktısını YouTube'a yükle — mevcut `youtube_upload` yolunu kullanır.

NİÇİN AYRI DOSYA: `tools/notebook_hat.py` SADECE üretir; yükleme
`modules/youtube_upload.video_yukle()`'in işi. 2026-11-13'te motorun kendi
içinden yükleme yapması çift yükleme hatasına yol açmıştı — aynı hata
tekrarlanmasın diye sorumluluk ayrı tutuluyor.

Girdi : /tmp/hat_sonuc.json (notebook_hat.py'nin çıktısı)
Çıktı : stdout'a yayın URL'si, arşive kayıt, Telegram bildirimi
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

RAPOR = Path("/tmp/hat_sonuc.json")


def main() -> int:
    if not RAPOR.exists():
        print(f"❌ {RAPOR} yok — üretim tamamlanmamış, yükleme yapılmıyor.")
        return 1

    rapor = json.loads(RAPOR.read_text(encoding="utf-8"))
    if rapor.get("hata"):
        # KAPAKSIZ / EKSİK VİDEO YAYINLANMAZ (kullanıcı kararı).
        print(f"❌ Üretim hatası: {rapor['hata']}")
        print("Yükleme YAPILMADI.")
        return 1

    paket = rapor.get("paket") or {}
    video = paket.get("final_video")
    kapak = paket.get("kapak_dosyasi")
    if not video or not Path(video).exists():
        print(f"❌ video dosyası yok: {video}")
        return 1
    if not kapak or not Path(kapak).exists():
        print(f"❌ kapak dosyası yok: {kapak} — yükleme YAPILMADI.")
        return 1

    print(f"→ video : {video} ({Path(video).stat().st_size / 1e6:.1f} MB)")
    print(f"→ kapak : {kapak}")
    print(f"→ başlık: {paket.get('baslik')}")

    from modules.youtube_upload import video_yukle

    try:
        video_id = video_yukle(paket)
    except Exception as e:
        print(f"❌ YÜKLEME HATASI: {type(e).__name__}: {e}")
        return 1

    url = f"https://www.youtube.com/shorts/{video_id}"
    print(f"✅ YAYINDA: {url}")
    print(f"   kapak yüklendi: {paket.get('kapak_yuklendi')}")

    rapor["yayin"] = {"video_id": video_id, "url": url,
                      "kapak_yuklendi": paket.get("kapak_yuklendi")}
    RAPOR.write_text(json.dumps(rapor, ensure_ascii=False, indent=1), encoding="utf-8")

    try:
        from modules.telegram_notify import send_message

        sure = (rapor.get("video") or {}).get("sure")
        send_message(
            f"🎬 <b>BOBİ TV — NotebookLM videosu yayında</b>\n"
            f"🎥 {paket.get('baslik', '')[:70]}\n"
            f"⏱️ {sure} sn\n"
            f"🖼️ Kapak: {'✅' if paket.get('kapak_yuklendi') else '❌'}\n"
            f"🔗 {url}"
        )
    except Exception as e:
        print(f"[uyarı] Telegram bildirimi gönderilemedi: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
