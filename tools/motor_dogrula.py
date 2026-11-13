"""Üretilen motoru GERÇEKTEN çalıştırıp doğrular.

NİÇİN: Sözdizimi geçen kod çalışan kod değildir. Gemini'nin yazdığı motor
ilk turda `google-genai` (kurulu değil, API anahtarı da yok) ve `dosya_adi`
(zorunlu alan) yüzünden çalışamazdı. Bu betik motoru uçtan uca koşar.

NASIL: `video_yukle` stub'lanır (YouTube'a yüklemez), `video_uret(1)` çağrılır,
çıkan MP4 ffprobe ile denetlenir: 1080x1920, ses akışı var, 5-70 sn.

ÇIKTI: docs/MOTOR_DOGRULAMA.json — geçti mi, süre, çözünürlük, hata izi.
"""
from __future__ import annotations

import json
import subprocess
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

RAPOR = Path("docs/MOTOR_DOGRULAMA.json")


def _ffprobe(yol: str) -> dict:
    try:
        cikti = subprocess.run(
            ["ffprobe", "-v", "error", "-print_format", "json",
             "-show_format", "-show_streams", yol],
            capture_output=True, text=True, timeout=90,
        )
        return json.loads(cikti.stdout or "{}")
    except Exception as e:
        return {"hata": f"{type(e).__name__}: {e}"}


def main() -> int:
    rapor: dict = {"gecti": False, "paket": None, "probe": None, "hata": None, "traceback": None}

    # YouTube yüklemesini stub'la — doğrulamada kanala video gitmesin.
    import modules.youtube_upload as yu

    yuklenen: list = []

    def _stub(paket):
        yuklenen.append(paket)
        print(f"[doğrula] video_yukle stub'landı: {paket.get('baslik')}")
        return "STUB_ID"

    yu.video_yukle = _stub

    try:
        from modules.yeni_motor import motor

        # Motor `from modules.youtube_upload import video_yukle` ile aldıysa
        # stub devreye girmez; motorun ad alanını da yamala.
        if hasattr(motor, "video_yukle"):
            motor.video_yukle = _stub

        paket = motor.video_uret(1)
        rapor["paket"] = {k: v for k, v in (paket or {}).items() if k != "final_video"}
        video = (paket or {}).get("final_video")
        if not video or not Path(video).exists():
            raise RuntimeError(f"final_video yok veya dosya yok: {video}")

        pr = _ffprobe(video)
        rapor["probe"] = pr
        if pr.get("hata"):
            raise RuntimeError(f"ffprobe: {pr['hata']}")

        akislar = pr.get("streams", [])
        video_akis = [s for s in akislar if s.get("codec_type") == "video"]
        ses_akis = [s for s in akislar if s.get("codec_type") == "audio"]
        sure = float(pr.get("format", {}).get("duration", 0) or 0)

        if not video_akis:
            raise RuntimeError("video akışı yok")
        if not ses_akis:
            raise RuntimeError("ses akışı yok — video sessiz")
        gen, yuk = int(video_akis[0].get("width", 0)), int(video_akis[0].get("height", 0))
        if (gen, yuk) != (1080, 1920):
            raise RuntimeError(f"çözünürlük {gen}x{yuk}, beklenen 1080x1920")
        if not (5.0 <= sure <= 70.0):
            raise RuntimeError(f"süre {sure:.1f} sn, 5-70 aralığı dışında")

        # --- KAPAK (2026-11-13 kullanıcı bildirimi: kapak yapılmıyordu) ----
        kapak = (paket or {}).get("kapak_dosyasi", "")
        if not kapak or not Path(kapak).exists():
            raise RuntimeError(
                "kapak_dosyasi boş veya dosya yok — video kapaksız yayınlanır"
            )
        kboyut = Path(kapak).stat().st_size
        if kboyut < 10_000:
            raise RuntimeError(f"kapak çok küçük: {kboyut} bayt")
        if kboyut > 2 * 1024 * 1024:
            raise RuntimeError(f"kapak 2 MB üstü: {kboyut} bayt (YouTube reddeder)")
        from PIL import Image

        with Image.open(kapak) as ki:
            kg, ky = ki.size
        rapor["kapak"] = {"yol": Path(kapak).name, "boyut_kb": kboyut // 1024,
                          "olcu": f"{kg}x{ky}"}

        rapor["gecti"] = True
        rapor["olcum"] = {"sure_sn": round(sure, 2), "cozunurluk": f"{gen}x{yuk}",
                          "ses": ses_akis[0].get("codec_name"), "boyut_kb": Path(video).stat().st_size // 1024}
        print(f"[doğrula] ✅ GEÇTİ — {sure:.1f} sn, {gen}x{yuk}, "
              f"ses={ses_akis[0].get('codec_name')}, kapak={rapor['kapak']['olcu']} "
              f"{rapor['kapak']['boyut_kb']}KB")
    except Exception as e:
        rapor["hata"] = f"{type(e).__name__}: {str(e)[:400]}"
        rapor["traceback"] = traceback.format_exc()[-2500:]
        print(f"[doğrula] ❌ {rapor['hata']}")

    RAPOR.parent.mkdir(exist_ok=True)
    RAPOR.write_text(json.dumps(rapor, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if rapor["gecti"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
