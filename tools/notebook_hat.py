"""NotebookLM hattı — konu üret → video üret → kırp → kapak göm → paketle.

TAM ZİNCİR (kullanıcı isteği 2026-11-08):
    Gemini web (konu + kapak) → NotebookLM (video) → son işleme → YouTube

YÜKLEME YAPMAZ. YouTube yüklemesi `main_pipeline`'ın işi (`toplu_yukle`) —
tek sorumluluk ilkesi (2026-11-13 kararı, çift yükleme hatası tekrarlanmasın).

ÖLÇÜLEN SÜRELER (2026-11-08, canlı):
    konu (Gemini web)   : ~20-60 sn
    kapak (Gemini web)  : ~40-90 sn
    video (NotebookLM)  : 285-632 sn   ← değişken, sıraya bağlı
    kırpma + kapak gömme: ~25 sn
    TOPLAM              : 6-13 dk

KULLANIM:
    python3 tools/notebook_hat.py --video-no 12
    python3 tools/notebook_hat.py --video-no 12 --kategori hayvanlar

ÇIKTI: /tmp/bobi_<slug>_<damga>.mp4 + /tmp/bobi_kapak_<damga>.jpg
stdout'a paket JSON'u basar (final_video, baslik, kapak_dosyasi, ...).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import video_son_isle as son  # noqa: E402

#: YouTube Shorts tavanı 180 sn; güvenlik payı bırakıyoruz.
UST_SN = 179.0


def _kimlik_kur() -> str:
    """NotebookLM kimliğini kur — TAZELENMIŞ çerezi tercih eder.

    NİÇİN: `__Secure-1PSIDTS` saatte bir dönüyor. `notebook_cerez_tazele.py`
    tazelenmiş storage_state'i /tmp/nb_state.json'a yazar. O dosya varsa
    onu kullanırız; yoksa secret'tan doğrudan kurarız (eski davranış).
    """
    from tools.notebook_video import _depo_hazirla

    taze = Path("/tmp/nb_state.json")
    if taze.exists():
        try:
            veri = json.loads(taze.read_text(encoding="utf-8"))
            if veri.get("cookies"):
                os.environ["NOTEBOOKLM_AUTH_JSON"] = taze.read_text(encoding="utf-8")
                print(f"→ kimlik: tazelenmiş çerez ({len(veri['cookies'])} adet)")
                return "taze"
        except Exception as e:
            print(f"[hat] taze çerez okunamadı ({e}) — secret'a düşülüyor")
    os.environ["NOTEBOOKLM_AUTH_JSON"] = json.dumps(_depo_hazirla())
    print("→ kimlik: secret çerezi (tazelenmemiş)")
    return "secret"


def _paket(konu: dict, video: str, kapak: str, damga: str) -> dict:
    """main_pipeline / youtube_upload sözleşmesine uygun paket."""
    return {
        "dosya_adi": Path(video).stem,
        "final_video": video,
        "baslik": f"{konu['baslik']}"[:95],
        "etiketler": konu.get("etiketler", ["shorts"]),
        "kapak_dosyasi": kapak,
        "senaryo": {
            # Promptun AÇIKLAMA bölümü (merak cümlesi + yorum sorusu +
            # "Bunu bilmeyen bir arkadaşını etiketle!").
            "aciklama_metni": konu.get("aciklama") or konu["metin"],
            "kaynaklar": [],
            "kategori": konu.get("kategori", ""),
            "sabit_yorum": konu.get("konu", ""),
            "etkilesim": "Bunu bilmeyen bir arkadaşını etiketle!",
        },
        "kategori": konu.get("kategori", ""),
        "damga": damga,
    }


def calistir(video_no: int = 0, kategori: str | None = None,
             konu: dict | None = None, uret: bool = True) -> dict:
    """Hattı çalıştırır. `konu` verilirse Gemini konu adımı atlanır (test için)."""
    from modules.gemini_web import gorsel_uret
    from modules.yeni_motor.motor import kapak_istemini_yaz
    from tools.konu_uret import konu_uret
    from tools.notebook_video import _depo_hazirla, _slug, _uret

    t0 = time.time()
    damga = datetime.now().strftime("%Y%m%d_%H%M%S")
    rapor = {"asamalar": {}, "hata": None}

    # --- 1) KONU -----------------------------------------------------------
    if konu is None:
        print("\n=== 1/4 KONU (Gemini web — kullanıcının promptu) ===")
        t = time.time()
        konu = konu_uret(video_no, kategori)
        rapor["asamalar"]["konu"] = round(time.time() - t, 1)
        if not konu:
            return {**rapor, "hata": "konu üretilemedi (Gemini cevap yok/JSON bozuk)"}
    print(f"→ {konu['baslik']}  [{konu.get('kelime')} kelime]")
    print(f"→ konu: {konu.get('konu', '')}")
    try:
        from tools.konu_uret import konu_kaydet

        konu_kaydet(konu.get("konu", ""))
    except Exception as e:
        print(f"[uyarı] konu kaydedilemedi: {e}")
    rapor["konu"] = konu

    # --- 2) KAPAK (Gemini web) --------------------------------------------
    ham_kapak = f"/tmp/bobi_kapak_ham_{damga}.jpg"
    kapak = f"/tmp/bobi_kapak_{damga}.jpg"          # 9:16 — videoya gömülür
    kapak_yt = f"/tmp/bobi_kapak_yt_{damga}.jpg"    # 16:9 — thumbnails.set
    print("\n=== 2/4 KAPAK (Gemini web) ===")
    t = time.time()
    try:
        uretildi = gorsel_uret(kapak_istemini_yaz(konu["baslik"]), ham_kapak)
    except Exception as e:
        uretildi = None
        print(f"[hat] kapak istisnası: {type(e).__name__}: {e}")
    rapor["asamalar"]["kapak"] = round(time.time() - t, 1)
    if not uretildi or not Path(ham_kapak).exists():
        # KAPAK OLMADAN YAYIN YOK (kullanıcı kararı) → hat burada durur.
        return {**rapor, "hata": "kapak üretilemedi — kapaksız video yayınlanmaz"}

    # İKİ SÜRÜM (2026-11-08 regresyon düzeltmesi):
    #   dikey : 1080x1920, görselin TAMAMI (contain) → videonun ilk 1.5 sn'si.
    #           Kırpma YOK; 8f7398a'daki "cover" kırpması metnin %44'ünü
    #           kesiyordu ("İNİZ", "DİNİ NASIL YİY").
    #   16:9   : 1280x720, ortada net görsel + kenarlarda bulanık dolgu
    #           → thumbnails.set (2 gün önceki videolarla aynı görünüm).
    from modules.yeni_motor.motor import kapak_olcekle, kapak_youtube_surumu

    try:
        kapak_olcekle(ham_kapak, kapak)
        kapak_youtube_surumu(ham_kapak, kapak_yt)
        from PIL import Image

        print(f"[hat] kapak ham {Image.open(ham_kapak).size} → "
              f"dikey {Image.open(kapak).size} + 16:9 {Image.open(kapak_yt).size}")
    except Exception as e:
        return {**rapor, "hata": f"kapak biçimlendirme hatası: {e}"}

    # --- 3) VİDEO (NotebookLM) --------------------------------------------
    print("\n=== 3/4 VİDEO (NotebookLM) ===")
    ham = f"/tmp/nb_{_slug(konu['baslik'])}_{damga}.mp4"
    _kimlik_kur()
    os.environ.setdefault("NOTEBOOKLM_QUIET_DEPRECATIONS", "1")
    t = time.time()
    try:
        import asyncio

        nb = asyncio.run(_uret(konu["metin"], konu["baslik"], ham))
    except Exception as e:
        return {**rapor, "hata": f"NotebookLM: {type(e).__name__}: {e}"}
    rapor["asamalar"]["video"] = round(time.time() - t, 1)
    rapor["notebook"] = {k: nb.get(k) for k in ("defter_id", "kaynak_id", "sure_sn")}

    # --- 4) SON İŞLEME (kırp + kapak) -------------------------------------
    print("\n=== 4/4 SON İŞLEME (kırp + kapak) ===")
    t = time.time()
    cikti = f"/tmp/bobi_{damga}.mp4"
    isl = son.son_isle(ham, kapak, cikti)
    rapor["asamalar"]["son_isle"] = round(time.time() - t, 1)
    rapor["isleme"] = {"kirpma": isl.get("kirpma"), "kapak": isl.get("kapak_gomme")}
    if isl.get("hata"):
        # Kapak gömülemediyse yayın YOK — kullanıcı kararı kesin.
        return {**rapor, "hata": isl["hata"]}

    final = isl["cikti"]
    bilgi = isl.get("bilgi") or son.video_bilgi(final)
    rapor["video"] = bilgi
    if bilgi["sure"] > UST_SN:
        return {**rapor, "hata": f"video çok uzun: {bilgi['sure']} sn > {UST_SN}"}

    paket = _paket(konu, final, kapak_yt, damga)
    rapor["asamalar"]["toplam"] = round(time.time() - t0, 1)
    rapor["paket"] = paket
    return rapor


def main() -> int:
    ap = argparse.ArgumentParser(description="NotebookLM video hattı")
    ap.add_argument("--video-no", type=int, default=0)
    ap.add_argument("--kategori", default=None)
    ap.add_argument("--konu-json", default=None,
                    help="Hazır konu JSON dosyası (Gemini atlanır)")
    ap.add_argument("--cikti", default="/tmp/hat_sonuc.json")
    a = ap.parse_args()

    konu = None
    if a.konu_json:
        konu = json.loads(Path(a.konu_json).read_text(encoding="utf-8"))

    rapor = calistir(a.video_no, a.kategori, konu)
    Path(a.cikti).write_text(json.dumps(rapor, ensure_ascii=False, indent=1),
                             encoding="utf-8")
    print("\n" + "=" * 60)
    print(json.dumps({k: rapor.get(k) for k in
                      ("asamalar", "video", "hata")}, ensure_ascii=False, indent=1))
    if rapor.get("paket"):
        print("PAKET:", rapor["paket"]["final_video"])
        print("KAPAK:", rapor["paket"]["kapak_dosyasi"])
    print("=" * 60)
    return 0 if not rapor.get("hata") else 1


if __name__ == "__main__":
    sys.exit(main())
