"""Arena çerezini kendini besleyen hale getirir (2026-11-12 kullanıcı isteği: "Yap").

SORUN: `ARENA_COOKIES_JSON` secret'ı elle alınan bir "anlık fotoğraf". Arena
kısa ömürlü access token + dönen (rotating) refresh token kullanıyor; tarayıcı
token'ı yeniledikçe eski kopya yetim kalıyor ve 1-2 gün içinde ölüyor.

ÇÖZÜM: Playwright oturumu her kurulduğunda, oturumun GÜNCEL `arena-auth-prod-v1.*`
çerezleri okunur. Yeni oturum gerçekten kullanılabilir görünüyorsa (login modalı
ÇIKMADIYSA) güncel çerez GitHub secret'ına geri yazılır. Böylece kullanıcı çerezi
bir kez verir, sistem kendini besler.

GÜVENLİK (kullanıcı isteği: "yaz, doğrula, olmazsa eskisini koru"):
  • Eski secret ASLA elle silinmez; yeni değer PUT ile üzerine yazılır, başarısız
    olursa eski değer yerinde kalır.
  • Yazılacak değer önce kendi okuyucusuyla (build_clean_arena_cookie) DOĞRULANIR:
    en az bir `arena-auth-prod-v1.*` parçası ve base64 gövde şart.
  • Login modalı görüldüyse (oturum düşmüşse) HİÇ yazılmaz — ölü çerez yazmak
    çalışan çerezi bozar.
  • Secret'a yazılan değer, `sanitize_cookie_json` ile üretim hattının okuduğu
    JSON biçimindedir (round-trip: yaz → oku → aynı çerez).
"""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

REPO = "mehetgege3-cmyk/bobi-tv"
SECRET_ADI = "ARENA_COOKIES_JSON"
COOKIE_ADI = "arena-auth-prod-v1"
DURUM_YOLU = Path("bobi_tv/state/arena_cerez.json")


# ---------------------------------------------------------------------------
# 1) Çerez toplama + doğrulama
# ---------------------------------------------------------------------------


def cerezleri_topla(cerezler: list[dict]) -> list[dict]:
    """Playwright cookie listesinden Arena oturum çerezlerini seçer."""
    return [
        {"name": str(c["name"]), "value": str(c["value"])}
        for c in (cerezler or [])
        if isinstance(c, dict) and str(c.get("name", "")).startswith(COOKIE_ADI)
    ]


def secret_paketi_olustur(cerezler: list[dict]) -> str | None:
    """Playwright çerezlerini, üretim hattının beklediği JSON metnine çevirir.

    Üretim tarafı `sanitize_cookie_json` + `build_clean_arena_cookie` ile
    `arena-auth-prod-v1.*` parçalarını okur; burada aynı biçim üretilir.
    """
    parcalar = cerezleri_topla(cerezler)
    if not parcalar:
        return None
    metin = json.dumps(parcalar, ensure_ascii=False)
    return metin if secret_dogrula(metin) else None


def secret_dogrula(metin: str) -> bool:
    """Yazmadan ÖNCE doğrulama: çerez okunabilir mi? (round-trip testi)"""
    if not metin or COOKIE_ADI not in metin:
        return False
    try:
        from modules.arena_api import build_clean_arena_cookie

        temiz = build_clean_arena_cookie(json.loads(metin))
    except Exception:
        return False
    return bool(temiz) and len(str(temiz)) > 40


# ---------------------------------------------------------------------------
# 2) GitHub secret yazma
# ---------------------------------------------------------------------------


def _token() -> str:
    for ad in ("GH_SECRET_PAT", "GH_PAT"):
        deger = str(os.environ.get(ad) or "").strip()
        if deger:
            return deger
    return ""


def _istek(url: str, veri: dict | None = None, yontem: str = "GET") -> dict:
    token = _token()
    r = urllib.request.Request(
        url,
        data=json.dumps(veri).encode() if veri is not None else None,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
        method=yontem,
    )
    with urllib.request.urlopen(r, timeout=30) as c:
        govde = c.read()
        return json.loads(govde) if govde else {}


def secret_yaz(metin: str, repo: str = REPO) -> tuple[bool, str]:
    """Değeri GitHub Actions secret'ına yazar. (basari, mesaj) döndürür."""
    if not _token():
        return False, "GH_PAT/GH_SECRET_PAT yok — secret yazılmadı (mevcut çerez korunuyor)"
    if not secret_dogrula(metin):
        return False, "doğrulama başarısız — secret YAZILMADI (mevcut çerez korunuyor)"
    try:
        try:
            from nacl import encoding, public  # type: ignore
        except ImportError:
            return False, "PyNaCl kurulu değil — secret yazılmadı (mevcut çerez korunuyor)"

        pk = _istek(f"https://api.github.com/repos/{repo}/actions/secrets/public-key")
        kutu = public.SealedBox(public.PublicKey(pk["key"].encode(), encoding.Base64Encoder()))
        sifreli = base64.b64encode(kutu.encrypt(metin.encode("utf-8"))).decode()
        _istek(
            f"https://api.github.com/repos/{repo}/actions/secrets/{SECRET_ADI}",
            {"encrypted_value": sifreli, "key_id": pk["key_id"]},
            "PUT",
        )
        return True, f"{SECRET_ADI} güncellendi ({len(metin)} karakter)"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code} — secret yazılamadı, mevcut çerez korunuyor"
    except Exception as e:  # pragma: no cover
        return False, f"hata: {str(e)[:120]} — mevcut çerez korunuyor"


# ---------------------------------------------------------------------------
# 3) Durum kaydı (panel/ölçüm için)
# ---------------------------------------------------------------------------


def durum_yaz(guncellendi: bool, mesaj: str, yol: Path | None = None) -> dict:
    hedef = yol or DURUM_YOLU
    kayit = {
        "zaman": datetime.now(UTC).isoformat(),
        "guncellendi": bool(guncellendi),
        "mesaj": str(mesaj)[:300],
    }
    try:
        hedef.parent.mkdir(parents=True, exist_ok=True)
        gecmis = []
        if hedef.exists():
            eski = json.loads(hedef.read_text(encoding="utf-8"))
            gecmis = list(eski.get("gecmis") or [])[-20:]
        gecmis.append(kayit)
        hedef.write_text(
            json.dumps({"son": kayit, "gecmis": gecmis}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as e:  # pragma: no cover
        print(f"[Çerez] Durum yazılamadı: {str(e)[:100]}")
    return kayit


# ---------------------------------------------------------------------------
# 4) Oturumdan çerez alıp yazma (tek giriş noktası)
# ---------------------------------------------------------------------------


def oturumdan_guncelle(cerezler: list[dict], *, oturum_saglikli: bool = True) -> dict:
    """Kullanılabilir bir Arena oturumundan gelen çerezleri secret'a yazar.

    `oturum_saglikli=False` (login modalı görüldü / cevap alınamadı) ise
    HİÇBİR ŞEY yazılmaz — ölü çerez, çalışan çerezi bozmasın.
    """
    if not oturum_saglikli:
        return durum_yaz(False, "oturum sağlıklı değil — yazılmadı")
    metin = secret_paketi_olustur(cerezler)
    if not metin:
        return durum_yaz(False, "güncel çerez bulunamadı/doğrulanamadı — yazılmadı")
    basari, mesaj = secret_yaz(metin)
    print(f"[Çerez] {'✅' if basari else '⚠️'} {mesaj}")
    return durum_yaz(basari, mesaj)
