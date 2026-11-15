"""Video son işleme — NotebookLM çıktısını yayına hazırlar.

İKİ İŞ (kullanıcı kararı 2026-11-08):
  1) **Bitiş kırpma** — NotebookLM videonun sonuna "Gemini Notebook" yazısı
     ekliyor. Bu bölüm HER ZAMAN kesilir.
  2) **Kapak gömme** — Gemini kapağı videonun İLK 1.5 saniyesine girer.

ÖLÇÜM (2026-11-08, /tmp/nb_kisa.mp4, 74.09 sn):
  son 30 sn 5 fps tarandı → parlaklık 216.1'den 246.0'a sıçradı
  kırpma noktası = 71.0 sn → outro 3.09 sn
  "yaklaşık son 4 saniye" tahmini DOĞRU çıktı; sabit sayı yerine ölçülüyor.

NEDEN SABİT SAYI DEĞİL: NotebookLM outro'yu her videoda aynı yere koymuyor.
Sabit "son 4 sn" yazsam bazen konuşmanın sonunu keserdim. Eşik tabanlı arama
(parlaklık > 238) outro'nun gerçek başlangıcını buluyor.

KULLANIM:
    python3 tools/video_son_isle.py /tmp/video.mp4 --kapak /tmp/kapak.jpg
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

#: Outro ekranının parlaklık eşiği (0-255). Saha ölçümü: içerik 216, outro 246.
#: 238 iki değerin ortasında ama outro'ya yakın — içeriğin açık sahnelerini
#: (beyaz arka planlı çizimler) yanlışlıkla kesmemek için.
OUTRO_PARLAKLIK = 238.0

#: Outro en az bu kadar uzunsa kesilir. Daha kısaysa zaten kesilmiş sayılır.
OUTRO_MIN_SN = 1.0

#: Kırpmadan sonra videonun kalan son kısmı bundan kısa olamaz.
KALAN_MIN_SN = 5.0

#: Outro araması videonun son kaç saniyesinde yapılır.
ARAMA_PENCERE_SN = 30.0

#: Kapak ekran süresi (kullanıcı kararı 2026-11-11).
KAPAK_SN = 1.5


def _ffmpeg() -> str:
    """ffmpeg yolunu çöz: PATH'te varsa onu, yoksa imageio paketini kullan."""
    yol = shutil.which("ffmpeg")
    if yol:
        return yol
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def _ffprobe() -> str | None:
    return shutil.which("ffprobe")


def video_bilgi(video: str) -> dict:
    """Süre + genişlik + yükseklik + fps. ffprobe yoksa ffmpeg çıktısından okur."""
    ff, fp = _ffmpeg(), _ffprobe()
    bilgi = {"sure": 0.0, "genislik": 0, "yukseklik": 0, "fps": 30.0}

    if fp:
        r = subprocess.run(
            [fp, "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height,r_frame_rate,duration",
             "-show_entries", "format=duration",
             "-of", "json", video],
            capture_output=True, text=True,
        )
        try:
            d = json.loads(r.stdout or "{}")
            st = (d.get("streams") or [{}])[0]
            bilgi["genislik"] = int(st.get("width") or 0)
            bilgi["yukseklik"] = int(st.get("height") or 0)
            hiz = str(st.get("r_frame_rate") or "30/1")
            if "/" in hiz:
                a, b = hiz.split("/")
                bilgi["fps"] = round(float(a) / float(b or 1), 3)
            sure = (d.get("format") or {}).get("duration") or st.get("duration")
            bilgi["sure"] = round(float(sure or 0), 3)
        except Exception:
            pass

    if not bilgi["sure"] or not bilgi["genislik"]:
        # Yedek: ffmpeg -i çıktısını (stderr) ayrıştır.
        r = subprocess.run([ff, "-i", video], capture_output=True, text=True)
        import re as _re

        m = _re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", r.stderr)
        if m:
            s, d, sn = m.groups()
            bilgi["sure"] = round(int(s) * 3600 + int(d) * 60 + float(sn), 3)
        m = _re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", r.stderr)
        if m:
            bilgi["genislik"], bilgi["yukseklik"] = int(m.group(1)), int(m.group(2))
        m = _re.search(r"(\d+(?:\.\d+)?) fps", r.stderr)
        if m:
            bilgi["fps"] = round(float(m.group(1)), 3)
    return bilgi


