"""Arena çerezini DOĞRULA ve (canlıysa) `ARENA_COOKIES_JSON` secret'ına yaz.

NEDEN: Ölü bir çerezi secret'a yazmak 4 saat sonra "neden çalışmıyor?" demek
demektir. Bu araç yazmadan ÖNCE `pulse` ucuyla çerezin canlı olduğunu ölçer.

KULLANIM
    # Cookie-Editor → Export → JSON  (dizi)  dosyaya kaydet:
    PYTHONPATH=. GH_PAT=<token> python3 tools/cerez_kur.py --dosya /tmp/arena_cerez.json

    # ya da doğrudan panodan (stdin):
    pbpaste | PYTHONPATH=. GH_PAT=<token> python3 tools/cerez_kur.py

    # sadece doğrula, yazma:
    PYTHONPATH=. python3 tools/cerez_kur.py --dosya /tmp/arena_cerez.json --kuru

KABUL EDİLEN BİÇİMLER (modules/arena_http._cerez_basligi ile aynı):
  1. Cookie-Editor JSON dizisi:  [{"name":"arena-auth-prod-v1.0","value":"...","domain":...}]
  2. {"ad": "değer"} nesnesi
  3. Ham `arena-auth-prod-v1.0` değeri (tek satır)
  4. `base64-` önekli değer
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules import arena_http  # noqa: E402


def normalestir(ham: str) -> str:
    """Girdiyi `Cookie` başlığına çevirir (secret'a yazılacak asıl biçim)."""
    return arena_http._cerez_basligi(ham)


def onemli_cerezler(ham: str) -> list[str]:
    """Teşhis için: çerez başlığındaki adları listeler (değer YAZILMAZ)."""
    baslik = normalestir(ham)
    return [p.split("=", 1)[0].strip() for p in baslik.split(";") if "=" in p]


def main() -> int:
    ap = argparse.ArgumentParser(description="Arena çerezini doğrula + secret'a yaz")
    ap.add_argument("--dosya", help="çerez dosyası (JSON dizi / nesne / ham değer)")
    ap.add_argument("--kuru", action="store_true", help="sadece doğrula, secret'a yazma")
    ap.add_argument("--zorla", action="store_true", help="ölü olsa bile yaz")
    a = ap.parse_args()

    ham = Path(a.dosya).read_text(encoding="utf-8").strip() if a.dosya else sys.stdin.read().strip()
    if not ham:
        print("❌ Çerez boş. --dosya ver ya da stdin'e yapıştır.")
        return 2

    baslik = normalestir(ham)
    if not baslik:
        print("❌ Çerez biçimi tanınamadı (ne dizi, ne nesne, ne ham değer).")
        return 2

    # Teşhis (değerler gizli)
    adlar = onemli_cerezler(ham)
    print(f"[1/3] Biçim tanındı · {len(baslik)} karakter · {len(adlar)} çerez")
    for ad in adlar:
        isaret = " ⭐" if ad.startswith("arena-auth") else ""
        print(f"       • {ad}{isaret}")
    if not any("arena-auth" in x for x in adlar):
        print("⚠️  UYARI: `arena-auth-prod-v1.*` çerezi YOK. Bu çerez işe yaramaz.")
        print("    Arena'ya GİRİŞ YAPMIŞ haldeyken export etmelisin.")

    # Canlılık ölçümü (pulse)
    print("[2/3] Çerez canlı mı? (pulse ucu)")
    canli = arena_http.oturum_canli_mi(baslik)
    print(f"       → {'✅ CANLI' if canli else '❌ ÖLÜ / 401'}")

    if a.kuru:
        print("[3/3] --kuru verildi, secret'a yazılmadı.")
        return 0 if canli else 1

    if not canli and not a.zorla:
        print("[3/3] ⛔ Ölü çerez secret'a YAZILMADI.")
        print("      Önce tarayıcıda arena.ai'ye giriş yap, sonra export et.")
        print("      Yine de yazmak istersen: --zorla")
        return 1

    # Geçici dosyaya yaz (kalıcı repoya girmesin) + secret'a bas
    gecici = Path("/tmp/arena_cerez_kur.txt")
    gecici.write_text(baslik, encoding="utf-8")
    tok = (os.environ.get("GH_PAT") or "").strip()
    if not tok:
        print("[3/3] ❌ GH_PAT yok; secret'a yazılamaz. (--kuru ile doğrulama yapabilirsin)")
        return 2
    calistir = [
        sys.executable, "tools/secret_duzelt.py",
        "--ad", "ARENA_COOKIES_JSON", "--dosya", str(gecici), "--dosya-icerik",
    ]
    print(f"[3/3] Secret'a yazılıyor… ({len(baslik)} karakter)")
    ortam = {**os.environ, "GH_PAT": tok, "PYTHONPATH": "."}
    s = subprocess.run(calistir, env=ortam, capture_output=True, text=True)
    print((s.stdout or "").strip()[-400:])
    if s.returncode != 0:
        print("❌ Secret yazılamadı:", (s.stderr or "").strip()[-300:])
        return s.returncode

    try:
        gecici.unlink()  # çerez diskte kalmasın
    except Exception:
        pass
    print("\n✅ BİTTİ. Sıradaki adım: üretim koşusunu tetikle ve kapağın")
    print("   `kaynak=arena_gorsel` geldiğini logdan doğrula.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
