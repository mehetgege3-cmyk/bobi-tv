"""BOBİ TV — Ayar Deposu (TODO 2, 6, 8).

Tek doğruluk kaynağı `bobi_tv/state/ayarlar.json` üzerinde:
- ATOMİK yazma (tmp + os.replace — yarıda kesilen yazma eski dosyayı bozmaz)
- Toleranslı yükleme: bozuk JSON → `ayarlar.json.bozuk` yedeği + varsayılanlara
  dönüş (arsive_ekle'nin `except: arsiv=[]` EZME hatası tekrarlanmaz);
  bilinmeyen anahtar yok sayılır; aralık dışı değer varsayılana döner.
  ASLA exception fırlatıp botu düşürmez.
- Şema sürümü (`sur`): farklıysa uyar + varsayılanlar.
- Öncelik: state > env > katalog varsayılanı.
- Değişiklik geçmişi (TODO 6): append-only JSONL, 200 satır rotasyonu
  (`ayar_gecmisi.1.jsonl`). sadece_goruntule ayarlar geçmişe YAZILMAZ.
- Bekleyen kuyruk (TODO 8): push başarısızsa `ayarlar_bekleyen.json`'a yazılır,
  sonraki koşuda tekrar denenir. Push başarısızlığı SESSİZCE YUTULMAZ.
- `commit_ve_yukle`: ayar dosyaları OFFSET İLE KARIŞMADAN AYRI bir commit'te
  push edilir (TODO 8). Secret değeri argv'ye girmez; kimlik git kimliğinden gelir.
"""

from __future__ import annotations

import json
import os
import subprocess
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from modules.ayar_katalogu import (
    ayar_getir,
    degistirilebilir_mi,
    tumu,
)

SEMA_SURUMU: int = 1
GECMIS_SINIRI: int = 200

AYARLAR_YOLU = Path("bobi_tv/state/ayarlar.json")
GECMIS_YOLU = Path("bobi_tv/state/ayar_gecmisi.jsonl")
BEKLEYEN_YOLU = Path("bobi_tv/state/ayarlar_bekleyen.json")

GIT_KIMLIK_AD: str = "BOBİ TV Bot"
GIT_KIMLIK_EPOSTA: str = "bobi-tv-bot@users.noreply.github.com"


def _simd() -> str:
    return datetime.now(UTC).isoformat()


def _atomik_yaz(yol: Path, icerik: str) -> None:
    """Yaz → os.replace: yarıda kesilme eski dosyayı bozmaz."""
    yol.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(yol) + ".tmp")
    tmp.write_text(icerik, encoding="utf-8")
    os.replace(tmp, yol)


def _yedek_yolu(yol: Path) -> Path:
    return Path(str(yol) + ".bozuk")


def varsayilanlar() -> dict[str, Any]:
    """Değiştirilebilir ayarların katalog varsayılanları."""
    return {a["anahtar"]: a["varsayilan"] for a in tumu() if degistirilebilir_mi(a)}


def _dogrula(anahtar: str, deger: Any) -> tuple[Any, str | None]:
    """Katalog kurallarına göre doğrular. Döner: (temiz_deger | None, uyarı | None).

    Temiz değer None ise ayar YAZILMAZ (kaydedilirken düşürülür). Uyarı doluysa
    temiz değer varsayılana dönmüş demektir (aralık dışı → varsayılan).
    """
    a = ayar_getir(anahtar)
    if a is None:
        return None, f"bilinmeyen anahtar yok sayıldı: {anahtar!r}"
    if not degistirilebilir_mi(a):
        return None, f"yalnızca görüntülenen ayar yazılamaz: {anahtar!r}"
    tip = a["tip"]
    if tip == "anahtar":
        metin = str(deger).strip().lower()
        return ("1" if metin in ("1", "true", "yes", "evet") else "0"), None
    if tip == "secim":
        secenekler = [str(s) for s in (a["secenekler"] or [])]
        if str(deger) in secenekler:
            return str(deger), None
        return (
            None,
            f"aralık dışı seçim: {anahtar}={deger!r} — reddedildi, varsayılan "
            f"{a['varsayilan']!r} etkin kalır (katalogda böyle bir seçenek yok)",
        )
    # sayi
    try:
        n = int(deger)
    except (TypeError, ValueError):
        return None, f"sayı beklenirdi: {anahtar}={deger!r} — reddedildi, varsayılan etkin kalır"
    mn, mx = a["min"], a["max"]
    if mn is not None and n < int(mn):
        return None, f"aralık dışı: {anahtar}={n} < {mn} — reddedildi, varsayılan etkin kalır"
    if mx is not None and n > int(mx):
        return None, f"aralık dışı: {anahtar}={n} > {mx} — reddedildi, varsayılan etkin kalır"
    return n, None


