"""LMARENA_EMAIL secret'ını düzeltir (yazım hatası: gmal.com → gmail.com).

Kullanım:
  1) .env gibi bir dosyaya DOĞRU adresi yaz:  LMARENA_EMAIL=hesap@gmail.com
  2) GH_PAT=... python tools/secret_duzelt.py --dosya /home/user/uploads/eposta.txt
     veya:  GH_PAT=... python tools/secret_duzelt.py --eposta hesap@gmail.com

Yaptığı: ön kontrol (yazım hatası varsa DURUR) → GitHub Actions secret'ını
libsodium ile şifreleyip yazar (repo secret API). Şifre/adres log'a yazılmaz.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.request
from pathlib import Path

REPO = os.environ.get("GH_REPO", "mehetgege3-cmyk/bobi-tv")


def _token() -> str:
    t = os.environ.get("GH_PAT", "").strip()
    if t:
        return t
    for aday in ("/home/user/uploads/githubpat-2.json",):
        try:
            import re

            m = re.search(r"gh[pousr]_[A-Za-z0-9]+", Path(aday).read_text(encoding="utf-8"))
            if m:
                return m.group(0)
        except Exception:
            pass
    return ""


def _istek(yol: str, veri: dict | None = None, yontem: str = "GET") -> dict:
    govde = json.dumps(veri).encode() if veri else None
    istek = urllib.request.Request(
        f"https://api.github.com{yol}",
        data=govde,
        method=yontem,
        headers={
            "Authorization": f"Bearer {_token()}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(istek, timeout=60) as y:
        ham = y.read().decode()
    return json.loads(ham) if ham.strip() else {}


def secret_yaz(ad: str, deger: str) -> tuple[bool, str]:
    try:
        from nacl import encoding, public  # type: ignore
    except ImportError:
        return False, "PyNaCl yok: pip install pynacl"
    if not _token():
        return False, "GH_PAT yok"
    pk = _istek(f"/repos/{REPO}/actions/secrets/public-key")
    kutu = public.SealedBox(public.PublicKey(pk["key"].encode(), encoding.Base64Encoder()))
    sifreli = base64.b64encode(kutu.encrypt(deger.encode("utf-8"))).decode()
    _istek(
        f"/repos/{REPO}/actions/secrets/{ad}",
        {"encrypted_value": sifreli, "key_id": pk["key_id"]},
        "PUT",
    )
    return True, f"{ad} güncellendi"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--eposta", default="")
    ap.add_argument("--dosya", default="")
    a = ap.parse_args()

    adres = a.eposta.strip()
    if not adres and a.dosya:
        for satir in Path(a.dosya).read_text(encoding="utf-8").splitlines():
            if satir.strip().lower().startswith("lmarena_email="):
                adres = satir.split("=", 1)[1].strip()
            elif "@" in satir and not adres:
                adres = satir.strip()
    if not adres:
        print("❌ Adres yok: --eposta veya --dosya ver")
        return 2

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from modules.arena_giris import eposta_on_kontrol

    gecerli, mesaj = eposta_on_kontrol(adres)
    if not gecerli:
        print(f"⛔ YAZILMADI — ön kontrol: {mesaj}")
        return 3
    print(f"✅ Ön kontrol geçti: {mesaj}")
    ok, sonuc = secret_yaz("LMARENA_EMAIL", adres)
    print(("✅ " if ok else "❌ ") + sonuc)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
