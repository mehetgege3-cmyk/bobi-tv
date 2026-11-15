"""NotebookLM çerezini tazele — CI'da kendi kendini iyileştiren kimlik.

SORUN (2026-11-08'de ölçüldü):
  Google `__Secure-1PSIDTS` çerezini yaklaşık saatte bir **döndürüyor**.
  Secret'taki kopya eskiyince NotebookLM "signed-out page" veriyor.
  Kanıt: 18:13'te aynı secret çalıştı (22 defter), 18:32'de aynı secret
  AuthError verdi. Secret bozulmadı — arasındaki koşu değeri döndürdü.

KÜTÜPHANENİN KENDİ BELGESİ (`data/SKILL.md`), birebir:
    "For unattended or headless work, prefer durable profile-backed
     master-token auth over a copied cookie snapshot... A sibling master token
     can automatically re-mint expired file-backed cookies. Inline
     NOTEBOOKLM_AUTH_JSON is only a short-lived fallback; it bypasses this
     recovery path."

  Yani çerez kopyası CI için YETERSİZ: her döndürmede ölüyor ve kurtarma yolu
  (master token) devre dışı kalıyor. İki mod destekleniyor:

  A) **MASTER TOKEN (kalıcı, önerilen)** — `NOTEBOOKLM_MASTER_TOKEN_JSON`
     secret'ı varsa profile yazılır (0600), `notebooklm auth refresh`
     çerezleri kendisi üretir. Oturum ölse bile kendini yeniler.
  B) **ÇEREZ (geçici)** — `NOTEBOOK_GOOGLE` varsa eski yol. Saatlik
     döndürmede kırılır; yalnız A yoksa kullanılır.

ÇEREZ TAZELEME (B modu, kütüphanenin önerisi):
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


def _profil_dizini() -> Path:
    """`notebooklm` profil dizini (NOTEBOOKLM_HOME / NOTEBOOKLM_PROFILE)."""
    kok = Path(os.environ.get("NOTEBOOKLM_HOME") or (Path.home() / ".notebooklm"))
    return kok / "profiles" / (os.environ.get("NOTEBOOKLM_PROFILE") or "default")


def _master_token_kur() -> Path | None:
    """`NOTEBOOKLM_MASTER_TOKEN_JSON` → profil master_token.json (0600).

    Belge: "Write its exact value to the selected profile's master_token.json
    with mode 0600, unset it, then run `notebooklm auth refresh` to mint
    storage_state.json."

    Döner: kurulan dosya yolu (yoksa None).
    """
    ham = (os.environ.get("NOTEBOOKLM_MASTER_TOKEN_JSON") or "").strip()
    if not ham:
        return None
    d = _profil_dizini()
    d.mkdir(parents=True, exist_ok=True)
    hedef = d / "master_token.json"
    hedef.write_text(ham, encoding="utf-8")
    hedef.chmod(0o600)
    # Belge şartı: değişkeni bırakma.
    os.environ.pop("NOTEBOOKLM_MASTER_TOKEN_JSON", None)
    print(f"→ master token kuruldu: {hedef} (0600)")
    return hedef


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
    # ---- A) MASTER TOKEN: kalıcı, kendini yenileyen kimlik ----------------
    if (os.environ.get("NOTEBOOKLM_MASTER_TOKEN_JSON") or "").strip():
        print("=== kimlik modu: MASTER TOKEN (kalıcı) ===")
        if not _master_token_kur():
            print("❌ master token yazılamadı")
            return 1
        # Çerezleri token'dan üret. inline NOTEBOOKLM_AUTH_JSON kurtarma yolunu
        # kapatıyor (belge) — burada hiç kullanmıyoruz.
        os.environ.pop("NOTEBOOKLM_AUTH_JSON", None)
        r = subprocess.run(
            ["notebooklm", "auth", "refresh", "--verify"],
            capture_output=True, text=True, timeout=300,
        )
        cikti = ((r.stdout or "") + (r.stderr or "")).strip()
        print(cikti[-1500:] if cikti else "(çıktı yok)")
        if r.returncode != 0:
            print("❌ master token ile çerez üretilemedi")
            return 1
        durum = _profil_dizini() / "storage_state.json"
        if not durum.exists():
            print(f"❌ {durum} oluşmadı")
            return 1
        return _dogrula(durum, secret_yazma=True, master=True)

    # ---- B) ÇEREZ: geçici yol --------------------------------------------
    ham = (os.environ.get("NOTEBOOK_GOOGLE") or "").strip()
    if not ham:
        print("❌ ne NOTEBOOKLM_MASTER_TOKEN_JSON ne NOTEBOOK_GOOGLE var")
        return 2

    print("=== kimlik modu: ÇEREZ (geçici — master token önerilir) ===")
    DURUM.unlink(missing_ok=True)
    durum_yaz(ham)

    if not tazele():
        print("❌ çerez tazelenemedi — oturum gerçekten ölü, yeniden giriş gerekli")
        return 1
    return _dogrula(DURUM, secret_yazma="--secret-yazma" not in sys.argv, master=False)


def _dogrula(durum: Path, secret_yazma: bool, master: bool) -> int:
    """Tazelenmiş çerezle gerçek bir okuma yap — kimlik gerçekten çalışıyor mu?"""
    from notebooklm import NotebookLMClient
    import asyncio

    metin = durum.read_text(encoding="utf-8")
    os.environ["NOTEBOOKLM_AUTH_JSON"] = metin

    async def _dene() -> int:
        async with NotebookLMClient.from_storage() as c:
            nbs = await c.notebooks.list()
            return len(nbs)

    try:
        adet = asyncio.run(_dene())
    except Exception as e:
        print(f"❌ doğrulama hatası: {type(e).__name__}: {e}")
        return 1
    if adet <= 0:
        print("❌ defter listesi boş")
        return 1
    print(f"✅ kimlik geçerli — {adet} defter")

    # Master token modunda secret yazmaya gerek YOK: token kendini yeniliyor.
    if secret_yazma and not master:
        _secret_guncelle(metin)
    return 0


if __name__ == "__main__":
    sys.exit(main())
