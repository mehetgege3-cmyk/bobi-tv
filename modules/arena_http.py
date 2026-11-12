"""Arena ile TARAYICISIZ veri yolu (cevap + görsel indirme).

NEDEN VAR (2026-11-12, Drive'daki `arena.ai_*.md` HAR dosyasıyla kanıtlandı):

  Arena'nın web uygulaması mesajı `POST /nextjs-api/stream/create-chat` ile
  gönderiyor. Bu isteğin gövdesinde **`recaptchaV3Token` ZORUNLU** — jeton
  tarayıcıda üretiliyor, dışarıdan üretilemiyor (jetonsuz deneme: HTTP 400
  `ZodError ... path: ["recaptchaV3Token"]`).

  AMA cevap ve görsel TARAYICI GEREKTİRMİYOR:
    • `GET /api/chat/{chat_id}/events`        → SSE; `text-delta` parçaları,
                                                 `tool-output-available` içinde
                                                 görselin `hash` değeri
    • `GET /api/chat/workspace/cas/user/{h}`  → `image/png` (gerçek görsel)
    • `GET /api/history/unified?limit=N`      → son sohbetler (chat_id bulmak için)

  Canlı kanıt: hash `ncoCtMLfdc358Ey9wglM-B3UUTRNnmagcXr4BxtSZx8` → HTTP 200,
  image/png, 3 165 495 bayt, 1408×768.

BÖYLECE: tarayıcı yalnızca "gönder" düğmesi için açılır; cevabı DOM'dan
okumaya / ekran görüntüsü almaya GEREK YOKTUR (eski kırılgan yöntem).
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request

ARENA = "https://arena.ai"
UA = (
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/157.0.0.0 Mobile Safari/537.36"
)

_OTURUM: dict = {}

# KULLANICI BULGUSU (2026-11-13): Arena görsel ürettikten sonra
# "Which image do you prefer?" diye SORU soruyor ve cevap bekliyor. Biz
# cevaplamadığımız için akış bitmiyor, görsel hiç teslim edilmiyordu.
# Prompt sonuna bu cümle eklenince Arena sormadan doğrudan yapıyor.
SORU_SORMA = "Soru sorma, yap."


def prompt_hazirla(prompt: str) -> str:
    """Arena'ya giden HER istemin sonuna 'Soru sorma, yap.' ekler."""
    t = (prompt or "").rstrip()
    if SORU_SORMA.lower() in t.lower():
        return t
    return f"{t}\n\n{SORU_SORMA}"


def oturum_doldu_isaretle() -> None:
    """Çerez ölü çıktığında bu koşuda tekrar denemeyi engeller."""
    _OTURUM["doldu"] = True


def oturum_doldu_mu() -> bool:
    return bool(_OTURUM.get("doldu"))


def _cerez_basligi(cookies_raw: str | None = None) -> str:
    """`ARENA_COOKIES_JSON` (ham base64 ya da Cookie-Editor JSON) → Cookie başlığı."""
    raw = (cookies_raw or os.environ.get("ARENA_COOKIES_JSON", "") or "").strip()
    if not raw:
        return ""
    if raw.startswith("base64-"):
        raw = raw[len("base64-"):]
    if raw.startswith("["):
        try:
            parcalar = json.loads(raw)
            return "; ".join(
                f"{c.get('name')}={c.get('value')}"
                for c in parcalar
                if isinstance(c, dict) and c.get("name")
            )
        except Exception:
            return ""
    if raw.startswith("{"):
        try:
            veri = json.loads(raw)
            if isinstance(veri, dict) and "name" not in veri:
                return "; ".join(f"{k}={v}" for k, v in veri.items())
        except Exception:
            return ""
    # Ham değer: yalnız `arena-auth-prod-v1.0` çerezi verilmiş olabilir
    return f"arena-auth-prod-v1.0={raw}"


