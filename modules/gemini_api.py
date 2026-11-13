"""Gemini API istemcisi — metin ve görsel üretimi.

ÖLÇÜM (2026-11-13, `docs/GEMINI_ENTEGRASYON.md`):
  • Anahtar `GEMINI_API_KEY` GEÇERLİ (404 mesajları "model yok" diyor,
    "anahtar geçersiz" demiyor).
  • METİN: `gemini-3.8-flash` bazen 503 (yüksek talep) → retry ile çözülür.
  • GÖRSEL: tüm görsel modelleri **429, `limit: 0`** → bu projede ücretsiz
    katmanda görsel üretimi TANIMLI DEĞİL. Kodla çözülemez; faturalandırma ya
    da görsel yetkili başka anahtar gerekir. `kota_yok` olarak raporlanır.

Bu modül ASLA görsel uydurmaz: üretim olmazsa `None` döner ve nedenini yazar.
"""

from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

TABAN = "https://generativelanguage.googleapis.com/v1beta/models"
METIN_MODELI = os.environ.get("GEMINI_METIN_MODELI", "gemini-3.8-flash")
GORSEL_MODELI = os.environ.get("GEMINI_GORSEL_MODELI", "gemini-3-pro-image")

# Görsel yetkisi olan modeller (kota varsa sırayla denenir)
# GÜNCEL DOKÜMAN (ai.google.dev/gemini-api/docs/image-generation, 2026-10-26):
#   Nano Banana 2.1          → gemini-nano-banana-2.1        (önerilen)
#   Nano Banana 2 Lite       → gemini-3.1-flash-lite-image
#   Nano Banana 2            → gemini-3.1-flash-image
#   Nano Banana Pro          → gemini-3-pro-image
#   Nano Banana (LEGACY)     → gemini-2.5-flash-image
GORSEL_ADAYLARI = (
    "gemini-nano-banana-2.1",
    "gemini-3.1-flash-image",
    "gemini-3.1-flash-lite-image",
    "gemini-3-pro-image",
    "gemini-2.5-flash-image",
)

_SON = {"hata": None, "kota_yok": False, "yeniden_dene_sn": None}


def anahtar() -> str:
    return (os.environ.get("GEMINI_API_KEY") or "").strip()


def durum() -> dict:
    return {"anahtar_var": bool(anahtar()), **_SON}


def _post(model: str, govde: dict, sure: int = 120) -> tuple[int | None, object]:
    anaht = anahtar()
    if not anaht:
        return None, "GEMINI_API_KEY yok"
    req = urllib.request.Request(
        f"{TABAN}/{model}:generateContent",
        data=json.dumps(govde).encode("utf-8"),
        method="POST",
        headers={"content-type": "application/json", "x-goog-api-key": anaht},
    )
    try:
        with urllib.request.urlopen(req, timeout=sure) as r:
            return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return None, f"{type(e).__name__}: {str(e)[:120]}"


def metin_uret(prompt: str, *, deneme: int = 3, sure: int = 120) -> str | None:
    """Düz metin üretir. 503/timeout'ta üstel geri çekilme ile tekrar dener."""
    if not prompt.strip():
        return None
    govde = {"contents": [{"parts": [{"text": prompt}]}]}
    for i in range(max(1, deneme)):
        kod, veri = _post(METIN_MODELI, govde, sure)
        if kod == 200 and isinstance(veri, dict):
            try:
                parcalar = veri["candidates"][0]["content"]["parts"]
                metin = "".join(p.get("text", "") for p in parcalar).strip()
                if metin:
                    _SON["hata"] = None
                    return metin
            except Exception:
                pass
        _SON["hata"] = f"{kod}: {str(veri)[:140]}"
        print(f"[Gemini] metin deneme {i + 1}/{deneme} → {kod} {str(veri)[:100]}", flush=True)
        if kod in (400, 401, 403, 404):
            return None  # kalıcı hata; tekrar denemek boşa
        time.sleep(2 ** i * 2)
    return None


def gorsel_uret(prompt: str, hedef_yol: str, *, en_az: int = 5000) -> str | None:
    """Görsel üretir ve indirir. Kota yoksa `None` + `kota_yok=True`."""
    if not prompt.strip():
        return None
    govde = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
            "imageConfig": {"aspectRatio": "9:16"},
        },
    }
    yol = Path(hedef_yol)
    yol.parent.mkdir(parents=True, exist_ok=True)
    for model in GORSEL_ADAYLARI:
        kod, veri = _post(model, govde, sure=180)
        if kod == 200 and isinstance(veri, dict):
            try:
                for parca in veri["candidates"][0]["content"]["parts"]:
                    inline = parca.get("inlineData") or parca.get("inline_data") or {}
                    b64 = inline.get("data")
                    if not b64:
                        continue
                    ham = base64.b64decode(b64)
                    if len(ham) < en_az:
                        continue
                    yol.write_bytes(ham)
                    print(f"[Gemini] ✅ görsel üretildi: {model} · {len(ham)} bayt", flush=True)
                    _SON["hata"] = None
                    return str(yol)
            except Exception as e:
                print(f"[Gemini] görsel ayrıştırma hatası: {str(e)[:100]}", flush=True)
            continue
        metin = str(veri)
        if kod == 429:
            import re as _re

            m = _re.search(r"retry in (?:([0-9]+)h)?([0-9]+)m", metin)
            if m:
                _SON["yeniden_dene_sn"] = int(m.group(1) or 0) * 3600 + int(m.group(2)) * 60
        if kod == 429 and "limit: 0" in metin:
            _SON["kota_yok"] = True
            _SON["hata"] = "kota_yok (limit: 0 — ücretsiz katmanda görsel yok)"
            sifir = kota_sifirlanma()
            print(
                f"[Gemini] ⛔ {model}: görsel kotası ÜCRETSİZ KATMANDA 0 (limit: 0). "
                + (f"Sıfırlanma: {sifir}." if sifir else "")
                + " Kalıcı çözüm: faturalandırma ya da görsel yetkili anahtar.",
                flush=True,
            )
            return None  # diğer modeller de aynı sonucu verir
        print(f"[Gemini] {model} → {kod} {metin[:110]}", flush=True)
    return None


def kota_sifirlanma() -> str | None:
    """Kota 429'unda API'nin verdiği "retry in 2h15m" → sıfırlanma anı (UTC).

    DOKÜMAN (ai.google.dev/gemini-api/docs/rate-limits): "Requests per day (RPD)
    quotas reset at midnight Pacific time." Ölçümle doğrulandı:
    2026-11-13 05:45 UTC'de "retry in 2h15m03s" → 08:00 UTC = Pasifik gece yarısı.
    """
    sn = _SON.get("yeniden_dene_sn")
    if not sn:
        return None
    from datetime import datetime, timedelta, timezone

    an = datetime.now(timezone.utc) + timedelta(seconds=sn)
    return an.strftime("%Y-%m-%d %H:%M UTC")


def goruntu_uret_ve_sakla(prompt: str, dosya_adi: str = "gemini_kapak.png") -> str | None:
    """Kolaylık: `BOBITV_GECICI_KOK`/kanit altına yazar."""
    kok = os.environ.get("BOBITV_GECICI_KOK", "kanit")
    return gorsel_uret(prompt, str(Path(kok) / dosya_adi))
