"""NotebookLM uçlarını canlı dene — HAR'dan çıkan formülü doğrular.

NİÇİN: 2026-11-15 HAR'ı (notebook.google.com_..._20_03_28.har) iki şeyi gösterdi:

  1. `at` token'ı çerezde DEĞİL. Sayfa HTML'indeki WIZ_global_data içinde:
         "SNlM0e":"AGpKfmjsBSIdBAr9wZCEw_vRv44R:1794760360836"
     Bu değer her sayfa yüklemesinde tazelenir.

  2. Gerçek RPC çağrısı şu gövdeyle gidiyor (URL-decode edilmiş):
         f.req=[[["gArtLc","[[2,null,null,[1,null,...]],[[1,25,4,8,10,14,2,3,6]]],
                 \"<notebook_id>\",\"NOT artifact.status = \\\"ARTIFACT_STATUS_SUGGESTED\\\"\""],null,"generic"]]
         at=AGpKfmjsBSIdBAr9wZCEw_vRv44R:1794760360836
     Yani: RPC ID + JSON string + "generic" sarmalayıcı.

Bu araç SADECE OKUR. Not oluşturmaz, silmez, üretmez. Sadece hangi RPC
kimliklerinin 200 döndüğünü söyler.

ÇIKTI: konsol + docs/NOTEBOOK_UC_DENEME.md
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

RAPOR = Path("docs/NOTEBOOK_UC_DENEME.md")
TABAN = "https://notebook.google.com"
#: HAR'da görülen uygulama yolu (CSP report-uri'sinden doğrulandı).
UYGULAMA = "/_/LabsTailwindUi"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36"
)

#: HAR'ın SON kaydından BİREBİR alındı (uydurma değil).
RPC_HAR = "gArtLc"

#: Aday RPC kimlikleri — SADECE deneme. Hiçbiri HAR'da yok; 200 dönen
#: olursa hangisi olduğu raporda tek tek yazılır.
RPC_ADAYLARI = [
    "wXbhsf",  # proje/notebook listesi
    "hPTbtc",  # notebook detayı
    "khqZz",   # kaynak listesi
    "rLM1Ne",  # kaynak ekleme
    "izAoDd",  # sohbet gönder
    "tr032e",  #?
    "VfAZjd",  #?
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


def _cerez_basligi(c: dict[str, str]) -> str:
    return "; ".join(f"{k}={v}" for k, v in c.items())


def _sapisidhash(sapisid: str) -> str:
    import hashlib
    zaman = int(time.time())
    ozet = hashlib.sha1(
        f"{zaman} {sapisid} https://notebook.google.com".encode()
    ).hexdigest()
    return f"SAPISIDHASH {zaman}_{ozet}"


def _get(url: str, cerez: dict[str, str], ek: dict[str, str] | None = None,
         veri: bytes | None = None) -> tuple[int, str]:
    basliklar = {
        "user-agent": UA,
        "accept-language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        "cookie": _cerez_basligi(cerez),
        "referer": TABAN + "/",
        "origin": TABAN,
    }
    if "SAPISID" in cerez:
        basliklar["authorization"] = _sapisidhash(cerez["SAPISID"])
    if ek:
        basliklar.update(ek)
    istek = urllib.request.Request(url, data=veri, headers=basliklar,
                                   method="POST" if veri else "GET")
    try:
        with urllib.request.urlopen(istek, timeout=45) as y:
            return y.status, y.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:  # ağ hatası
        return 0, f"{type(e).__name__}: {e}"


def _at_bul(html: str) -> tuple[str | None, str | None]:
    """SNlM0e = at token, FdrFJe = fsid (istek kimliği)."""
    at = re.search(r'"SNlM0e":"([^"]+)"', html)
    fsid = re.search(r'"FdrFJe":"([^"]+)"', html)
    return (at.group(1) if at else None,
            fsid.group(1) if fsid else None)


def _rpc(at: str, fsid: str | None, cerez: dict[str, str], rpc: str,
         ic: str) -> tuple[int, str]:
    govde = json.dumps([[[rpc, ic, None, "generic"]]], separators=(",", ":"))
    veri = urllib.parse.urlencode({"f.req": govde, "at": at}).encode()
    url = f"{TABAN}{UYGULAMA}/data/batchexecute?rpcids={rpc}&hl=tr&rt=c"
    if fsid:
        url += f"&f.sid={fsid}"
    return _get(url, cerez, {
        "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
        "x-same-domain": "1",
        "accept": "*/*",
    }, veri)


def main() -> int:
    cerez = _cerezler()
    satirlar: list[str] = []
    d = satirlar.append

    d("# NotebookLM Uç Denemesi")
    d("")
    d(f"- Çerez sayısı: **{len(cerez)}**")
    d("- Kaynak: `notebook.google.com_2026_11_15_20_03_28.har`")
    d("")

    # — 1. Sayfayı aç, at token'ı çek —
    d("## 1. Sayfa + `at` token")
    d("")
    kod, html = _get(TABAN + "/", cerez)
    d(f"- `GET /` → **HTTP {kod}**")
    at, fsid = _at_bul(html) if kod == 200 else (None, None)
    if at:
        d(f"- `SNlM0e` (at) → **BULUNDU** (`{at[:14]}…`, {len(at)} krkt)")
    else:
        d("- `SNlM0e` (at) → **YOK** (oturum geçersiz olabilir)")
    d(f"- `FdrFJe` (f.sid) → {'BULUNDU' if fsid else 'YOK'}")
    d("")

    if not at:
        d("**DURDURULDU:** at token olmadan RPC denenemez.")
        RAPOR.write_text("\n".join(satirlar) + "\n", encoding="utf-8")
        print("\n".join(satirlar))
        return 1

    # — 2. HAR'daki RPC'yi birebir dene (kontrol grubu) —
    d("## 2. HAR'daki RPC birebir (`gArtLc`)")
    d("")
    ic_har = (
        '[[2,null,null,[1,null,null,null,null,null,null,null,null,null,null,'
        '[1]]],[[1,25,4,8,10,14,2,3,6]]],"18547767-c4b2-47a3-8d2e-d62513426959",'
        '"NOT artifact.status = \\"ARTIFACT_STATUS_SUGGESTED\\""'
    )
    kod, govde = _rpc(at, fsid, cerez, RPC_HAR, ic_har)
    d(f"- `{RPC_HAR}` → **HTTP {kod}**")
    if kod == 200:
        d("- ✅ **Kimlik zinciri ÇALIŞIYOR** (çerez + SAPISIDHASH + at + f.req)")
    else:
        d(f"- ❌ gövde: `{govde[:200]}`")
    d("")

    # — 3. Aday RPC'ler —
    d("## 3. Aday RPC kimlikleri")
    d("")
    d("| RPC | HTTP | Sonuç |")
    d("|---|---|---|")
    calisan: list[str] = []
    for rpc in RPC_ADAYLARI:
        ic = json.dumps([None], separators=(",", ":"))
        kod, govde = _rpc(at, fsid, cerez, rpc, ic)
        isaret = "✅" if kod == 200 and "errcode" not in govde[:200] else "—"
        if isaret == "✅":
            calisan.append(rpc)
        d(f"| `{rpc}` | {kod} | {isaret} |")
        time.sleep(0.4)
    d("")
    d(f"200 dönen aday sayısı: **{len(calisan)}** → {calisan or 'yok'}")
    d("")

    RAPOR.write_text("\n".join(satirlar) + "\n", encoding="utf-8")
    print("\n".join(satirlar))
    return 0


if __name__ == "__main__":
    sys.exit(main())
