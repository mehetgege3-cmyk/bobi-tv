"""Gemini WEB istemcisi — çerezle görsel üretimi (API anahtarı GEREKMEZ).

NEDEN: `GEMINI_API_KEY` bu projede görsel kotası `limit: 0` veriyor
(`docs/GEMINI_ENTEGRASYON.md` §9). Gemini WEB'in arka ucu ise **abonelik**
kotasını kullanır: `gemini.google.com`'da görsel üretilebiliyorsa, çerezle de
üretilebilir.

CANLI KANIT (2026-11-13): çerez + StreamGenerate → HTTP 200, 27.690 bayt
`image/jpeg`, 286×512 → `kanit/gemini/web_elma.png`.

GEREKLİ ÇEREZLER (`GEMINI_COOKIES` secret'ı, "ad=değer; ..." biçimi):
  • `__Secure-1PSID`   → ana oturum (uzun ömürlü)
  • `__Secure-1PSIDTS` → zaman damgası (KISA ömürlü, yenilenmeli)

CSRF JETONU: `https://gemini.google.com/app` HTML'inden `SNlM0e`.

GÖVDE BİÇİMİ (kaynaktan doğrulandı: `gemini_webapi` 2.1.1 `client.py`):
  f.req = json.dumps([None, json.dumps(ic_list)])
  ic_list = [None]*81; [0]=[prompt,0,None,None,None,None,0]; [1]=["tr"]
            [2]=metadata(10 öğe); [7]=1; [79]=model; [59]=uuid

GÖRSEL İNDİRME: yanıttaki `googleusercontent.com` URL'i; indirirken de çerez
gerekir. URL sonuna `=s2048` eklenirse daha büyük gelir (ölçüldü: 286×512).

UYARI: `__Secure-1PSIDTS` çabuk ölür; Gemini sekmesi AÇIK kalırsa daha hızlı
ölür. Ayrıca Google bu arayüzü haber vermeden değiştirebilir; kırılırsa
`tools/gemini_cerez_kur.py --kuru` ile oturum canlılığı ölçülür.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

GENERATE = (
    "https://gemini.google.com/_/BardChatUi/data/"
    "assistant.lamda.BardFrontendService/StreamGenerate"
)
INIT = "https://gemini.google.com/app"
BASLIKLAR = {
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "accept-language": "tr-TR,tr;q=0.9,en;q=0.8",
}
METADATA = ["", "", "", None, None, None, None, None, None, ""]

_SON = {"hata": None, "jeton": None}


# ---------------------------------------------------------------------------
# Çerez / jeton
# ---------------------------------------------------------------------------

def cerez() -> str:
    """`GEMINI_COOKIES` secret'ı → Cookie başlığı."""
    ham = (os.environ.get("GEMINI_COOKIES") or "").strip()
    if not ham:
        return ""
    if ham.startswith("["):
        try:
            return "; ".join(
                f"{c['name']}={c['value']}" for c in json.loads(ham) if c.get("name")
            )
        except Exception:
            return ""
    return ham


def hazir_mi() -> bool:
    c = cerez()
    return bool(c) and "__Secure-1PSID" in c


def jeton(cerez_basligi: str | None = None) -> str | None:
    """`gemini.google.com/app` → `SNlM0e` (at) jetonu. Önbelleğe alınır."""
    if _SON["jeton"]:
        return _SON["jeton"]
    c = cerez_basligi or cerez()
    if not c:
        return None
    req = urllib.request.Request(INIT, headers={**BASLIKLAR, "cookie": c})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            html = r.read().decode("utf-8", "replace")
            son = r.geturl()
    except Exception as e:
        _SON["hata"] = f"sayfa: {type(e).__name__} {str(e)[:90]}"
        return None
    if "accounts.google.com" in son:
        _SON["hata"] = "oturum yok (accounts.google.com'a yönlendi)"
        return None
    for kalip in (r'SNlM0e["\']?\s*[:=]\s*["\']([^"\']+)', r'"SNlM0e","([^"]+)"'):
        m = re.search(kalip, html)
        if m:
            _SON["jeton"] = m.group(1)
            return _SON["jeton"]
    _SON["hata"] = "SNlM0e bulunamadı"
    return None