def _istek(yol: str, *, cerez: str, kabul: str = "application/json", sure: int = 45):
    req = urllib.request.Request(
        ARENA + yol,
        headers={
            "cookie": cerez,
            "accept": kabul,
            "user-agent": UA,
            "referer": ARENA + "/agent",
            "accept-language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        },
    )
    return urllib.request.urlopen(req, timeout=sure)


# --------------------------------------------------------------------------- #
# Sohbet listesi / kimliği
# --------------------------------------------------------------------------- #
def son_sohbetler(cerez: str, limit: int = 6) -> list[dict]:
    """Son sohbetler (en yeni önce). Oturum ölüyse boş liste."""
    try:
        with _istek(f"/api/history/unified?limit={int(limit)}", cerez=cerez) as r:
            veri = json.loads(r.read().decode("utf-8", "replace"))
        return veri.get("entries", []) or []
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            oturum_doldu_isaretle()
        print(f"[Arena HTTP] sohbet listesi alınamadı: HTTP {e.code}", flush=True)
        return []
    except Exception as e:
        print(f"[Arena HTTP] sohbet listesi hatası: {str(e)[:120]}", flush=True)
        return []


def sohbet_id_bekle(cerez: str, bilinen: set[str], *, azami_sn: int = 90) -> str | None:
    """Gönderimden sonra YENİ oluşan sohbetin kimliğini bulur."""
    bitis = time.time() + azami_sn
    while time.time() < bitis:
        if oturum_doldu_mu():          # 401 → boşuna 15 tur denemeyiz
            print("[Arena HTTP] oturum doldu — kimlik arama bırakıldı", flush=True)
            return None
        for kayit in son_sohbetler(cerez, limit=8):
            kid = kayit.get("id")
            if kid and kid not in bilinen:
                return kid
        time.sleep(3)
    return None


# --------------------------------------------------------------------------- #
# SSE akışı: cevap metni + görsel
# --------------------------------------------------------------------------- #
def _sse_kayitlari(metin: str):
    """SSE gövdesini kayıt listesine çevirir (`event:`/`data:` satırları)."""
    for satir in metin.splitlines():
        if not satir.startswith("data: "):
            continue
        try:
            paket = json.loads(satir[6:])
        except Exception:
            continue
        for kayit in paket.get("records", []) or []:
            try:
                yield json.loads(kayit.get("body", "{}"))
            except Exception:
                continue


def akisi_oku(chat_id: str, cerez: str) -> dict:
    """`/events` akışını okur; cevap metni + görsel yolu/hash'i döndürür.

    Dönen sözlük anahtarları:
      metin     : modelin düz cevabı (text-delta parçalarının birleşimi)
      gorsel_yolu: Arena'nın yazdığı dosya yolu (örn. /home/user/kapak.png)
      hash      : CAS kimliği → /api/chat/workspace/cas/user/{hash} ile inilir
      durumlar  : görülen olay tipleri (teşhis için)
    """
    sonuc = {"metin": "", "gorsel_yolu": None, "hash": None, "durumlar": {}}
    parcalar: list[str] = []
    try:
        with _istek(f"/api/chat/{chat_id}/events", cerez=cerez,
                    kabul="text/event-stream", sure=180) as r:
            govde = r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            oturum_doldu_isaretle()
        print(f"[Arena HTTP] events hatası: HTTP {e.code}", flush=True)
        return sonuc
    except Exception as e:
        print(f"[Arena HTTP] events okunamadı: {str(e)[:120]}", flush=True)
        return sonuc

    for kayit in _sse_kayitlari(govde):
        veri = kayit.get("data") or {}
        tip = veri.get("type") or ""
        if tip:
            sonuc["durumlar"][tip] = sonuc["durumlar"].get(tip, 0) + 1
        if tip == "text-delta":
            parcalar.append(veri.get("delta") or "")
        elif tip == "tool-output-available":
            cikti = veri.get("output") or {}
            if cikti.get("hash"):
                sonuc["hash"] = cikti["hash"]
            yol = cikti.get("file_path") or cikti.get("path")
            if yol:
                sonuc["gorsel_yolu"] = yol
        elif tip == "tool-input-available" and veri.get("toolName") == "generate_image":
            giris = veri.get("input") or {}
            if giris.get("file_path"):
                sonuc["gorsel_yolu"] = giris["file_path"]

    sonuc["metin"] = "".join(parcalar).strip()
    # Metinde geçen görsel yolu (output'ta gelmediyse yedek)
    if not sonuc["gorsel_yolu"] and sonuc["metin"]:
        m = re.search(r"(/[^\s`]+\.(?:png|jpe?g|webp))", sonuc["metin"], re.I)
        if m:
            sonuc["gorsel_yolu"] = m.group(1)
    return sonuc


def oturum_canli_mi(cerez: str) -> bool:
    """`/api/me/pulse` ile oturumun GERÇEKTEN canlı olduğunu ölçer.

    KOŞU 43325201001: pahalı kapak aşamasına girildi, ilk turdan sonra çerez
    öldü (401) ve 8 tur boşa harcandı. Bu kontrol işe girmeden önce yapılır.
    """
    if not cerez:
        return False
    try:
        with _istek("/api/me/pulse", cerez=cerez, sure=25) as r:
            veri = json.loads(r.read().decode("utf-8", "replace"))
        if isinstance(veri, dict) and "pulse" in veri:
            return True
        return False
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            oturum_doldu_isaretle()
            print(f"[Arena HTTP] oturum ÖLÜ (pulse HTTP {e.code})", flush=True)
        else:
            print(f"[Arena HTTP] pulse HTTP {e.code}", flush=True)
        return False
    except Exception as e:
        print(f"[Arena HTTP] pulse hatası: {str(e)[:90]}", flush=True)
        return False


def gorsel_indir(hash_: str, hedef_yol: str, cerez: str) -> str | None:
    """Üretilen görseli TARAYICISIZ indirir. Başarılıysa dosya yolunu döndürür."""
    if not hash_:
        return None
    import pathlib

    yol = pathlib.Path(hedef_yol)
    yol.parent.mkdir(parents=True, exist_ok=True)
    try:
        with _istek(
            f"/api/chat/workspace/cas/user/{hash_}?w=1024",
            cerez=cerez,
            kabul="image/avif,image/webp,image/png,image/*,*/*",
            sure=120,
        ) as r:
            boyut = 0
            with open(yol, "wb") as f:
                while True:
                    parca = r.read(65536)
                    if not parca:
                        break
                    f.write(parca)
                    boyut += len(parca)
        if boyut < 5000:  # boş/kırık yanıt koruması
            print(f"[Arena HTTP] görsel çok küçük ({boyut} bayt) — geçersiz", flush=True)
            yol.unlink(missing_ok=True)
            return None
        print(f"[Arena HTTP] ✅ görsel indi: {yol} ({boyut} bayt)", flush=True)
        return str(yol)
    except Exception as e:
        print(f"[Arena HTTP] görsel indirilemedi: {str(e)[:120]}", flush=True)
        return None


def gorsel_yolu_ile_indir(hash_veya_yol: str, hedef_yol: str, cerez: str) -> str | None:
    """Verilen değer CAS hash'i de olabilir dosya yolu da; ikisini de dener."""
    if not hash_veya_yol:
        return None
    aday = hash_veya_yol.rsplit("/", 1)[-1]
    return gorsel_indir(aday, hedef_yol, cerez)


def hash_bekle(
    chat_id: str,
    cerez: str,
    *,
    azami_sn: int = 300,
    aralik: int = 15,
) -> dict:
    """Görsel hash'i görünene kadar akışı TEKRAR okur.

    NEDEN (canlı koşu 43311322015): Arena görsel üretimi ilk denemede
    başarısız olursa kendi cevabında "İlk deneme tüm modellerde başarısız
    oldu... yeniden deneyeceğim" diyor ve DAHA SONRA yeni bir deneme
    başlatıyor. Tek seferlik okuma bunu kaçırıyordu (hash yok → yanlış
    "görsel üretilmedi" sonucu).
    """
    bitis = time.time() + azami_sn
    son: dict = {"metin": "", "gorsel_yolu": None, "hash": None, "durumlar": {}}
    tur = 0
    while time.time() < bitis:
        tur += 1
        # KOŞU 43325201001: çerez iş ortasında öldü (HTTP 401) ve 8 tur boşa
        # denendi. Oturum dolduysa hemen çık.
        if oturum_doldu_mu():
            print("[Arena HTTP] oturum doldu (401) — hash bekleme bırakıldı", flush=True)
            return son
        akis = akisi_oku(chat_id, cerez)
        son = akis
        if akis["hash"]:
            print(f"[Arena HTTP] ✅ görsel hash'i bulundu (tur {tur})", flush=True)
            return akis
        print(
            f"[Arena HTTP] tur {tur}: hash yok · cevap: "
            f"{(akis['metin'] or '(boş)')[:90]}",
            flush=True,
        )
        if akis.get("durumlar", {}).get("finish") and not akis["hash"]:
            # akış bitti, görsel yok → yine de bir tur daha bekle (yeniden deneme)
            pass
        time.sleep(aralik)
    print("[Arena HTTP] ⛔ süre doldu, görsel hash'i gelmedi", flush=True)
    return son