def yukle(
    state_yolu: Path = AYARLAR_YOLU, env: dict[str, str] | None = None
) -> tuple[dict[str, Any], list[str]]:
    """Etkili değerleri döndürür: state > env > katalog varsayılanı.

    Döner: (degerler, uyarilar). Hiçbir koşulda exception fırlatmaz;
    bozuk dosya `.bozuk` olarak saklanır ve varsayılanlara dönülür.
    """
    uyarilar: list[str] = []
    degerler: dict[str, Any] = varsayilanlar()
    ham: dict[str, Any] = {}
    if state_yolu.exists():
        try:
            veri = json.loads(state_yolu.read_text(encoding="utf-8"))
            if not isinstance(veri, dict):
                raise ValueError("kök bir nesne (dict) değil")
            sur = veri.get("sur")
            if sur != SEMA_SURUMU:
                uyarilar.append(f"şema sürümü {sur!r} ≠ {SEMA_SURUMU} — varsayılanlar kullanılıyor")
            else:
                aday = veri.get("ayarlar")
                if isinstance(aday, dict):
                    ham = aday
        except Exception as e:
            yedek = _yedek_yolu(state_yolu)
            try:
                yedek.write_text(state_yolu.read_text(encoding="utf-8"), encoding="utf-8")
                uyarilar.append(
                    f"bozuk ayar dosyası {yedek.name} olarak saklandı — varsayılanlara dönüldü ({e})"
                )
            except Exception:
                uyarilar.append(f"bozuk ayar dosyası okunamadı: {e}")
            ham = {}
    for k, v in ham.items():
        temiz, hata = _dogrula(str(k), v)
        if temiz is not None:
            degerler[str(k)] = temiz
        if hata:
            uyarilar.append(hata)

    # env katmanı: yalnızca state'te KARŞILIK OLMAYAN anahtarlar için
    state_anahtarlari = set(ham.keys())
    for a in tumu():
        if not degistirilebilir_mi(a):
            continue
        k = str(a["anahtar"])
        if k in state_anahtarlari:
            continue
        ham_env = (env or {}).get(str(a["env_adi"]))
        if ham_env is None:
            continue
        temiz, hata = _dogrula(k, ham_env)
        if temiz is not None:
            degerler[k] = temiz
        if hata:
            uyarilar.append(hata)
    return degerler, uyarilar


def state_ham_ayarlari(state_yolu: Path = AYARLAR_YOLU) -> dict[str, Any]:
    """State dosyasındaki ham `ayarlar` sözlüğü (kaynak etiketi için)."""
    try:
        veri = json.loads(state_yolu.read_text(encoding="utf-8"))
        aday = veri.get("ayarlar")
        if isinstance(aday, dict):
            return aday
    except Exception:
        pass
    return {}


def kaydet(
    degisiklikler: dict[str, Any], state_yolu: Path = AYARLAR_YOLU
) -> tuple[dict[str, Any], list[str]]:
    """Değişiklikleri doğrular ve ATOMİK yazar. Döner: (uygulanan, uyarilar).

    Bozuk mevcut dosya önce `yukle` içinde .bozuk'a arşivlenir, ardından bu
    çağrı taze bir geçerli dosya yazar (kurtarma yolu)."""
    uyarilar: list[str] = []
    mevcut, okuma_uyarlari = yukle(state_yolu)
    uyarilar.extend(okuma_uyarlari)
    yeni = dict(mevcut)
    uygulanan: dict[str, Any] = {}
    for k, v in degisiklikler.items():
        temiz, hata = _dogrula(str(k), v)
        if temiz is None:
            if hata:
                uyarilar.append(hata)
            continue
        yeni[str(k)] = temiz
        uygulanan[str(k)] = temiz
        if hata:
            uyarilar.append(hata)
    belge = {"sur": SEMA_SURUMU, "guncelleme": _simd(), "ayarlar": yeni}
    _atomik_yaz(state_yolu, json.dumps(belge, ensure_ascii=False, indent=2) + "\n")
    return uygulanan, uyarilar


