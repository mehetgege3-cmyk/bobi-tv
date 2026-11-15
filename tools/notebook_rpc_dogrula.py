"""NotebookLM RPC'lerini HAR'daki BİREBİR yüklerle canlı doğrular.

NİÇİN: `tools/notebook_rpc_kesif.py` yük şablonunu yanlış uydurduğu için
"BILINMEZ" verdi. Oysa HAR'da 65 `batchexecute` çağrısı ve 21 farklı RPC
var; her birinin TAM gövdesi elimizde. Bu araç o gövdeleri birebir
gönderir ve yanıtı ayrıştırır.

Doğrulanan RPC'ler (HAR kayıt sırasına göre):
  rLM1Ne  — defter meta: başlık, emoji, kaynak listesi
  hPTbtc  — kaynak kimlikleri
  cFji9   — artifact metnini OKU (üretilen içerik)
  otmP3b  — BAŞLIKTAN ALT KONU ÜRET (konu_uret için aday)
  VfAZjd  — defter açılış sohbeti + önerilen sorular + chat_id
  EylDcb  — kota/kullanım

SADECE OKUR. Defter oluşturmaz, kaynak eklemez, silmez.
Tek istisna: `otmP3b` bir başlık verilince alt konu ÖNERİR (arayüzün
"başlık yazınca öneri getir" davranışı). Kalıcı bir şey yaratmaz.

ÇIKTI: konsol + docs/NOTEBOOK_RPC_DOGRULAMA.md
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

RAPOR = Path("docs/NOTEBOOK_RPC_DOGRULAMA.md")
TABAN = "https://notebook.google.com"
UYGULAMA = "/_/LabsTailwindUi"

#: HAR'dan alınan gerçek kimlikler.
DEFTER = "18547767-c4b2-47a3-8d2e-d62513426959"
KAYNAK = "8f453169-bdfc-4a5f-8298-1c504922cdca"
ARTIFACT = "da2a6b72-35b2-4458-ac08-fe4cb0766dd3"
BL = "boq_labs-tailwind-frontend_20261112.11_p0"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36"
)

#: HAR'da her isteğin taşıdığı ortak çerçeve.
CERCEVE = "[2,null,[1],[1,null,null,null,null,null,null,null,null,null,[1,3]]]"


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
        "referer": f"{TABAN}/notebook/{DEFTER}",
        "origin": TABAN,
        "x-same-domain": "1",
    }
    if ek:
        basliklar.update(ek)
    istek = urllib.request.Request(url, data=veri, headers=basliklar,
                                   method="POST" if veri else "GET")
    try:
        with urllib.request.urlopen(istek, timeout=60) as y:
            return y.status, y.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}"


def _oturum(cerez: dict[str, str]) -> tuple[str | None, str | None]:
    """at token + f.sid — SADECE not defteri sayfasında var (ana sayfada YOK)."""
    kod, html = _get(f"{TABAN}/notebook/{DEFTER}", cerez)
    if kod != 200:
        return None, None
    at = re.search(r'"SNlM0e":"([^"]+)"', html)
    fsid = re.search(r'"FdrFJe":"([^"]+)"', html)
    return (at.group(1) if at else None, fsid.group(1) if fsid else None)


def _rpc(at: str, fsid: str, cerez: dict[str, str], rpc: str,
         ic: str) -> tuple[int, str]:
    """HAR'daki çerçeveyi birebir kurar."""
    govde = json.dumps([[[rpc, ic, None, "generic"]]], separators=(",", ":"))
    veri = urllib.parse.urlencode({"f.req": govde, "at": at}).encode()
    url = (f"{TABAN}{UYGULAMA}/data/batchexecute?rpcids={rpc}"
           f"&source-path=%2Fnotebook%2F{DEFTER}&bl={BL}"
           f"&f.sid={fsid}&hl=tr&rt=c")
    return _get(url, cerez, {
        "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
    }, veri)


