"""NotebookLM çerezini tazele — CI'da kendi kendini iyileştiren kimlik.

SORUN (2026-11-08'de ölçüldü):
  Google `__Secure-1PSIDTS` çerezini yaklaşık saatte bir **döndürüyor**.
  Secret'taki kopya eskiyince NotebookLM "signed-out page" veriyor.
  Kanıt: 18:13'te aynı secret çalıştı (22 defter), 18:32'de aynı secret
  AuthError verdi. Secret bozulmadı — arasındaki koşu değeri döndürdü.

ÇÖZÜM (kütüphanenin kendi önerisi, `notebooklm auth refresh --help`):
  * storage_state.json dosya olarak tutulur,
  * `notebooklm auth refresh --verify` dönen çerezi tazeler ve doğrular,
  * tazelenmiş çerez secret'a GERİ YAZILIR → sonraki koşu taze değerle başlar.

  Kütüphane: "Cadence: 15-20 minutes is the recommended interval". Bizim
  kadans seyrek olduğu için her koşunun BAŞINDA tazeleme yapılıyor.

SECRET GÜNCELLEME: `GH_PAT` ile GitHub Secrets API'si (libsodium sealed box).
PAT yoksa tazeleme yine yapılır, sadece kalıcılaşmaz (uyarı basılır).

KULLANIM:
    NOTEBOOK_GOOGLE='...' GH_PAT='...' python3 tools/notebook_cerez_tazele.py
    ... --secret-yazma          # yalnız tazele, secret'a dokunma
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
from pathlib import Path

#: Tazelenmiş storage_state buraya yazılır; hat bu dosyayı kullanır.
DURUM = Path("/tmp/nb_state.json")

#: GitHub deposu / secret adı.
REPO = "mehetgege3-cmyk/bobi-tv"
SECRET_ADI = "NOTEBOOK_GOOGLE"


def durum_yaz(ham: str) -> dict:
    """NOTEBOOK_GOOGLE (JSON / ; ayraçlı) → Playwright storage_state dosyası."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools.notebook_video import _depo_hazirla

    # _depo_hazirla ortamdan okur; zaten ortamda var.
    depo = _depo_hazirla()
    DURUM.write_text(json.dumps(depo, ensure_ascii=False), encoding="utf-8")
    DURUM.chmod(0o600)
    print(f"→ storage_state yazıldı: {DURUM} ({len(depo['cookies'])} çerez)")
    return depo


def tazele() -> bool:
    """`notebooklm auth refresh --verify` — dönen çerezi yerinde günceller."""
    r = subprocess.run(
        ["notebooklm", "--storage", str(DURUM), "auth", "refresh", "--verify"],
        capture_output=True, text=True, timeout=300,
    )
    cikti = ((r.stdout or "") + (r.stderr or "")).strip()
    print(cikti[-1500:] if cikti else "(çıktı yok)")
    return r.returncode == 0


def _secret_guncelle(deger: str) -> bool:
    """GitHub Secrets API: public key al → sealed box → PUT."""
    import urllib.request

    pat = (os.environ.get("GH_PAT") or "").strip()
    if not pat:
        print("⚠️ GH_PAT yok — secret güncellenmedi (tazeleme yalnız bu koşu için)")
        return False
    try:
        from nacl import encoding, public
    except Exception:
        print("⚠️ pynacl yok — secret güncellenmedi")
        return False

    bas = {
        "Authorization": f"Bearer {pat}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "bobi-tv-cerez",
    }
    url = f"https://api.github.com/repos/{REPO}/actions/secrets/public-key"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=bas),
                                    timeout=30) as r:
            anahtar = json.loads(r.read())
    except Exception as e:
        print(f"⚠️ public-key alınamadı: {type(e).__name__}: {e}")
        return False

    pk = public.PublicKey(anahtar["key"].encode(), encoding.Base64Encoder())
    sifreli = base64.b64encode(
        public.SealedBox(pk).encrypt(deger.encode())).decode()

    veri = json.dumps({"encrypted_value": sifreli,
                       "key_id": anahtar["key_id"]}).encode()
    url = f"https://api.github.com/repos/{REPO}/actions/secrets/{SECRET_ADI}"
    try:
        req = urllib.request.Request(url, data=veri, headers=bas, method="PUT")
        with urllib.request.urlopen(req, timeout=30) as r:
            if r.status in (201, 204):
                print(f"✅ {SECRET_ADI} secret'ı tazelendi (sonraki koşu taze başlar)")
                return True
    except Exception as e:
        print(f"⚠️ secret yazılamadı: {type(e).__name__}: {e}")
    return False


def main() -> int:
    ham = (os.environ.get("NOTEBOOK_GOOGLE") or "").strip()
    if not ham:
        print("❌ NOTEBOOK_GOOGLE boş")
        return 2

    DURUM.unlink(missing_ok=True)
    durum_yaz(ham)

    if not tazele():
        print("❌ çerez tazelenemedi — oturum gerçekten ölü, yeniden giriş gerekli")
        return 1

    # Doğrulama: tazelenmiş çerezle defter listesi okunabiliyor mu?
    from notebooklm import NotebookLMClient
    import asyncio

    async def _dene() -> int:
        async with NotebookLMClient.from_storage(path=str(DURUM)) as c:
            nbs = await c.notebooks.list()
            print(f"✅ kimlik geçerli — {len(nbs)} defter")
            return len(nbs)

    os.environ.pop("NOTEBOOKLM_AUTH_JSON", None)
    os.environ["NOTEBOOKLM_AUTH_JSON"] = DURUM.read_text(encoding="utf-8")
    try:
        adet = asyncio.run(_dene())
    except Exception as e:
        print(f"❌ tazeleme sonrası kimlik hatası: {type(e).__name__}: {e}")
        return 1
    if adet <= 0:
        print("❌ defter listesi boş")
        return 1

    if "--secret-yazma" not in sys.argv:
        yeni = DURUM.read_text(encoding="utf-8")
        _secret_guncelle(yeni)
    return 0


if __name__ == "__main__":
    sys.exit(main())