# ---------------------------------------------------------------------------
# TODO 6 — değişiklik geçmişi (append-only, 200 satır rotasyonu)
# ---------------------------------------------------------------------------


def gecmis_yedek_yolu(gecmis_yolu: Path = GECMIS_YOLU) -> Path:
    return gecmis_yolu.with_name(gecmis_yolu.stem + ".1" + gecmis_yolu.suffix)


def gecmise_ekle(
    kullanici_id: int | None,
    anahtar: str,
    eski: Any,
    yeni: Any,
    kaynak: str = "telegram",
    gecmis_yolu: Path = GECMIS_YOLU,
) -> None:
    """Değişiklik kaydı yazar. sadece_goruntule ayarlar geçmişe YAZILMAZ."""
    a = ayar_getir(anahtar)
    if a is None or not degistirilebilir_mi(a):
        return
    satir = json.dumps(
        {
            "zaman": _simd(),
            "kullanici_id": kullanici_id,
            "anahtar": anahtar,
            "eski": eski,
            "yeni": yeni,
            "kaynak": kaynak,
        },
        ensure_ascii=False,
    )
    gecmis_yolu.parent.mkdir(parents=True, exist_ok=True)
    with open(gecmis_yolu, "a", encoding="utf-8") as f:
        f.write(satir + "\n")
    _gecmis_dondur(gecmis_yolu)


def _gecmis_dondur(gecmis_yolu: Path) -> None:
    """Sınır aşımında: en eski taşma satırları `.1.jsonl`e taşınır, mevcut
    dosya son GECMIS_SINIRI satırda kalır."""
    try:
        satirlar = gecmis_yolu.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return
    if len(satirlar) <= GECMIS_SINIRI:
        return
    tasinan = satirlar[:-GECMIS_SINIRI]
    kalan = satirlar[-GECMIS_SINIRI:]
    yedek = gecmis_yedek_yolu(gecmis_yolu)
    yedek.parent.mkdir(parents=True, exist_ok=True)
    yedek.write_text("\n".join(tasinan) + "\n", encoding="utf-8")
    _atomik_yaz(gecmis_yolu, "\n".join(kalan) + "\n")


def gecmisi_oku(son_n: int = 10, gecmis_yolu: Path = GECMIS_YOLU) -> list[dict[str, Any]]:
    """Son N değişiklik (yedek dosyadaki eskiler dahil, kronolojik)."""
    kayitlar: list[dict[str, Any]] = []
    yedek = gecmis_yedek_yolu(gecmis_yolu)
    for yol in (yedek, gecmis_yolu):
        try:
            for satir in yol.read_text(encoding="utf-8").splitlines():
                if not satir.strip():
                    continue
                try:
                    veri = json.loads(satir)
                except Exception:
                    continue
                if isinstance(veri, dict):
                    kayitlar.append(veri)
        except FileNotFoundError:
            continue
    return kayitlar[-son_n:]


# ---------------------------------------------------------------------------
# TODO 8 — bekleyen kuyruk (push başarısızlığı yutulmaz)
# ---------------------------------------------------------------------------


def bekleyene_yaz(
    degisiklikler: dict[str, Any],
    sebep: str,
    kullanici_id: int | None = None,
    bekleyen_yolu: Path = BEKLEYEN_YOLU,
) -> None:
    """Push edilemeyen değişikliği atomik olarak kuyruğa alır."""
    belge = {
        "degisiklikler": degisiklikler,
        "sebep": sebep,
        "kullanici_id": kullanici_id,
        "zaman": _simd(),
    }
    _atomik_yaz(bekleyen_yolu, json.dumps(belge, ensure_ascii=False, indent=2) + "\n")