def _yuk(govde: str, rpc: str) -> tuple[str, object]:
    """wrb.fr satırındaki JSON yükünü çöz. (durum, veri)."""
    i = govde.find(f'"wrb.fr","{rpc}","')
    if i < 0:
        return "YUK_YOK", None
    bas = i + len(f'"wrb.fr","{rpc}","')
    # JSON string: \" kaçışlarını sayarak kapanışı bul
    j = bas
    while j < len(govde):
        if govde[j] == "\\":
            j += 2
            continue
        if govde[j] == '"':
            break
        j += 1
    ham = govde[bas:j]
    try:
        metin = json.loads('"' + ham + '"')
        return "OK", json.loads(metin)
    except Exception as e:
        return f"COZUM_HATASI: {e}", None


def main() -> int:
    cerez = _cerezler()
    out: list[str] = []
    d = out.append

    d("# NotebookLM RPC Doğrulaması")
    d("")
    d(f"- Çerez: **{len(cerez)}**")
    d(f"- Defter: `{DEFTER}`")
    d("")

    at, fsid = _oturum(cerez)
    if not at:
        d("**DURDURULDU:** `at` token alınamadı.")
        RAPOR.write_text("\n".join(out) + "\n", encoding="utf-8")
        print("\n".join(out))
        return 1
    d(f"- `at`: `{at[:12]}…` · `f.sid`: `{fsid}`")
    d("")

    denemeler = [
        ("rLM1Ne", "defter meta (başlık/emoji/kaynak)",
         f'["{DEFTER}",null,{CERCEVE},null,0,[[null,null,[1]]]]'),
        ("hPTbtc", "kaynak kimlikleri",
         f'[{CERCEVE},null,"{DEFTER}",20]'),
        ("cFji9", "artifact METNİNİ OKU",
         f'["{DEFTER}",null,null,{CERCEVE}]'),
        ("EylDcb", "kota / kullanım",
         f'[{CERCEVE}]'),
        ("otmP3b", "BAŞLIKTAN ALT KONU ÜRET (YENİ tohum)",
         f'[{CERCEVE},"{DEFTER}",[["{ARTIFACT}"]],10,null,'
         f'"Neden kediler kutulara girmeyi sever","tr"]'),
        ("VfAZjd", "defter sohbeti + öneriler",
         f'["{DEFTER}",{CERCEVE}]'),
    ]

    d("## Sonuçlar")
    d("")
    d("| RPC | İş | HTTP | Durum |")
    d("|---|---|---|---|")
    sonuc: dict[str, object] = {}
    for rpc, ne, ic in denemeler:
        kod, govde = _rpc(at, fsid, cerez, rpc, ic)
        durum, veri = _yuk(govde, rpc)
        if durum == "OK" and veri not in (None, [], ""):
            durum = "GERCEK"
            sonuc[rpc] = veri
        elif durum == "OK":
            durum = "BOS"
        d(f"| `{rpc}` | {ne} | {kod} | **{durum}** |")
    d("")

    # — Kanıtlar —
    if "rLM1Ne" in sonuc:
        v = sonuc["rLM1Ne"]
        try:
            baslik = v[0][0][0] if isinstance(v[0], list) else v[0]
        except Exception:
            baslik = "?"
        d(f"### `rLM1Ne` → defter başlığı: **{baslik}**")
        d("")

    if "cFji9" in sonuc:
        v = sonuc["cFji9"]
        try:
            metin = v[0][0][1][1]
            d("### `cFji9` → artifact metni (ilk 700 krkt)")
            d("")
            d("```")
            d(metin[:700])
            d("```")
            d("")
            d(f"- **Toplam uzunluk: {len(metin)} karakter**")
            d("")
        except Exception as e:
            d(f"### `cFji9` → yapı çözülemedi: {e}")
            d("")

    if "otmP3b" in sonuc:
        v = sonuc["otmP3b"]
        d("### `otmP3b` → YENİ tohum için üretilen alt konular")
        d("")
        d("Tohum: `Neden kediler kutulara girmeyi sever`")
        d("")
        d("| # | Başlık | Alt başlık | Stil |")
        d("|---|---|---|---|")
        for i, k in enumerate(v[0] if isinstance(v[0], list) else [], 1):
            try:
                d(f"| {i} | {k[0]} | {k[1] or '—'} | {k[2][0] if k[2] else '—'} |")
            except Exception:
                d(f"| {i} | `{k}` | — | — |")
        d("")
        d("✅ **`otmP3b` çalışıyor → konu üretimi için kullanılabilir.**")
        d("")

    RAPOR.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
