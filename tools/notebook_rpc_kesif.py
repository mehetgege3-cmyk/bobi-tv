"""NotebookLM RPC keşfi — 200 ile GERÇEK VERİYİ ayırır.

NİÇİN: `batchexecute` hata durumunda bile **HTTP 200** döner; içine
`"errcode":...` ya da boş `[]` yazar. Bir önceki deneme 200 gördü ama bu
"RPC çalıştı" demek DEĞİL. Bu araç yanıt GÖVDESİNİ ayrıştırır:

  - gövdede `wrb.fr` + RPC id + dolu içerik  → GERÇEK
  - gövdede `errcode` / boş liste            → HATA

Ayrıca `at` token'ı her sayfa yüklemesinde tazelendiği için burada
her koşuda yeniden alınır.

SADECE OKUR: defter oluşturmaz, kaynak eklemez, silmez.

ÇIKTI: konsol + docs/NOTEBOOK_RPC_KESIF.md
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

RAPOR = Path("docs/NOTEBOOK_RPC_KESIF.md")
TABAN = "https://notebook.google.com"
UYGULAMA = "/_/LabsTailwindUi"
DEFTER = "18547767-c4b2-47a3-8d2e-d62513426959"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36"
)

#: Denenecek RPC'ler ve anlamlı varsayımları.
ADAYLAR = [
    ("wXbhsf", "[]", "defter listesi"),
    ("hPTbtc", json.dumps([DEFTER]), "defter detayı"),
    ("khqZz", json.dumps([DEFTER]), "kaynak listesi"),
    ("rLM1Ne", json.dumps([DEFTER]), "kaynak ekleme?"),
    ("izAoDd", json.dumps([DEFTER]), "sohbet?"),
    ("tr032e", json.dumps([DEFTER]), "?"),
    ("VfAZjd", json.dumps([DEFTER]), "?"),
]


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
    basliklar = {
        "user-agent": UA,
        "accept-language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        "cookie": "; ".join(f"{k}={v}" for k, v in cerez.items()),
        "referer": TABAN + "/",
        "origin": TABAN,
    }
    if ek:
        basliklar.update(ek)
    istek = urllib.request.Request(url, data=veri, headers=basliklar,
                                   method="POST" if veri else "GET")
    try:
        with urllib.request.urlopen(istek, timeout=45) as y:
            return y.status, y.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}"


def _at_al(cerez: dict[str, str]) -> tuple[str | None, str | None]:
    kod, html = _get(f"{TABAN}/notebook/{DEFTER}", cerez)
    if kod != 200:
        return None, None
    at = re.search(r'"SNlM0e":"([^"]+)"', html)
    fsid = re.search(r'"FdrFJe":"([^"]+)"', html)
    return (at.group(1) if at else None, fsid.group(1) if fsid else None)


def _rpc(at: str, fsid: str, cerez: dict[str, str], rpc: str,
         ic: str) -> tuple[int, str]:
    govde = json.dumps([[[rpc, ic, None, "generic"]]], separators=(",", ":"))
    veri = urllib.parse.urlencode({"f.req": govde, "at": at}).encode()
    url = (f"{TABAN}{UYGULAMA}/data/batchexecute?rpcids={rpc}"
           f"&hl=tr&rt=c&f.sid={fsid}")
    return _get(url, cerez, {
        "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
        "x-same-domain": "1",
        "accept": "*/*",
    }, veri)


def _degerlendir(govde: str, rpc: str) -> tuple[str, str]:
    """(durum, kanıt) — 'GERCEK' | 'HATA' | 'BOS' | 'BILINMEZ'."""
    if "errcode" in govde:
        m = re.search(r'"errcode":\s*(-?\d+)', govde)
        kod = m.group(1) if m else "?"
        return "HATA", f"errcode {kod}"
    if f"wrb.fr" not in govde:
        return "BILINMEZ", govde[:120].replace("\n", " ")
    # wrb.fr satırındaki JSON yükünü çıkar
    m = re.search(re.escape(rpc) + r'","(.*?)",null,null,null,"generic"', govde, re.S)
    if not m:
        m = re.search(r'wrb\.fr","' + re.escape(rpc) + r'","(.*?)"\]', govde, re.S)
    if not m:
        return "BILINMEZ", govde[:160].replace("\n", " ")
    yuk = m.group(1)
    yuk = yuk.encode().decode("unicode_escape", "replace")
    if yuk in ("", "[]", "null"):
        return "BOS", yuk
    return "GERCEK", f"{len(yuk)} karakter yük"


def main() -> int:
    cerez = _cerezler()
    out: list[str] = []
    d = out.append

    d("# NotebookLM RPC Keşfi")
    d("")
    d(f"- Çerez: **{len(cerez)}**")
    d(f"- Defter: `{DEFTER}`")
    d("")

    at, fsid = _at_al(cerez)
    if not at:
        d("**DURDURULDU:** at token alınamadı.")
        RAPOR.write_text("\n".join(out) + "\n", encoding="utf-8")
        print("\n".join(out))
        return 1
    d(f"- `at` alındı: `{at[:12]}…` ({len(at)} krkt) · `f.sid`: `{fsid[:10]}…`")
    d("")

    d("## RPC sonuçları")
    d("")
    d("| RPC | Varsayım | HTTP | Durum | Kanıt |")
    d("|---|---|---|---|---|")
    gercek: list[tuple[str, str, str]] = []
    for rpc, ic, ne in ADAYLAR:
        kod, govde = _rpc(at, fsid, cerez, rpc, ic)
        durum, kanit = _degerlendir(govde, rpc)
        if durum == "GERCEK":
            gercek.append((rpc, ne, govde))
        d(f"| `{rpc}` | {ne} | {kod} | **{durum}** | {kanit} |")
        time.sleep(0.4)
    d("")

    # — Gerçek veri dönenlerin gövdesini göster —
    for rpc, ne, govde in gercek:
        d(f"### `{rpc}` — {ne}")
        d("")
        d("```")
        d(govde[:1200].replace("\\n", " "))
        d("```")
        d("")

    d("## Özet")
    d("")
    d(f"GERÇEK veri dönen: **{len(gercek)}** → "
      f"{[g[0] for g in gercek] or 'yok'}")

    RAPOR.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
