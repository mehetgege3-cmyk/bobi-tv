"""Kapağın GERÇEKTEN ne olduğunu ölç: istem → Gemini → kaç görsel → hangisi alındı.

NİÇİN: Kullanıcı (2026-11-13) "ya istemi yollamadın ya yanlış görseli aldın" dedi.
`gemini_web.gorsel_uret()` yanıttaki TÜM googleusercontent URL'lerini toplayıp
`urls[0]`'ı alıyor. Gemini birden fazla görsel döndürürse (aday/varyasyon),
körlemesine İLKİ seçiliyor — doğru olan sonuncu olabilir.

NASIL: Aynı istemi yollar, yanıttaki TÜM görsel URL'lerini indirir, yan yana
kaydeder. Hangisinin ne olduğunu gözle görebilmek için.

ÇIKTI: out/kapak_prob/*.jpg + docs/KAPAK_PROB.md
"""
from __future__ import annotations

import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules import gemini_web  # noqa: E402
from modules.yeni_motor.motor import kapak_istemini_yaz  # noqa: E402

BASLIK = "Su İçerken Hiç Düşündün mü?"
CIKIS = Path("out/kapak_prob")


def main() -> int:
    CIKIS.mkdir(parents=True, exist_ok=True)
    istem = kapak_istemini_yaz(BASLIK)
    print(f"[prob] İSTEM: {istem}", flush=True)

    c = gemini_web.cerez()
    if not c:
        print("[prob] çerez yok", flush=True)
        return 1
    at = gemini_web.jeton(c)
    if not at:
        print("[prob] jeton yok", flush=True)
        return 1

    govde, uid = gemini_web._govde(istem, at)
    url = f"{gemini_web.GENERATE}?hl=tr&_reqid=100000&rt=c"
    req = urllib.request.Request(
        url, data=govde, method="POST",
        headers={
            **gemini_web.BASLIKLAR,
            "cookie": c,
            "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
            "origin": "https://gemini.google.com",
            "referer": "https://gemini.google.com/app",
            "x-same-domain": "1",
            "x-goog-ext-525005358-jspb": f'["{uid}",1]',
        },
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        yanit = r.read().decode("utf-8", "replace")
    print(f"[prob] yanıt: {len(yanit)} karakter", flush=True)

    urls = re.findall(
        r"https://[A-Za-z0-9._/-]*googleusercontent\.com/[A-Za-z0-9._/=-]+", yanit
    )
    # tekrarları at, sırayı koru
    gorulen, benzersiz = set(), []
    for u in urls:
        t = u.split("=")[0]
        if t in gorulen:
            continue
        gorulen.add(t)
        benzersiz.append(u)

    print(f"[prob] BENZERSİZ GÖRSEL URL: {len(benzersiz)}", flush=True)

    rapor = [f"# KAPAK PROBU — {BASLIK}", "", f"**İstem:** {istem}", ""]
    rapor.append(f"**Yanıt:** {len(yanit)} karakter · **Görsel URL:** {len(benzersiz)}")
    rapor.append("")

    indirilen = []
    for i, u in enumerate(benzersiz, 1):
        temel = u.split("=")[0]
        hedef = CIKIS / f"aday_{i}.jpg"
        ok = False
        for aday in (temel + "=s2048", u, temel + "=s1024"):
            try:
                r2 = urllib.request.Request(aday, headers={**gemini_web.BASLIKLAR, "cookie": c})
                with urllib.request.urlopen(r2, timeout=120) as r:
                    ham = r.read()
                if len(ham) < 5000 or ham[:2] not in (b"\xff\xd8", b"\x89P"):
                    continue
                hedef.write_bytes(ham)
                ok = True
                break
            except Exception as e:
                print(f"[prob] aday {i} indirme: {type(e).__name__}", flush=True)
        if ok:
            indirilen.append(hedef)
            rapor.append(f"- `aday_{i}.jpg` — {hedef.stat().st_size // 1024} KB "
                         f"{'← kodun seçtiği (urls[0])' if i == 1 else ''}")
            print(f"[prob] aday {i} indi: {hedef.stat().st_size} bayt", flush=True)
        else:
            rapor.append(f"- aday_{i} indirilemedi")
            print(f"[prob] aday {i} İNDİRİLEMEDİ", flush=True)

    rapor.append("")
    if len(indirilen) > 1:
        rapor.append(f"## ⚠️ Gemini {len(indirilen)} görsel döndürdü, kod `urls[0]`'ı alıyor")
        rapor.append("Yani doğru görsel ilki değilse YANLIŞ kapak yükleniyor.")
    else:
        rapor.append("## Gemini tek görsel döndürdü — seçim sorunu yok")

    (Path("docs") / "KAPAK_PROB.md").write_text("\n".join(rapor) + "\n", encoding="utf-8")
    print("[prob] docs/KAPAK_PROB.md yazıldı", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
