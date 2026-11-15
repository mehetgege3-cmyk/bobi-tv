"""NotebookLM kimliğini kur, tazele ve kendini iyileştir.

SORUN (2026-11-08 ölçümü):
  Google `__Secure-1PSIDTS` çerezini saatte bir döndürüyor. CI'daki statik
  kopya eskiyince NotebookLM "signed-out page" veriyor. Kanıt: 18:13'te
  aynı secret 22 defter gördü, 18:32'de AuthError.

ÇÖZÜM — üç kimlik modu (sırayla denenir):

  A) **NOTEBOOKLM_AUTH_JSON** (storage_state.json, 39 çerez) ← TERCİH EDİLEN
     Tarayıcının tam durumu. Hem `SID`+`SAPISID` (ikincil bağ) hem
     `__Secure-1PSIDTS` içinde. Dosyaya yazılır, `auth refresh` ile tazelenir,
     TAZE değer secret'a geri yazılır → sonraki koşu taze başlar.

  B) **NOTEBOOKLM_MASTER_TOKEN_JSON** (kalıcı, tarayıcısız)
     Token'dan çerez üretilir. Şifre değişse bile geçerli.

  C) **NOTEBOOK_GOOGLE** (kısmi çerez listesi — eski yol, yedek)
     Eksik alanlarla doldurulur; saatlik döndürmede kırılgan.

KÜTÜPHANENİN KENDİ BELGESİ (`data/SKILL.md`):
  "Inline NOTEBOOKLM_AUTH_JSON is only a short-lived fallback; it bypasses
   this recovery path." → Bu yüzden değer DOSYAYA yazılıp dosya üzerinden
  tazeleniyor; inline bırakılmıyor.

KULLANIM:
    python3 tools/notebook_cerez_tazele.py            # kur + tazele + doğrula
    python3 tools/notebook_cerez_tazele.py --secret-yazma   # secret'a yazma

ÇIKTI: /tmp/nb_state.json — hat ve temizlik araçları bunu kullanır.
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
from pathlib import Path

#: Tazelenmiş durum burada tutulur. Hat ve temizlik araçları bunu okur.
DURUM = Path("/tmp/nb_state.json")

REPO = "mehetgege3-cmyk/bobi-tv"

#: notebooklm-py'nin zorunlu çerezleri.
ZORUNLU = ("SID", "__Secure-1PSIDTS")


def _profil_dizini() -> Path:
    kok = Path(os.environ.get("NOTEBOOKLM_HOME") or (Path.home() / ".notebooklm"))
    return kok / "profiles" / (os.environ.get("NOTEBOOKLM_PROFILE") or "default")


# --------------------------------------------------------------------------
# Durum yazımı
# --------------------------------------------------------------------------
def _storage_state_yaz(ham: str) -> dict:
    """NOTEBOOKLM_AUTH_JSON → /tmp/nb_state.json (olduğu gibi, normalize)."""
    veri = json.loads(ham)
    cerez = veri.get("cookies", veri if isinstance(veri, list) else [])
    temiz = []
    for c in cerez:
        if not isinstance(c, dict) or not c.get("name") or not c.get("value"):
            continue
        d = c.get("domain") or ".google.com"
        if not d.startswith("."):
            d = "." + d.lstrip(".")
        exp = c.get("expires")
        temiz.append({
            "name": str(c["name"]), "value": str(c["value"]), "domain": d,
            "path": c.get("path") or "/",
            "expires": exp if isinstance(exp, (int, float)) and exp > 0 else -1,
            # Tarayıcıdan gelen değeri KORU — zorla True yazmak Google'ın
            # çerez eşleştirmesini bozuyor (2026-11-15 CookieMismatch).
            "httpOnly": bool(c.get("httpOnly", True)),
            "secure": bool(c.get("secure", True)),
            "sameSite": c.get("sameSite") or "None",
        })
    depo = {"cookies": temiz, "origins": veri.get("origins", [])}
    adlar = {c["name"] for c in temiz}
    eksik = [z for z in ZORUNLU if z not in adlar]
    if eksik:
        raise SystemExit(f"HATA: zorunlu çerez eksik → {eksik}")
    DURUM.write_text(json.dumps(depo, ensure_ascii=False), encoding="utf-8")
    DURUM.chmod(0o600)
    print(f"→ storage_state yazıldı: {DURUM} ({len(temiz)} çerez, "
          f"{len(depo['origins'])} origin)")
    return depo


def _cerez_listesinden(ham: str) -> dict:
    """NOTEBOOK_GOOGLE (kısmi liste) → storage_state. Eksik alanlar doldurulur."""
    if ham.lstrip().startswith(("[", "{")):
        veri = json.loads(ham)
        if isinstance(veri, dict) and "cookies" in veri:
            veri = veri["cookies"]
        cerez = ([c for c in veri if isinstance(c, dict) and c.get("name")]
                 if isinstance(veri, list)
                 else [{"name": k, "value": v} for k, v in veri.items()])
    else:
        cerez = []
        for parca in ham.split(";"):
            if "=" in parca:
                k, v = parca.strip().split("=", 1)
                cerez.append({"name": k, "value": v})
    return _storage_state_yaz(json.dumps({"cookies": cerez, "origins": []}))


# --------------------------------------------------------------------------
# Tazeleme / doğrulama
# --------------------------------------------------------------------------
def _tazele(dosya: Path = DURUM) -> bool:
    """`notebooklm --storage <dosya> auth refresh --verify`."""
    r = subprocess.run(
        ["notebooklm", "--storage", str(dosya), "auth", "refresh", "--verify"],
        capture_output=True, text=True, timeout=300,
    )
    cikti = ((r.stdout or "") + (r.stderr or "")).strip()
    print(cikti[-1200:] if cikti else "(çıktı yok)")
    return r.returncode == 0


def _dogrula(dosya: Path = DURUM) -> int:
    """Tazelenmiş çerezle gerçek okuma — kimlik gerçekten çalışıyor mu?"""
    import asyncio

    from notebooklm import NotebookLMClient

    os.environ.pop("NOTEBOOKLM_AUTH_JSON", None)
    os.environ["NOTEBOOKLM_AUTH_JSON"] = dosya.read_text(encoding="utf-8")

    async def _dene() -> int:
        async with NotebookLMClient.from_storage() as c:
            return len(await c.notebooks.list())

    try:
        adet = asyncio.run(_dene())
    except Exception as e:
        print(f"❌ doğrulama hatası: {type(e).__name__}: {e}")
        return -1
    return adet


# --------------------------------------------------------------------------
# Secret geri yazma (kendini iyileştirme)
# --------------------------------------------------------------------------
def _secret_guncelle(secret_adi: str, deger: str) -> bool:
    """GitHub Secrets API — libsodium sealed box. Değer loglanmaz."""
    pat = (os.environ.get("GH_PAT") or "").strip()
    if not pat:
        print(f"⚠️ GH_PAT yok — {secret_adi} güncellenmedi (yalnız bu koşu taze)")
        return False
    try:
        from nacl import encoding, public
    except Exception:
        print("⚠️ pynacl yok — secret güncellenmedi")
        return False
    import urllib.request

    bas = {"Authorization": f"Bearer {pat}",
           "Accept": "application/vnd.github+json",
           "X-GitHub-Api-Version": "2022-11-28",
           "User-Agent": "bobi-tv-cerez"}
    try:
        url = f"https://api.github.com/repos/{REPO}/actions/secrets/public-key"
        with urllib.request.urlopen(urllib.request.Request(url, headers=bas),
                                    timeout=30) as r:
            anahtar = json.loads(r.read())
        pk = public.PublicKey(anahtar["key"].encode(), encoding.Base64Encoder())
        sifreli = base64.b64encode(
            public.SealedBox(pk).encrypt(deger.encode())).decode()
        veri = json.dumps({"encrypted_value": sifreli,
                           "key_id": anahtar["key_id"]}).encode()
        url = f"https://api.github.com/repos/{REPO}/actions/secrets/{secret_adi}"
        req = urllib.request.Request(url, data=veri, headers=bas, method="PUT")
        with urllib.request.urlopen(req, timeout=30) as r:
            if r.status in (201, 204):
                print(f"✅ {secret_adi} tazelendi — sonraki koşu taze çerezle başlar")
                return True
    except Exception as e:
        print(f"⚠️ secret yazılamadı: {type(e).__name__}: {e}")
    return False


# --------------------------------------------------------------------------
# Akış
# --------------------------------------------------------------------------
def main() -> int:
    yaz = "--secret-yazma" not in sys.argv
    DURUM.unlink(missing_ok=True)

    # ---- A) storage_state (tercih edilen) --------------------------------
    ham = (os.environ.get("NOTEBOOKLM_AUTH_JSON") or "").strip()
    if ham:
        print("=== kimlik modu: STORAGE_STATE (39 çerez, tarayıcı çıktısı) ===")
        _storage_state_yaz(ham)
        if not _tazele():
            print("⚠️ tazeleme başarısız — mevcut çerezle doğrulanıyor")
        adet = _dogrula()
        if adet <= 0:
            print("❌ kimlik geçersiz")
            return 1
        print(f"✅ kimlik geçerli — {adet} defter")
        if yaz:
            _secret_guncelle("NOTEBOOKLM_AUTH_JSON",
                             DURUM.read_text(encoding="utf-8"))
        return 0

    # ---- B) master token (kalıcı) ---------------------------------------
    if (os.environ.get("NOTEBOOKLM_MASTER_TOKEN_JSON") or "").strip():
        print("=== kimlik modu: MASTER TOKEN ===")
        d = _profil_dizini()
        d.mkdir(parents=True, exist_ok=True)
        (d / "master_token.json").write_text(
            os.environ.pop("NOTEBOOKLM_MASTER_TOKEN_JSON"), encoding="utf-8")
        (d / "master_token.json").chmod(0o600)
        os.environ.pop("NOTEBOOKLM_AUTH_JSON", None)
        if not _tazele(d / "storage_state.json"):
            print("❌ master token ile çerez üretilemedi")
            return 1
        depo = d / "storage_state.json"
        if not depo.exists():
            print(f"❌ {depo} oluşmadı")
            return 1
        DURUM.write_text(depo.read_text(encoding="utf-8"), encoding="utf-8")
        DURUM.chmod(0o600)
        adet = _dogrula()
        if adet <= 0:
            return 1
        print(f"✅ kimlik geçerli — {adet} defter")
        return 0

    # ---- C) kısmi çerez (yedek) -----------------------------------------
    ham = (os.environ.get("NOTEBOOK_GOOGLE") or "").strip()
    if not ham:
        print("❌ kimlik yok: NOTEBOOKLM_AUTH_JSON / NOTEBOOKLM_MASTER_TOKEN_JSON"
              " / NOTEBOOK_GOOGLE — hiçbiri tanımlı değil")
        return 2
    print("=== kimlik modu: KISMİ ÇEREZ (yedek yol) ===")
    _cerez_listesinden(ham)
    if not _tazele():
        print("⚠️ tazeleme başarısız — mevcut çerezle doğrulanıyor")
    adet = _dogrula()
    if adet <= 0:
        print("❌ kimlik geçersiz — NOTEBOOKLM_AUTH_JSON secret'ı gerekli")
        return 1
    print(f"✅ kimlik geçerli — {adet} defter")
    if yaz:
        _secret_guncelle("NOTEBOOK_GOOGLE", DURUM.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
