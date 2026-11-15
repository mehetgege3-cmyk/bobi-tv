"""Master token kurulum yardımcısı — tek komutla.

KULLANICI İÇİN: `notebooklm login --master-token` komutunu elle yazmak yerine
bu betiği çalıştır. Ne yaptığını adım adım söyler, sonunda GitHub secret'ı
kendisi yazar (GH_PAT varsa) veya dosyanın yolunu verir.

ADIMLAR (betiğin yaptığı):
  1. `notebooklm login --master-token --account <e-posta>` → tarayıcı açılır,
     Google hesabına giriş yapılır (bir kez).
  2. Çıkan `master_token.json` okunur (0600).
  3. GitHub Secrets API ile `NOTEBOOKLM_MASTER_TOKEN_JSON` olarak yazılır.

KULLANIM:
    NOTEBOOK_EMAIL=hesap@gmail.com GH_PAT=ghp_... python3 tools/master_token_kur.py
    ... --secret-yazma        # secret'a yazma, sadece dosya üret

GÜVENLİK: token değeri EKRANA BASILMAZ. Yalnız uzunluğu ve dosya yolu yazılır.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = "mehetgege3-cmyk/bobi-tv"
SECRET_ADI = "NOTEBOOKLM_MASTER_TOKEN_JSON"


def _profil_dizini() -> Path:
    kok = Path(os.environ.get("NOTEBOOKLM_HOME") or (Path.home() / ".notebooklm"))
    return kok / "profiles" / (os.environ.get("NOTEBOOKLM_PROFILE") or "default")


def giris_yap(eposta: str) -> int:
    """Tarayıcıyı açar, master token üretir. Kullanıcı bir kez giriş yapar."""
    print("=" * 62)
    print("ADIM 1/3 — Tarayıcı açılacak, Google hesabına giriş yap")
    print(f"         Hesap: {eposta}")
    print("         Not defterlerinin olduğu hesap OLMALI.")
    print("=" * 62)
    r = subprocess.run(
        ["notebooklm", "login", "--master-token", "--account", eposta],
        text=True,
    )
    if r.returncode != 0:
        print(f"\n❌ giriş başarısız (kod {r.returncode}).")
        print("   Elle denemek için:  notebooklm login --master-token "
              f"--account {eposta}")
        return r.returncode
    return 0


def token_dosyasi() -> Path | None:
    """master_token.json'u bul (profil dizini veya eski konum)."""
    adaylar = [
        _profil_dizini() / "master_token.json",
        Path.home() / ".notebooklm" / "master_token.json",
    ]
    for a in adaylar:
        if a.exists() and a.stat().st_size > 20:
            return a
    return None


def secret_yaz(deger: str) -> bool:
    """GitHub Secrets API — libsodium sealed box."""
    pat = (os.environ.get("GH_PAT") or "").strip()
    if not pat:
        print("⚠️ GH_PAT yok — secret'a yazılmadı. Değeri elle eklemelisin.")
        return False
    try:
        from nacl import encoding, public
    except Exception:
        print("⚠️ pynacl yok. Kur: pip install pynacl")
        return False
    import urllib.request

    bas = {"Authorization": f"Bearer {pat}",
           "Accept": "application/vnd.github+json",
           "X-GitHub-Api-Version": "2022-11-28",
           "User-Agent": "bobi-tv-token"}
    url = f"https://api.github.com/repos/{REPO}/actions/secrets/public-key"
    with urllib.request.urlopen(urllib.request.Request(url, headers=bas),
                                timeout=30) as r:
        anahtar = json.loads(r.read())

    pk = public.PublicKey(anahtar["key"].encode(), encoding.Base64Encoder())
    sifreli = base64.b64encode(
        public.SealedBox(pk).encrypt(deger.encode())).decode()
    veri = json.dumps({"encrypted_value": sifreli,
                       "key_id": anahtar["key_id"]}).encode()
    url = f"https://api.github.com/repos/{REPO}/actions/secrets/{SECRET_ADI}"
    req = urllib.request.Request(url, data=veri, headers=bas, method="PUT")
    with urllib.request.urlopen(req, timeout=30) as r:
        if r.status in (201, 204):
            print(f"✅ GitHub secret yazıldı: {SECRET_ADI}")
            return True
    print(f"⚠️ secret yazılamadı (HTTP {r.status})")
    return False


def dogrula() -> int:
    """Master token'dan çerez üretilebiliyor mu? (gerçek okuma testi)"""
    print("=" * 62)
    print("ADIM 3/3 — Token doğrulanıyor (defter listesi okunacak)")
    print("=" * 62)
    os.environ.pop("NOTEBOOKLM_AUTH_JSON", None)
    r = subprocess.run(["notebooklm", "auth", "refresh", "--verify"],
                       capture_output=True, text=True, timeout=300)
    cikti = ((r.stdout or "") + (r.stderr or "")).strip()
    print(cikti[-1200:] if cikti else "(çıktı yok)")
    return r.returncode


def main() -> int:
    ap = argparse.ArgumentParser(description="NotebookLM master token kur")
    ap.add_argument("--eposta", default=os.environ.get("NOTEBOOK_EMAIL", ""))
    ap.add_argument("--secret-yazma", action="store_true")
    a = ap.parse_args()

    if not a.eposta:
        print("❌ e-posta gerekli:  --eposta hesap@gmail.com")
        return 2

    if giris_yap(a.eposta) != 0:
        return 1

    print("\n" + "=" * 62)
    print("ADIM 2/3 — Token dosyası aranıyor")
    print("=" * 62)
    dosya = token_dosyasi()
    if not dosya:
        print("❌ master_token.json bulunamadı.")
        print(f"   Beklenen yer: {_profil_dizini() / 'master_token.json'}")
        return 1
    deger = dosya.read_text(encoding="utf-8").strip()
    dosya.chmod(0o600)
    print(f"✅ bulundu: {dosya}")
    print(f"   uzunluk: {len(deger)} krkt (değer basılmıyor)")

    if a.secret_yazma:
        print(f"   → secret'a yazılmadı (--secret-yazma verilmedi)")
        print(f"   Değeri elle eklemek için: {dosya}")
    else:
        secret_yaz(deger)

    kod = dogrula()
    print()
    if kod == 0:
        print("✅ KURULUM TAMAM — artık NotebookLM oturumu kendini yeniliyor.")
        print("   Sıradaki: Actions → 'Notebook Hattı' → Run workflow")
    else:
        print("❌ doğrulama başarısız — çıktıyı bana göster.")
    return kod


if __name__ == "__main__":
    sys.exit(main())
