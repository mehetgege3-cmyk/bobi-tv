"""Gemini WEB oturum çerezini doğrula ve `GEMINI_COOKIES` secret'ına yaz.

NEDEN API DEĞİL: `GEMINI_API_KEY` bu projede görsel kotası `limit: 0` veriyor
(`docs/GEMINI_ENTEGRASYON.md` §9). Gemini WEB'in kendi arka ucu ise abonelik
kotasını kullanır: `gemini.google.com`'da görsel üretilebiliyorsa, çerezle de
üretilebilir (aynı arka uç: `StreamGenerate`).

KAYNAK (K1 kuralı — 2026-11-13'te okundu):
  • `__Secure-1PSID`   → ana oturum çerezi, uzun ömürlü
  • `__Secure-1PSIDTS` → zaman damgası, KISA ömürlü, `RotateCookies` ile yenilenir
  • `SNlM0e`           → CSRF/at jetonu, `https://gemini.google.com/app` HTML'inde
  • Görsel indirme: `generated_image` URL'leri Google depolamasından gelir,
    indirirken de çerez gerekir.
  • UYARI: Gemini web tarayıcıda AÇIK kalırsa çerez daha hızlı ölür →
    çerez aldıktan sonra sekme kapatılmalı.

KULLANIM
    # Cookie-Editor → Export → JSON (gemini.google.com) → dosya
    PYTHONPATH=. GH_PAT=<token> python3 tools/gemini_cerez_kur.py --dosya /tmp/gemini.json

    # sadece doğrula:
    PYTHONPATH=. python3 tools/gemini_cerez_kur.py --dosya /tmp/gemini.json --kuru

    # iki değeri elle ver:
    ... --psid "g.a000..." --psidts "sidts-..."

KABUL EDİLEN BİÇİMLER
  1. Cookie-Editor JSON dizisi   [{"name":"__Secure-1PSID","value":"...","domain":".google.com"}]
  2. {"ad":"değer"} nesnesi
  3. "ad=değer; ad=değer" başlık metni (DevTools → Request Headers → Cookie)
  4. --psid / --psidts bayrakları
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SECRET_ADI = "GEMINI_COOKIES"
ONEMLI = (
    "__Secure-1PSID",
    "__Secure-1PSIDTS",
    "__Secure-3PSID",
    "__Secure-3PSIDTS",
    "SID",
    "HSID",
    "SSID",
    "APISID",
    "SAPISID",
    "__Secure-3PAPISID",
    "NID",
)
# Zorunlu: en az biri şart
ZORUNLU = ("__Secure-1PSID", "__Secure-3PSID")

BASLIKLAR = {
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "accept-language": "tr-TR,tr;q=0.9,en;q=0.8",
}


# ---------------------------------------------------------------------------
# 1) Biçim normalizasyonu
# ---------------------------------------------------------------------------

def cerez_sozlugu(ham: str) -> dict[str, str]:
    """Girdiyi {ad: değer} sözlüğüne çevirir (değer gizliliği korunur)."""
    ham = (ham or "").strip()
    if not ham:
        return {}
    if ham.startswith("base64-"):
        import base64

        try:
            ham = base64.b64decode(ham[len("base64-"):]).decode("utf-8", "replace").strip()
        except Exception:
            return {}
    # JSON dizi
    if ham.startswith("["):
        try:
            veri = json.loads(ham)
            return {
                str(c["name"]): str(c["value"])
                for c in veri
                if isinstance(c, dict) and c.get("name")
            }
        except Exception:
            return {}
    # JSON nesne ({"name":..} tek çerez ya da {ad: değer})
    if ham.startswith("{"):
        try:
            veri = json.loads(ham)
            if isinstance(veri, dict):
                if "name" in veri and "value" in veri:
                    return {str(veri["name"]): str(veri["value"])}
                return {str(k): str(v) for k, v in veri.items() if not isinstance(v, (dict, list))}
        except Exception:
            return {}
    # "ad=değer; ad=değer"
    if "=" in ham:
        sonuc = {}
        for parca in ham.split(";"):
            if "=" not in parca:
                continue
            ad, deger = parca.split("=", 1)
            ad = ad.strip()
            if ad:
                sonuc[ad] = deger.strip()
        return sonuc
    return {}


def onemli_suz(sozluk: dict[str, str]) -> dict[str, str]:
    """Gemini için gereken çerezleri seçer (hepsi .google.com'a ait olmalı)."""
    secilen = {k: v for k, v in sozluk.items() if k in ONEMLI}
    # Kalanları da at ama sayıyı raporla
    return secilen or dict(sozluk)


def baslik_metni(sozluk: dict[str, str]) -> str:
    return "; ".join(f"{k}={v}" for k, v in sozluk.items() if v)


# ---------------------------------------------------------------------------
# 2) Canlılık ölçümü
# ---------------------------------------------------------------------------

def snlm0e_al(cerez: dict[str, str]) -> str | None:
    """`gemini.google.com/app` HTML'inden CSRF jetonunu (SNlM0e) çeker."""
    req = urllib.request.Request(
        "https://gemini.google.com/app",
        headers={**BASLIKLAR, "cookie": baslik_metni(cerez)},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            html = r.read().decode("utf-8", "replace")
            son = r.geturl()
    except Exception as e:
        print(f"       sayfa hatası: {type(e).__name__} {str(e)[:90]}")
        return None
    if "accounts.google.com" in son:
        print("       → accounts.google.com'a yönlendirildi (OTURUM YOK)")
        return None
    for kalip in (r'SNlM0e["\']?\s*[:=]\s*["\']([^"\']+)', r'"SNlM0e","([^"]+)"'):
        m = re.search(kalip, html)
        if m:
            return m.group(1)
    print(f"       SNlM0e bulunamadı (sayfa {len(html)} karakter)")
    return None


def canli_mi(cerez: dict[str, str]) -> bool:
    if not any(k in cerez for k in ZORUNLU):
        return False
    return bool(snlm0e_al(cerez))


# ---------------------------------------------------------------------------
# 3) Secret yazımı
# ---------------------------------------------------------------------------

def secret_yaz(baslik: str) -> int:
    gecici = Path("/tmp/gemini_cerez_kur.txt")
    gecici.write_text(baslik, encoding="utf-8")
    try:
        s = subprocess.run(
            [sys.executable, "tools/secret_duzelt.py", "--ad", SECRET_ADI,
             "--dosya", str(gecici), "--dosya-icerik"],
            env={**os.environ, "PYTHONPATH": "."},
            capture_output=True, text=True,
        )
        print((s.stdout or "").strip()[-400:])
        return s.returncode
    finally:
        try:
            gecici.unlink()
        except Exception:
            pass


def main() -> int:
    ap = argparse.ArgumentParser(description="Gemini web çerezini doğrula + secret'a yaz")
    ap.add_argument("--dosya", help="çerez dosyası (JSON dizi / nesne / başlık metni)")
    ap.add_argument("--psid", help="__Secure-1PSID değeri")
    ap.add_argument("--psidts", help="__Secure-1PSIDTS değeri")
    ap.add_argument("--kuru", action="store_true", help="sadece doğrula, yazma")
    ap.add_argument("--zorla", action="store_true", help="ölü olsa bile yaz")
    a = ap.parse_args()

    if a.psid:
        ham = f"__Secure-1PSID={a.psid}"
        if a.psidts:
            ham += f"; __Secure-1PSIDTS={a.psidts}"
    elif a.dosya:
        ham = Path(a.dosya).read_text(encoding="utf-8").strip()
    else:
        ham = sys.stdin.read().strip()

    sozluk = cerez_sozlugu(ham)
    if not sozluk:
        print("❌ Çerez okunamadı. Desteklenen biçimler dosya başında yazılı.")
        return 2

    secilen = onemli_suz(sozluk)
    print(f"[1/3] {len(sozluk)} çerez okundu → {len(secilen)} tanesi kullanılacak")
    for k in ONEMLI:
        if k in sozluk:
            print(f"       ✅ {k} ({len(sozluk[k])} karakter)")
    eksik = [k for k in ZORUNLU if k not in sozluk]
    if eksik:
        print(f"       ⚠️  EKSİK/ZORUNLU: {', '.join(eksik)}")

    print("[2/3] Oturum canlı mı? (gemini.google.com/app → SNlM0e)")
    jeton = snlm0e_al(secilen)
    if jeton:
        print(f"       ✅ CANLI — SNlM0e alındı ({len(jeton)} karakter)")

    if a.kuru:
        print("[3/3] --kuru: secret'a yazılmadı.")
        return 0 if jeton else 1

    if not jeton and not a.zorla:
        print("[3/3] ⛔ Ölü çerez YAZILMADI. Önce tarayıcıda gemini.google.com'a")
        print("      giriş yap; sonra F12 → Application → Cookies → export et.")
        print("      Yine de yazmak için: --zorla")
        return 1

    baslik = baslik_metni(secilen)
    print(f"[3/3] {SECRET_ADI} secret'ına yazılıyor ({len(baslik)} karakter)")
    kod = secret_yaz(baslik)
    if kod == 0:
        print("\n✅ BİTTİ. Not: `__Secure-1PSIDTS` kısa ömürlüdür; süre dolarsa")
        print("   yeniden export gerekir. Gemini sekmesini AÇIK BIRAKMA.")
    return kod


if __name__ == "__main__":
    raise SystemExit(main())
