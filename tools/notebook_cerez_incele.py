"""NOTEBOOK_GOOGLE çerezini incele — yalnız OKUR, hiçbir şey değiştirmez.

NİÇİN: Kullanıcı (2026-11-15) yeni bir Google çerezi ekledi ve "har dosyası
vereceğim, önce gerekli incelemelerini yap" dedi. HAR'a hazır olmak için:

  1. Çerez gerçekten var mı, kaç çerez, hangi domain'ler?
  2. Hangi Google servislerine yetki veriyor? (NotebookLM / Gemini / Drive)
  3. Kritik anahtarlar var mı: SID, SAPISID, __Secure-1PSID, HSID, SSID…
  4. NotebookLM uçlarına erişim var mı? (batchexecute RPC'si)

ÇIKTI: docs/NOTEBOOK_CEREZ_INCELEME.md — değerler MASKELENİR, sır yazılmaz.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

RAPOR = Path("docs/NOTEBOOK_CEREZ_INCELEME.md")

#: Google'ın kritik çerezleri ve ne işe yaradıkları.
KRITIK = {
    "__Secure-1PSID": "ana oturum (Secure, httponly)",
    "__Secure-3PSID": "3. parti oturum",
    "__Secure-1PSIDTS": "oturum zaman damgası (yenilenir)",
    "SID": "Google oturum kimliği",
    "HSID": "oturum güvenlik çerezi",
    "SSID": "oturum güvenlik çerezi",
    "SAPISID": "Authorization: SAPISIDHASH için gerekli",
    "__Secure-1PAPISID": "SAPISIDHASH (1. parti)",
    "__Secure-3PAPISID": "SAPISIDHASH (3. parti)",
    "APISID": "eski API kimlik doğrulama",
    "OSID": "Google+ / servis oturumu",
    "NID": "tercih/oturum",
}

#: NotebookLM uçları — erişim denenecek adresler.
NOTEBOOK_UCLARI = {
    "ana sayfa": "https://notebooklm.google.com/",
    "RPC listesi": "https://notebooklm.google.com/_/LabsTailwindUi/data/batchexecute",
}


def _maskele(deger: str) -> str:
    if not deger:
        return "(boş)"
    if len(deger) <= 12:
        return deger[:2] + "…" + deger[-2:]
    return deger[:6] + "…" + deger[-4:] + f" ({len(deger)} karakter)"


def _cerez_ayristir(ham: str) -> dict[str, str]:
    """Çerez dizesini ya da JSON listesini dict'e çevir."""
    ham = (ham or "").strip()
    if not ham:
        return {}

    # JSON biçimi: [{name, value, domain, ...}, ...]
    if ham.startswith("[") or ham.startswith("{"):
        try:
            veri = json.loads(ham)
            if isinstance(veri, dict) and "cookies" in veri:
                veri = veri["cookies"]
            if isinstance(veri, list):
                return {str(c.get("name")): str(c.get("value", ""))
                        for c in veri if isinstance(c, dict) and c.get("name")}
            if isinstance(veri, dict):
                return {str(k): str(v) for k, v in veri.items()}
        except Exception:
            pass

    # "name=value; name2=value2" biçimi
    out: dict[str, str] = {}
    for parca in ham.split(";"):
        parca = parca.strip()
        if "=" in parca:
            k, v = parca.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def _sapisidhash(sapisid: str, origin: str = "https://notebooklm.google.com") -> str:
    import hashlib
    import time

    ts = str(int(time.time()))
    h = hashlib.sha1(f"{ts} {sapisid} {origin}".encode()).hexdigest()
    return f"SAPISIDHASH {ts}_{h}"


