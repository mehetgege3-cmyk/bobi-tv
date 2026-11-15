"""Kontrol testi: `null` yük oturum sorunu mu, yük sorunu mu?

NİÇİN: HAR'daki TAM gövdeler gönderildi ama `wrb.fr` yükü **null** döndü.
İki olasılık var ve ikisi çok farklı sonuç doğurur:

  A) YÜK sorunu   → RPC çalıştı, argüman beğenilmedi
  B) OTURUM sorunu→ istek işlendi ama bağlam (at/bl/sid) kabul edilmedi

Ayırt etme yöntemi — kontroller:
  1. `sODAg` boş yük `[]` ile: HAR'da `[true]` dönmüştü. En basit yük.
  2. UYDURMA RPC kimliği: hiç var olmayan bir id ne dönüyor?
     - `null` dönerse → null "işlenmedi" demek (B)
     - hata dönerse  → null "işlendi ama boş" demek (A)
  3. Bozuk `at` ile: 401 mi, null mı?
  4. `at` + `f.sid` aynı sayfadan mı, ayrı ayrı mı — eşleşme testi

SADECE OKUR.
ÇIKTI: konsol + docs/NOTEBOOK_KONTROL_TESTI.md
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

RAPOR = Path("docs/NOTEBOOK_KONTROL_TESTI.md")
TABAN = "https://notebook.google.com"
UYGULAMA = "/_/LabsTailwindUi"
DEFTER = "18547767-c4b2-47a3-8d2e-d62513426959"
BL = "boq_labs-tailwind-frontend_20261112.11_p0"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36"
)


def _cerezler() -> dict[str, str]:
    ham = (os.environ.get("NOTEBOOK_GOOGLE") or "").strip()
    if not ham:
        raise SystemExit("HATA: NOTEBOOK_GOOGLE boş.")
    if ham.startswith("[") or ham.startswith("{"):
        veri = json.loads(ham)
        if isinstance(veri, dict) and "cookies" in veri:
            veri = veri["cookies"]
        if isinstance(veri, list):
            return {str(c["name"]): str(c.get("value", ""))
                    for c in veri if isinstance(c, dict) and c.get("name")}
        return {str(k): str(v) for k, v in veri.items()}
    out: dict[str, str] = {}
    for parca in ham.split(";"):
        if "=" in parca:
            k, v = parca.strip().split("=", 1)
            out[k] = v
    return out


def _get(url: str, cerez: dict[str, str], ek: dict | None = None,
         veri: bytes | None = None) -> tuple[int, str]:
    b = {
        "user-agent": UA,
        "accept-language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        "cookie": "; ".join(f"{k}={v}" for k, v in cerez.items()),
        "referer": f"{TABAN}/notebook/{DEFTER}",
        "origin": TABAN,
        "x-same-domain": "1",
    }
    if ek:
        b.update(ek)
    r = urllib.request.Request(url, data=veri, headers=b,
                               method="POST" if veri else "GET")
    try:
        with urllib.request.urlopen(r, timeout=60) as y:
            return y.status, y.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}"


def _rpc(at: str, fsid: str, cerez: dict[str, str], rpc: str,
         ic: str) -> tuple[int, str]:
    govde = json.dumps([[[rpc, ic, None, "generic"]]], separators=(",", ":"))
    veri = urllib.parse.urlencode({"f.req": govde, "at": at}).encode()
    url = (f"{TABAN}{UYGULAMA}/data/batchexecute?rpcids={rpc}"
           f"&source-path=%2Fnotebook%2F{DEFTER}&bl={BL}"
           f"&f.sid={fsid}&hl=tr&rt=c")
    return _get(url, cerez, {
        "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
    }, veri)


def _ozet(govde: str) -> str:
    """Yanıtın kısa karakterizasyonu."""
    if "errcode" in govde:
        m = re.search(r'"errcode":\s*(-?\d+)', govde)
        return f"ERRCODE {m.group(1) if m else '?'}"
    m = re.search(r'"wrb\.fr","[^"]+",(null|"|\[|\{)', govde)
    if not m:
        return "wrb.fr YOK"
    if m.group(1) == "null":
        return "YÜK NULL"
    return f"YÜK VAR ({m.group(1)})"


def main() -> int:
    cerez = _cerezler()
    out: list[str] = []
    d = out.append
    d("# NotebookLM Kontrol Testi")
    d("")
    d("Soru: `null` yük **oturum** sorunu mu, **yük** sorunu mu?")
    d("")

    kod, html = _get(f"{TABAN}/notebook/{DEFTER}", cerez)
    at = re.search(r'"SNlM0e":"([^"]+)"', html)
    fsid = re.search(r'"FdrFJe":"([^"]+)"', html)
    if not at or not fsid:
        d(f"**DURDURULDU:** at/f.sid yok (sayfa HTTP {kod}).")
        RAPOR.write_text("\n".join(out) + "\n", encoding="utf-8")
        print("\n".join(out))
        return 1
    at, fsid = at.group(1), fsid.group(1)
    d(f"- Sayfa HTTP {kod} · `at` {len(at)} krkt · `f.sid` {fsid}")
    d("")

    d("## Denemeler")
    d("")
    d("| # | Deneme | HTTP | Yanıt |")
    d("|---|---|---|---|")
    kayit: list[tuple[str, str]] = []

    def dene(ad: str, rpc: str, ic: str, at_k: str | None = None,
             fs: str | None = None) -> None:
        k, g = _rpc(at_k or at, fs or fsid, cerez, rpc, ic)
        o = _ozet(g)
        d(f"| {len(kayit) + 1} | {ad} | {k} | **{o}** |")
        kayit.append((ad, g))

    # 1. HAR'da [true] dönen, yükü boş olan RPC — en basit vaka
    dene("`sODAg` boş yük (HAR: `[true]`)", "sODAg", "[]")
    # 2. Uydurma RPC kimliği — hiç var olmayan
    dene("UYDURMA RPC `zzzzzz`", "zzzzzz", "[]")
    # 3. Bozuk at
    dene("Bozuk `at` ile `sODAg`", "sODAg", "[]", at_k="BOZUK_AT_DEGERI")
    # 4. Sayfa at'si + UYDURMA f.sid
    dene("Uydurma `f.sid` ile `sODAg`", "sODAg", "[]", fs="123456789")
    d("")

    d("## Yorum")
    d("")
    ozet = {a: _ozet(g) for a, g in kayit}
    uydurma = [v for k, v in ozet.items() if "zzzzzz" in k][0]
    bozuk = [v for k, v in ozet.items() if "Bozuk" in k][0]
    d(f"- Uydurma RPC → **{uydurma}**")
    d(f"- Bozuk `at` → **{bozuk}**")
    d("")
    if uydurma == "YÜK NULL" and bozuk != "YÜK NULL":
        d("**SONUÇ: `null` yük = RPC kimliği tanınmadı.** Yani sunucu isteği")
        d("işliyor ama o bağlamda bu RPC'yi çalıştırmıyor. Oturum SAĞLAM.")
    elif bozuk == "YÜK NULL":
        d("**SONUÇ: bozuk `at` bile aynı `null`'u veriyor → `at` DOĞRULANMIYOR.**")
        d("Yani `null` bir hata sinyali değil; yük hiç işlenmiyor. Oturum")
        d("katmanında bir eksik var (muhtemelen `at` tazeliği / `bl` uyumu).")
    else:
        d("**SONUÇ:** desen net değil, ham yanıtlar aşağıda.")
    d("")

    d("## Ham yanıtlar")
    d("")
    for ad, g in kayit:
        d(f"### {ad}")
        d("")
        d("```")
        d(g[:400])
        d("```")
        d("")

    RAPOR.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
