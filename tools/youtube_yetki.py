"""YouTube OAuth yetkilendirme — tek komutla yeni refresh token üret.

SORUN (2026-11-08): Yükleme `invalid_grant / Token has been expired or revoked`
verdi. Sebep YouTube kodu değil: Google, "Testing" modundaki OAuth uygulamasının
refresh token'ını **7 günde** geçersiz kılıyor ve test kullanıcısı sınırı var.

ÇÖZÜM: Tarayıcıda bir kez izin verip yeni refresh token almak. İki yol:

  A) GitHub Actions üzerinden (sunucuda tarayıcı yok — bu yol kullanılır)
     Workflow "YouTube Yetki" çalıştırılır, log'da çıkan adrese gidilir,
     izin verilir, çıkan kodu forma yapıştırılır → secret kendiliğinden yazılır.

  B) Kendi bilgisayarında
     `python3 tools/youtube_yetki.py --yerel`

ÜRETİLEN secret: YOUTUBE_TOKEN (client_id, client_secret, refresh_token, token_uri)
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

#: YouTube yükleme + kapak + yorum izinleri.
KAPSAM = " ".join([
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",
])

YONLENDIRME = "urn:ietf:wg:oauth:2.0:oob"
TOKEN_URI = "https://oauth2.googleapis.com/token"

REPO = "mehetgege3-cmyk/bobi-tv"


def _istemci() -> tuple[str, str]:
    """client_id + client_secret — YOUTUBE_CLIENT_SECRET secret'ından."""
    ham = (os.environ.get("YOUTUBE_CLIENT_SECRET") or "").strip()
    if not ham:
        raise SystemExit("HATA: YOUTUBE_CLIENT_SECRET boş")
    d = json.loads(ham)
    # Google'un indirdiği dosya iki biçimde gelir: {"installed": {...}} veya düz.
    for anahtar in ("installed", "web", "web_application", "oauth_client"):
        if anahtar in d:
            d = d[anahtar]
            break
    return d["client_id"], d["client_secret"]


def yetki_adresi(client_id: str) -> str:
    q = urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": YONLENDIRME,
        "response_type": "code",
        "scope": KAPSAM,
        "access_type": "offline",
        "prompt": "consent",          # refresh_token'ı ZORLA ver
    })
    return f"https://accounts.google.com/o/oauth2/v2/auth?{q}"


def kod_ile_token(kod: str) -> dict:
    client_id, client_secret = _istemci()
    veri = urllib.parse.urlencode({
        "code": kod.strip(),
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": YONLENDIRME,
        "grant_type": "authorization_code",
    }).encode()
    req = urllib.request.Request(TOKEN_URI, data=veri, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            cevap = json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"hata": f"HTTP {e.code}: {e.read().decode(errors='replace')[:300]}"}

    if "refresh_token" not in cevap:
        return {"hata": f"refresh_token gelmedi: {list(cevap)}"}
    return {
        "token": cevap.get("access_token", ""),
        "refresh_token": cevap["refresh_token"],
        "client_id": client_id,
        "client_secret": client_secret,
        "token_uri": TOKEN_URI,
        "scopes": KAPSAM.split(),
    }


def dogrula(token_json: dict) -> str | None:
    """Yeni token'la kanal bilgisini oku — gerçekten yetkili mi?"""
    veri = urllib.parse.urlencode({
        "client_id": token_json["client_id"],
        "client_secret": token_json["client_secret"],
        "refresh_token": token_json["refresh_token"],
        "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request(TOKEN_URI, data=veri, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            access = json.loads(r.read())["access_token"]
    except Exception as e:
        return f"token yenilenemedi: {type(e).__name__}: {e}"

    url = ("https://www.googleapis.com/youtube/v3/channels"
           "?part=snippet&mine=true")
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {access}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read())
    except Exception as e:
        return f"kanal okunamadı: {type(e).__name__}: {e}"
    adlar = [c["snippet"]["title"] for c in d.get("items", [])]
    if not adlar:
        return "kanal bulunamadı (izin verilen hesapta kanal yok)"
    print(f"✅ kanal: {', '.join(adlar)}")
    print("✅ yükleme izni: var")
    return None


def secret_yaz(token_json: dict) -> bool:
    """YOUTUBE_TOKEN secret'ını GitHub'a yaz (libsodium sealed box)."""
    pat = (os.environ.get("GH_PAT") or "").strip()
    if not pat:
        print("⚠️ GH_PAT yok — secret yazılmadı")
        return False
    try:
        from nacl import encoding, public
    except Exception:
        print("⚠️ pynacl yok")
        return False

    deger = json.dumps(token_json)
    bas = {"Authorization": f"Bearer {pat}",
           "Accept": "application/vnd.github+json",
           "X-GitHub-Api-Version": "2022-11-28",
           "User-Agent": "bobi-tv-yt"}
    url = f"https://api.github.com/repos/{REPO}/actions/secrets/public-key"
    with urllib.request.urlopen(urllib.request.Request(url, headers=bas),
                                timeout=30) as r:
        k = json.loads(r.read())
    pk = public.PublicKey(k["key"].encode(), encoding.Base64Encoder())
    sif = base64.b64encode(public.SealedBox(pk).encrypt(deger.encode())).decode()
    body = json.dumps({"encrypted_value": sif,
                       "key_id": k["key_id"]}).encode()
    url = f"https://api.github.com/repos/{REPO}/actions/secrets/YOUTUBE_TOKEN"
    req = urllib.request.Request(url, data=body, headers=bas, method="PUT")
    with urllib.request.urlopen(req, timeout=30) as r:
        if r.status in (201, 204):
            print("✅ YOUTUBE_TOKEN secret'ı güncellendi")
            return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description="YouTube OAuth yetkilendirme")
    ap.add_argument("--adres", action="store_true", help="yalnız izin adresini bas")
    ap.add_argument("--kod", default="", help="tarayıcıda çıkan kodu ver")
    ap.add_argument("--yerel", action="store_true",
                    help="tarayıcıyı kendin aç (bilgisayarda çalıştır)")
    a = ap.parse_args()

    client_id, _ = _istemci()
    adres = yetki_adresi(client_id)

    if a.adres:
        print(adres)
        return 0

    if a.yerel and not a.kod:
        import webbrowser

        print("Tarayıcı açılıyor — Google hesabına giriş yapıp izin ver.")
        print(f"\nAdres: {adres}\n")
        try:
            webbrowser.open(adres)
        except Exception:
            pass
        a.kod = input("Ekranda çıkan kodu yapıştır: ").strip()

    if not a.kod:
        print("İzin adresi (tarayıcıda aç):")
        print(adres)
        print("\nSonra: --kod <çıkan kod>")
        return 0

    print("→ kod değiştiriliyor...")
    token_json = kod_ile_token(a.kod)
    if "hata" in token_json:
        print(f"❌ {token_json['hata']}")
        return 1
    print("✅ refresh_token alındı (değer basılmıyor)")

    hata = dogrula(token_json)
    if hata:
        print(f"❌ {hata}")
        return 1

    if not secret_yaz(token_json):
        hedef = Path("/tmp/youtube_token.json")
        hedef.write_text(json.dumps(token_json), encoding="utf-8")
        print(f"⚠️ secret yazılamadı — dosya: {hedef}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
