"""NotebookLM ile video üret — konu metninden dikey kısa videoya.

NİÇİN: 2026-11-15'e kadar `batchexecute` RPC'leri elle çağrılıyordu ve
`wrb.fr` yükü `null` dönüyordu. Defter açma / kaynak ekleme RPC'leri HAR'da
yoktu. Araştırma sonucu hazır çözüm bulundu: **notebooklm-py** (v0.8.6).

Ölçülen sonuç (2026-11-15, bu makinede, canlı):
  defter oluştur  : ~2 sn
  metin kaynağı   : ~5 sn
  video üretimi   : **632 sn (10.5 dk)**
  video           : 720×1280 dikey (9:16), 30 fps, H.264 + AAC, ~74 sn, ~9.7 MB

Bu araç SADECE video üretir ve indirir. YouTube'a yükleme `main_pipeline`'ın işi.

KULLANIM:
    NOTEBOOK_GOOGLE='[...]' python3 tools/notebook_video.py metin.txt "Başlık"

ÇIKTI: /tmp/<slug>.mp4  (workspace bütçesi: K7 — video /tmp'ye)
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path

#: Video üretimi 10-11 dakika sürüyor; 20 dakika güvenli tavan.
BEKLEME_TAVANI = 1200.0

#: NotebookLM'in zorunlu çerezleri. notebooklm-py SID + __Secure-1PSIDTS ister.
ZORUNLU = ("SID", "__Secure-1PSIDTS")


def _slug(metin: str, n: int = 40) -> str:
    """Dosya adı için güvenli slug. Türkçe karakterler korunur."""
    s = re.sub(r"[^\w\s-]", "", metin, flags=re.UNICODE).strip()
    s = re.sub(r"[\s_-]+", "_", s)
    return (s[:n].strip("_") or "video")


def _depo_hazirla() -> dict:
    """NOTEBOOK_GOOGLE → Playwright storage_state biçimi.

    notebooklm-py `NOTEBOOKLM_AUTH_JSON` değişkenini doğrudan okur; dosya
    gerekmez. Çerez alanları Playwright kurallarına çevrilir:
    `expires` yoksa -1 (oturum çerezi), `__Secure-*` için httpOnly şart.
    """
    ham = (os.environ.get("NOTEBOOK_GOOGLE") or "").strip()
    if not ham:
        raise SystemExit("HATA: NOTEBOOK_GOOGLE boş.")

    if ham.startswith("[") or ham.startswith("{"):
        veri = json.loads(ham)
        if isinstance(veri, dict) and "cookies" in veri:
            veri = veri["cookies"]
        cerez = ([c for c in veri if isinstance(c, dict) and c.get("name")]
                 if isinstance(veri, list)
                 else [{"name": k, "value": v} for k, v in veri.items()])
    else:
        cerez = []
        for parca in ham.split(";"):
            if "=" in parca:
                k, v = parca.strip().split("=", 1)
                cerez.append({"name": k, "value": v})

    adlar = {c["name"] for c in cerez}
    eksik = [z for z in ZORUNLU if z not in adlar]
    if eksik:
        raise SystemExit(f"HATA: zorunlu çerez eksik → {eksik}")

    temiz = []
    for c in cerez:
        if not c.get("value"):
            continue
        domain = c.get("domain") or ".google.com"
        if not domain.startswith("."):
            domain = "." + domain.lstrip(".")
        temiz.append({
            "name": str(c["name"]),
            "value": str(c["value"]),
            "domain": domain,
            "path": c.get("path") or "/",
            "expires": c.get("expires") if isinstance(c.get("expires"), (int, float))
                       and c.get("expires", 0) > 0 else -1,
            "httpOnly": True,
            "secure": True,
            "sameSite": "None",
        })
    return {"cookies": temiz, "origins": []}


async def _uret(metin: str, baslik: str, cikti: str) -> dict:
    from notebooklm import NotebookLMClient
    from notebooklm.types import VideoFormat

    sonuc = {"baslik": baslik, "defter_id": None, "kaynak_id": None,
             "video": None, "sure_sn": None, "hata": None}
    t0 = time.time()

    async with NotebookLMClient.from_storage() as c:
        # 1) Defter
        nb = await c.notebooks.create(baslik)
        sonuc["defter_id"] = nb.id
        print(f"1) ✅ defter: {nb.id} — {nb.title}")

        # 2) Metin kaynağı
        src = await c.sources.add_text(nb.id, baslik, metin, wait=True)
        sonuc["kaynak_id"] = getattr(src, "id", None)
        print(f"2) ✅ kaynak: {sonuc['kaynak_id']}")

        # 3) Kısa video — Türkçe
        st = await c.artifacts.generate_video(
            nb.id, language="tr", video_format=VideoFormat.SHORT)
        print(f"3) ✅ üretim başladı: task={st.task_id}")

        # 4) Bekle
        fin = await c.artifacts.wait_for_completion(
            nb.id, st.task_id, timeout=BEKLEME_TAVANI)
        print(f"4) ✅ bitti ({time.time() - t0:.0f} sn): "
              f"status={getattr(fin, 'status', fin)}")

        # 5) İndir
        yol = await c.artifacts.download_video(nb.id, cikti)
        sonuc["video"] = str(yol)

    sonuc["sure_sn"] = round(time.time() - t0, 1)
    return sonuc


def main() -> int:
    if len(sys.argv) < 3:
        print("KULLANIM: python3 tools/notebook_video.py <metin.txt> <Başlık>")
        return 2

    metin_yolu, baslik = sys.argv[1], sys.argv[2]
    metin = Path(metin_yolu).read_text(encoding="utf-8")
    if len(metin) < 100:
        print(f"HATA: metin çok kısa ({len(metin)} krkt)")
        return 2

    os.environ["NOTEBOOKLM_AUTH_JSON"] = json.dumps(_depo_hazirla())
    os.environ.setdefault("NOTEBOOKLM_QUIET_DEPRECATIONS", "1")

    cikti = f"/tmp/{_slug(baslik)}.mp4"
    print(f"→ Başlık: {baslik}")
    print(f"→ Metin: {len(metin)} krkt")
    print(f"→ Çıktı: {cikti}")
    print()

    try:
        sonuc = asyncio.run(_uret(metin, baslik, cikti))
    except Exception as e:
        print(f"\n❌ ÜRETİM BAŞARISIZ: {type(e).__name__}: {e}")
        return 1

    print()
    print("=" * 50)
    print(json.dumps(sonuc, ensure_ascii=False, indent=1))
    print("=" * 50)
    return 0


if __name__ == "__main__":
    sys.exit(main())