def _parlakliklar(video: str, baslangic: float, fps: float = 5.0) -> list[float]:
    """[baslangic, son] aralığını küçük gri kareler hâlinde okuyup ortalamasını verir.

    NİÇİN ham boru (pipe): 150 PNG yazıp tek tek açmak yerine tek ffmpeg
    çağrısı 90×160 gri bayt döndürüyor — 10 kat hızlı, disk kirletmiyor.
    """
    g, y = 90, 160
    r = subprocess.run(
        [_ffmpeg(), "-v", "error", "-ss", f"{max(0.0, baslangic):.3f}", "-i", video,
         "-vf", f"fps={fps},scale={g}:{y},format=gray",
         "-f", "rawvideo", "-"],
        capture_output=True,
    )
    ham = r.stdout or b""
    boyut = g * y
    return [
        sum(ham[i:i + boyut]) / boyut
        for i in range(0, len(ham) - boyut + 1, boyut)
    ]


def bitis_tespit(video: str, bilgi: dict | None = None) -> dict:
    """Outro'nun (Gemini Notebook yazısı) başladığı saniyeyi bulur.

    Döner: {"var": bool, "kesme_sn": float, "outro_sn": float, "parlaklik": float}
    `kesme_sn` = videonun yeni süresi (outro atıldığında).
    """
    bilgi = bilgi or video_bilgi(video)
    sure = bilgi["sure"]
    bos = {"var": False, "kesme_sn": sure, "outro_sn": 0.0, "parlaklik": 0.0}
    if sure < KALAN_MIN_SN * 2:
        return bos

    fps = 5.0
    baslangic = max(0.0, sure - ARAMA_PENCERE_SN)
    p = _parlakliklar(video, baslangic, fps)
    if not p:
        return bos

    # Sondan geriye: parlak (outro) olan kareleri atla, ilk içerik karesinde dur.
    i = len(p) - 1
    while i >= 0 and p[i] >= OUTRO_PARLAKLIK:
        i -= 1
    if i >= len(p) - 1:
        return bos                                  # sonda outro YOK
    sonraki = i + 1                                 # outro'nun ilk karesi
    kesme = baslangic + sonraki / fps
    outro = sure - kesme
    if outro < OUTRO_MIN_SN or kesme < KALAN_MIN_SN:
        return bos
    return {"var": True, "kesme_sn": round(kesme, 3),
            "outro_sn": round(outro, 3), "parlaklik": round(p[sonraki], 1)}


def bitis_kirp(video: str, hedef: str | None = None) -> dict:
    """Outro'yu keser. Outro yoksa videoya DOKUNMAZ (yeniden kodlamaz)."""
    bilgi = video_bilgi(video)
    tespit = bitis_tespit(video, bilgi)
    if not tespit["var"]:
        print(f"[son işle] outro bulunamadı — kırpma yok ({bilgi['sure']:.2f} sn)")
        return {**tespit, "video": video, "degisti": False}

    hedef = hedef or str(Path(video).with_name(Path(video).stem + "_kirpik.mp4"))
    r = subprocess.run(
        [_ffmpeg(), "-y", "-v", "error", "-i", video,
         "-t", f"{tespit['kesme_sn']:.3f}",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
         "-movflags", "+faststart", hedef],
        capture_output=True, text=True, timeout=900,
    )
    if r.returncode != 0 or not Path(hedef).exists() or Path(hedef).stat().st_size < 1000:
        print(f"[son işle] ❌ kırpma hatası: {(r.stderr or '')[-300:]}")
        return {**tespit, "video": video, "degisti": False}

    yeni = video_bilgi(hedef)
    print(f"[son işle] ✅ outro kesildi: {bilgi['sure']:.2f} → {yeni['sure']:.2f} sn "
          f"(-{tespit['outro_sn']:.2f} sn, parlaklık {tespit['parlaklik']})")
    return {**tespit, "video": hedef, "degisti": True,
            "eski_sure": bilgi["sure"], "yeni_sure": yeni["sure"]}