def main() -> int:
    ham = os.environ.get("NOTEBOOK_GOOGLE", "")
    cerezler = _cerez_ayristir(ham)

    rapor: list[str] = ["# NOTEBOOK_GOOGLE ÇEREZ İNCELEMESİ", ""]
    rapor.append(f"**Çerez sayısı:** {len(cerezler)}")
    rapor.append(f"**Ham uzunluk:** {len(ham)} karakter")
    rapor.append("")

    if not cerezler:
        rapor.append("## ❌ ÇEREZ BOŞ VEYA AYRIŞTIRILAMADI")
        RAPOR.write_text("\n".join(rapor) + "\n", encoding="utf-8")
        print("[incele] çerez yok/ayrıştırılamadı", flush=True)
        return 1

    # --- kritik çerezler -------------------------------------------------
    rapor.append("## Kritik çerezler")
    rapor.append("")
    rapor.append("| Çerez | Durum | Değer (maskeli) |")
    rapor.append("|---|---|---|")
    for ad, aciklama in KRITIK.items():
        var = ad in cerezler and bool(cerezler[ad])
        rapor.append(
            f"| `{ad}` | {'✅' if var else '—'} | "
            f"{_maskele(cerezler.get(ad, '')) if var else ''} |"
        )
    rapor.append("")
    rapor.append("_Açıklamalar:_")
    for ad, aciklama in KRITIK.items():
        if ad in cerezler:
            rapor.append(f"- `{ad}` — {aciklama}")
    rapor.append("")

    # --- diğer çerezler ---------------------------------------------------
    digerleri = sorted(set(cerezler) - set(KRITIK))
    rapor.append(f"## Diğer çerezler ({len(digerleri)})")
    rapor.append("")
    rapor.append("```")
    rapor.append(", ".join(digerleri) if digerleri else "(yok)")
    rapor.append("```")
    rapor.append("")

    # --- canlı erişim testi ----------------------------------------------
    cerez_basligi = "; ".join(f"{k}={v}" for k, v in cerezler.items())
    sapisid = cerezler.get("SAPISID") or cerezler.get("__Secure-3PAPISID", "")
    basliklar = {
        "cookie": cerez_basligi,
        "user-agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
        "accept-language": "tr,en;q=0.9",
    }
    if sapisid:
        basliklar["authorization"] = _sapisidhash(sapisid)

    rapor.append("## Canlı erişim testi")
    rapor.append("")
    rapor.append("| Uç | HTTP | Not |")
    rapor.append("|---|---|---|")
    for ad, url in NOTEBOOK_UCLARI.items():
        try:
            req = urllib.request.Request(url, headers=basliklar)
            with urllib.request.urlopen(req, timeout=45) as r:
                kod = r.status
                govde = r.read(200000).decode("utf-8", "replace")
            not_ = f"{len(govde)} karakter"
            if "notebooklm" in govde.lower():
                not_ += " · notebooklm izi var"
            if "accounts.google.com" in govde and kod in (301, 302, 200):
                not_ += " · ⚠️ login'e yönlendiriyor olabilir"
        except urllib.error.HTTPError as e:
            kod = e.code
            govde = ""
            not_ = e.reason
        except Exception as e:
            kod = "-"
            govde = ""
            not_ = f"{type(e).__name__}: {str(e)[:80]}"
        rapor.append(f"| `{url}` | **{kod}** | {not_} |")
        print(f"[incele] {ad}: HTTP {kod}", flush=True)

    rapor.append("")
    rapor.append("## Özet")
    rapor.append("")
    temel = [c for c in ("__Secure-1PSID", "SID", "SAPISID", "__Secure-3PSID") if c in cerezler]
    rapor.append(f"- Oturum çerezleri bulundu: **{len(temel)}/4** ({', '.join(temel) or 'yok'})")
    rapor.append(f"- SAPISIDHASH üretilebilir: **{'EVET' if sapisid else 'HAYIR'}**")
    rapor.append(f"- Toplam çerez: **{len(cerezler)}**")

    RAPOR.parent.mkdir(exist_ok=True)
    RAPOR.write_text("\n".join(rapor) + "\n", encoding="utf-8")
    print("[incele] docs/NOTEBOOK_CEREZ_INCELEME.md yazıldı", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
