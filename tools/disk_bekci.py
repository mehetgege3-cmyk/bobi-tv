"""Workspace bütçe bekçisi — 128 MB / 10.000 dosya limitini AŞMADAN uyarır.

NEDEN (2026-11-13, gerçek olay): Kanıt için GitHub artifact'larından videolar
indirildi (27 MB + 22 MB + 20 MB + 17 MB = 86 MB). Workspace 179 MB / 2.786
dosyaya çıktı, "Workspace over budget" uyarısı geldi ve **33 dosya kaydedilmedi**.
Kullanıcı: "Önce şunu düzelt, bir daha bu hatayı yapma."

KURAL: Kanıt olarak **video/mp4 workspace'e İNDİRİLMEZ**.
  • Video zaten YouTube'da yayında → link yeterli.
  • Gerekirse `/tmp`'ye indir, incele, sil (kalıcı değil).
  • Workspace'te yalnız KÜÇÜK kanıtlar kalır: kapak JPG/PNG, log, JSON.

KULLANIM
    python3 tools/disk_bekci.py            # rapor + limit kontrolü
    python3 tools/disk_bekci.py --esik 100 # özel eşik (MB)

Çıkış kodu: 0 = bütçe içinde, 1 = limit aşıldı.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

KOK = Path(os.environ.get("BOBITV_KOK", "/home/user"))
# Platform sınırları (uyarı metnindeki değerler)
VARSAYILAN_MB = 128
VARSAYILAN_DOSYA = 10_000
# Kendi güvenlik payımız: limitin %75'ini geçince UYARI
UYARI_ORANI = 0.75
# Workspace'e asla indirilmemesi gereken uzantılar
YASAK = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".zip", ".tar", ".gz"}
YASAK_MB = 3  # bu boyutun üstündeki yasak uzantı = ihlal


def tara(kok: Path) -> tuple[int, int, list[tuple[int, Path]]]:
    """(toplam bayt, dosya sayısı, büyük dosyalar) döner."""
    toplam = 0
    sayi = 0
    buyuk: list[tuple[int, Path]] = []
    for p in kok.rglob("*"):
        if not p.is_file() or "/.git/" in str(p):
            continue
        try:
            b = p.stat().st_size
        except OSError:
            continue
        toplam += b
        sayi += 1
        if b > 1024 * 1024:
            buyuk.append((b, p))
    buyuk.sort(reverse=True)
    return toplam, sayi, buyuk


def insan(bayt: int) -> str:
    for birim in ("B", "KB", "MB", "GB"):
        if bayt < 1024:
            return f"{bayt:.0f} {birim}"
        bayt /= 1024
    return f"{bayt:.1f} TB"


def main() -> int:
    ap = argparse.ArgumentParser(description="Workspace bütçe bekçisi")
    ap.add_argument("--esik", type=int, default=VARSAYILAN_MB, help="MB eşiği")
    ap.add_argument("--dosya-esik", type=int, default=VARSAYILAN_DOSYA)
    ap.add_argument("--kok", default=str(KOK))
    a = ap.parse_args()

    toplam, sayi, buyuk = tara(Path(a.kok))
    mb = toplam / (1024 * 1024)
    sinir_mb = a.esik * UYARI_ORANI

    print(f"Workspace: {insan(toplam)} · {sayi} dosya")
    print(f"Bütçe    : {a.esik} MB / {a.dosya_esik} dosya "
          f"(uyarı eşiği %{UYARI_ORANI * 100:.0f} = {sinir_mb:.0f} MB)")

    ihlal = False

    # 1) Bütçe
    if mb > a.esik:
        print(f"❌ BÜTÇE AŞILDI: {mb:.1f} MB > {a.esik} MB")
        ihlal = True
    elif mb > sinir_mb:
        print(f"⚠️  Bütçeye yaklaşıldı: {mb:.1f} MB > {sinir_mb:.0f} MB")
    else:
        print(f"✅ Bütçe içinde ({mb:.1f} MB)")

    if sayi > a.dosya_esik:
        print(f"❌ DOSYA SAYISI AŞILDI: {sayi} > {a.dosya_esik}")
        ihlal = True

    # 2) Yasak uzantılar (video/arşiv workspace'e inmemeli)
    for b, p in buyuk:
        if p.suffix.lower() in YASAK and b > YASAK_MB * 1024 * 1024:
            print(f"❌ YASAK DOSYA: {insan(b)} {p}")
            print("   → video/arşiv kanıtı workspace'e İNDİRİLMEZ; YouTube linki"
                  " veya /tmp kullan.")
            ihlal = True

    # 3) En büyük 5
    if buyuk:
        print("\nEn büyük dosyalar:")
        for b, p in buyuk[:5]:
            print(f"  {insan(b):>9}  {p.relative_to(Path(a.kok))}")

    return 1 if ihlal else 0


if __name__ == "__main__":
    raise SystemExit(main())