def kapak_gom(video: str, kapak_jpg: str, hedef: str | None = None,
              sn: float = KAPAK_SN) -> dict:
    """Kapağı videonun ilk `sn` saniyesine gömer.

    YÖNTEM: ayrı kapak klibi + concat demuxer. (2026-11-13'te `filter_complex`
    + `-loop 1` + `-shortest` denendi → "no packets" ile sessiz başarısızlık.
    concat yolu kanıtlanmış.)

    Kapak klibi videoyla AYNI çözünürlük/fps'te üretilir; yoksa concat patlar.
    """
    bilgi = video_bilgi(video)
    if not Path(kapak_jpg).exists():
        return {"video": video, "gomuldu": False, "hata": "kapak dosyası yok"}
    g, y = bilgi["genislik"] or 720, bilgi["yukseklik"] or 1280
    fps = bilgi["fps"] or 30.0
    hedef = hedef or str(Path(video).with_name(Path(video).stem + "_kapakli.mp4"))
    is_yeri = Path(hedef).parent
    sessiz = str(is_yeri / f"_{Path(video).stem}_kapakklip.mp4")
    liste = str(is_yeri / f"_{Path(video).stem}_concat.txt")

    r1 = subprocess.run(
        [_ffmpeg(), "-y", "-v", "error",
         "-loop", "1", "-t", f"{sn}", "-i", kapak_jpg,
         "-f", "lavfi", "-t", f"{sn}", "-i", "anullsrc=r=44100:cl=stereo",
         "-vf", f"scale={g}:{y}:force_original_aspect_ratio=increase,"
                f"crop={g}:{y},setsar=1,fps={fps}",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
         "-pix_fmt", "yuv420p", "-r", str(fps),
         "-c:a", "aac", "-b:a", "128k", "-shortest", sessiz],
        capture_output=True, text=True, timeout=300,
    )
    if r1.returncode != 0 or not Path(sessiz).exists():
        Path(sessiz).unlink(missing_ok=True)
        return {"video": video, "gomuldu": False,
                "hata": f"kapak klibi: {(r1.stderr or '')[-200:]}"}

    Path(liste).write_text(f"file '{sessiz}'\nfile '{video}'\n", encoding="utf-8")
    r2 = subprocess.run(
        [_ffmpeg(), "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", liste,
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
         "-pix_fmt", "yuv420p", "-r", str(fps),
         "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", hedef],
        capture_output=True, text=True, timeout=900,
    )
    for gecici in (sessiz, liste):
        Path(gecici).unlink(missing_ok=True)
    if r2.returncode != 0 or not Path(hedef).exists() or Path(hedef).stat().st_size < 1000:
        Path(hedef).unlink(missing_ok=True)
        return {"video": video, "gomuldu": False,
                "hata": f"birleştirme: {(r2.stderr or '')[-200:]}"}

    yeni = video_bilgi(hedef)
    print(f"[son işle] ✅ kapak gömüldü: {yeni['sure']:.2f} sn "
          f"({g}×{y}, ilk {sn} sn)")
    return {"video": hedef, "gomuldu": True, "sure": yeni["sure"],
            "genislik": yeni["genislik"], "yukseklik": yeni["yukseklik"]}


def son_isle(video: str, kapak_jpg: str = "", cikti: str | None = None) -> dict:
    """Tam zincir: kırp → kapak göm. Sıra ÖNEMLİ (önce kırp, sonra kapak)."""
    sonuc = {"girdi": video, "kapak": kapak_jpg or None, "cikti": video,
             "kirpma": None, "kapak_gomme": None, "hata": None}

    kirp = bitis_kirp(video)
    sonuc["kirpma"] = {k: kirp[k] for k in
                       ("var", "kesme_sn", "outro_sn", "degisti") if k in kirp}
    guncel = kirp["video"]

    if kapak_jpg:
        gom = kapak_gom(guncel, kapak_jpg)
        sonuc["kapak_gomme"] = gom
        if gom.get("gomuldu"):
            guncel = gom["video"]
        else:
            sonuc["hata"] = f"kapak gömülemedi: {gom.get('hata')}"

    sonuc["cikti"] = guncel
    sonuc["bilgi"] = video_bilgi(guncel)
    return sonuc


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="NotebookLM videosu → yayına hazır")
    ap.add_argument("video")
    ap.add_argument("--kapak", default="")
    ap.add_argument("--cikti", default=None)
    ap.add_argument("--olc", action="store_true", help="sadece ölç, dosya yazma")
    a = ap.parse_args()

    if a.olc:
        b = video_bilgi(a.video)
        t = bitis_tespit(a.video, b)
        print(json.dumps({"bilgi": b, "outro": t}, ensure_ascii=False, indent=1))
        return 0

    s = son_isle(a.video, a.kapak, a.cikti)
    print(json.dumps(s, ensure_ascii=False, indent=1))
    return 0 if not s.get("hata") else 1


if __name__ == "__main__":
    sys.exit(main())