def durum() -> dict:
    return {
        "cerez_var": hazir_mi(),
        "jeton_var": bool(_SON["jeton"]),
        "hata": _SON["hata"],
    }


# ---------------------------------------------------------------------------
# Üretim
# ---------------------------------------------------------------------------

def _govde(prompt: str, at: str) -> tuple[bytes, str]:
    icerik = [prompt, 0, None, None, None, None, 0]
    ic: list = [None] * 81
    ic[0] = icerik
    ic[1] = ["tr"]
    ic[2] = METADATA
    ic[6] = [1]
    ic[7] = 1
    ic[10] = 1
    ic[11] = 0
    ic[17] = [[0]]
    ic[18] = 0
    ic[27] = 1
    ic[30] = [4]
    ic[41] = [1]
    ic[53] = 0
    ic[61] = []
    ic[68] = 1
    ic[79] = 1
    ic[80] = 1
    uid = str(uuid.uuid4()).upper()
    ic[59] = uid
    f_req = json.dumps([None, json.dumps(ic)])
    return urllib.parse.urlencode({"at": at, "f.req": f_req}).encode(), uid


def gorsel_uret(prompt: str, hedef_yol: str, *, sure: int = 240) -> str | None:
    """Görsel üretir ve indirir. Başarısızsa None döner (uydurma yok)."""
    _SON["hata"] = None
    if not prompt.strip():
        return None
    c = cerez()
    if not c:
        _SON["hata"] = "GEMINI_COOKIES yok"
        return None
    at = jeton(c)
    if not at:
        _SON["hata"] = _SON["hata"] or "jeton yok"
        return None

    govde, uid = _govde(prompt, at)
    url = f"{GENERATE}?hl=tr&_reqid=100000&rt=c"
    req = urllib.request.Request(
        url, data=govde, method="POST",
        headers={
            **BASLIKLAR,
            "cookie": c,
            "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
            "origin": "https://gemini.google.com",
            "referer": "https://gemini.google.com/app",
            "x-same-domain": "1",
            "x-goog-ext-525005358-jspb": f'["{uid}",1]',
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=sure) as r:
            yanit = r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        _SON["hata"] = f"StreamGenerate HTTP {e.code}"
        print(f"[GeminiWeb] ❌ {_SON['hata']}", flush=True)
        if e.code in (401, 403):
            _SON["jeton"] = None
        return None
    except Exception as e:
        _SON["hata"] = f"{type(e).__name__}: {str(e)[:100]}"
        print(f"[GeminiWeb] ❌ {_SON['hata']}", flush=True)
        return None

    urls = re.findall(r"https://[A-Za-z0-9._/-]*googleusercontent\.com/[A-Za-z0-9._/=-]+", yanit)
    if not urls:
        _SON["hata"] = "yanıtta görsel URL yok (güvenlik/limit olabilir)"
        print(f"[GeminiWeb] ❌ {_SON['hata']} · yanıt {len(yanit)} karakter", flush=True)
        return None

    yol = Path(hedef_yol)
    yol.parent.mkdir(parents=True, exist_ok=True)
    temel = urls[0].split("=")[0]
    for aday in (temel + "=s2048", urls[0]):
        try:
            r2 = urllib.request.Request(aday, headers={**BASLIKLAR, "cookie": c})
            with urllib.request.urlopen(r2, timeout=120) as r:
                ham = r.read()
            if len(ham) < 5000 or ham[:2] not in (b"\xff\xd8", b"\x89P"):
                continue
            yol.write_bytes(ham)
            print(f"[GeminiWeb] ✅ görsel indi: {len(ham)} bayt → {yol}", flush=True)
            _SON["hata"] = None
            return str(yol)
        except Exception as e:
            print(f"[GeminiWeb] indirme: {type(e).__name__} {str(e)[:80]}", flush=True)
    _SON["hata"] = "görsel indirilemedi"
    return None


def goruntu_uret_ve_sakla(prompt: str, dosya_adi: str = "gemini_web_kapak.png") -> str | None:
    kok = os.environ.get("BOBITV_GECICI_KOK", "kanit")
    return gorsel_uret(prompt, str(Path(kok) / dosya_adi))