def bekleyenleri_al(bekleyen_yolu: Path = BEKLEYEN_YOLU) -> dict[str, Any] | None:
    """Bekleyen kaydı döndürür (bozuksa None — botu düşürmez)."""
    try:
        veri = json.loads(bekleyen_yolu.read_text(encoding="utf-8"))
        if isinstance(veri, dict) and isinstance(veri.get("degisiklikler"), dict):
            return veri
    except Exception:
        pass
    return None


def bekleyenleri_temizle(bekleyen_yolu: Path = BEKLEYEN_YOLU) -> None:
    with suppress(Exception):
        bekleyen_yolu.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# TODO 8 — ayrı commit + push (secret argv'ye girmez; hata yutulmaz)
# ---------------------------------------------------------------------------


def commit_ve_yukle(dosyalar: list[str], mesaj: str, repo_kok: Path | None = None) -> tuple[bool, str]:
    """Ayar dosyalarını AYRI bir commit'te push eder (offset/menü ile karışmaz).

    Döner: (basarili, durum). Push/commit başarısızlığı SESSİZCE YUTULMAZ —
    sebep metni döndürülür (bot bunu panele yazıp bekleyen kuyruğa alır).
    """
    kok = repo_kok or Path(".")
    if not dosyalar:
        return False, "commit listesi boş"

    def git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", "-C", str(kok), *args], capture_output=True, text=True, check=False)

    add = git("add", "-f", *dosyalar)
    if add.returncode != 0:
        return False, f"git add başarısız: {add.stderr.strip()[:160]}"
    if git("diff", "--staged", "--quiet").returncode == 0:
        return True, "değişiklik yok"
    commit = git(
        "-c",
        f"user.name={GIT_KIMLIK_AD}",
        "-c",
        f"user.email={GIT_KIMLIK_EPOSTA}",
        "commit",
        "-m",
        mesaj,
    )
    if commit.returncode != 0:
        return False, f"git commit başarısız: {commit.stderr.strip()[:160]}"
    push = git("push", "origin", "HEAD:main")
    if push.returncode != 0:
        return False, f"git push başarısız: {(push.stderr or push.stdout).strip()[:200]}"
    return True, ""


# ---------------------------------------------------------------------------
# TODO 9 — state → $GITHUB_ENV köprüsü (yalnızca secret olmayanlar)
# ---------------------------------------------------------------------------


def env_satirlari(degerler: dict[str, Any] | None = None, env: dict[str, str] | None = None) -> list[str]:
    """`KEY=value` satırları. SADECE secret olmayan, değiştirilebilir ve
    etkili ayarlar köprüden geçer; secret'lar bu yoldan env'e ASLA yazılmaz."""
    if degerler is None:
        degerler, _ = yukle(env=env)
    satirlar: list[str] = []
    for a in tumu():
        if a.get("secret"):
            continue
        if not degistirilebilir_mi(a):
            continue
        if a.get("etkili") is not True:
            continue
        deger = degerler.get(str(a["anahtar"]), a["varsayilan"])
        if deger is None:
            continue
        satirlar.append(f"{a['env_adi']}={deger}")
    return satirlar


def github_env_yaz(github_env_yolu: str | Path, satirlar: list[str]) -> None:
    """Satırları $GITHUB_ENV dosyasına ekler (sonraki adımlarda etkin olur)."""
    yolu = Path(github_env_yolu)
    yolu.parent.mkdir(parents=True, exist_ok=True)
    with open(yolu, "a", encoding="utf-8") as f:
        for satir in satirlar:
            f.write(satir + "\n")


def force_sifirla(state_yolu: Path = AYARLAR_YOLU) -> bool:
    """Tek kullanımlık force bayrağını tüketir (1 → 0). YAZILDIYSA True."""
    degerler, _ = yukle(state_yolu)
    if str(degerler.get("force", "0")) != "1":
        return False
    kaydet({"force": "0"}, state_yolu)
    return True
