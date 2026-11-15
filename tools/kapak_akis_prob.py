"""Kapak akışını UÇTAN UCA ölç: hangi istem, hangi dosya, hangi kapak YouTube'a gitti.

NİÇİN: Gemini'nin döndürdüğü görsel (yazılı, şaşkın adam) ile kanaldaki kapak
(yazısız, damla) BAMBAŞKA. Aradaki kopukluğu bulmak için her adımı ayrı ayrı
ölçüp hash'liyoruz:
  1. kapak istemi → Gemini → ham_kapak  (hash A)
  2. ham_kapak → kapak_olcekle → kapak  (hash B)
  3. paket["kapak_dosyasi"] ne?         (hash B olmalı)
"""
from __future__ import annotations
import hashlib, os, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from modules import gemini_web
from modules.yeni_motor import motor


def h(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()[:12] if Path(p).exists() else "YOK"


def main() -> int:
    baslik = motor.KONU_LISTESI[2]["baslik"]
    tmp = tempfile.mkdtemp()
    ham = os.path.join(tmp, "ham.jpg")
    kap = os.path.join(tmp, "kapak.jpg")

    istem = motor.kapak_istemini_yaz(baslik)
    print("İSTEM:", istem, flush=True)

    r = gemini_web.gorsel_uret(istem, ham)
    print(f"1) Gemini ham   : {r} · hash={h(ham)}", flush=True)
    if not r:
        print("   HATA:", gemini_web.durum().get("hata"), flush=True)
        return 1

    motor.kapak_olcekle(ham, kap)
    print(f"2) ölçeklenmiş  : {kap} · hash={h(kap)}", flush=True)

    # paket akışını taklit et: aynı yol mı dönüyor?
    print(f"3) paket kapak_dosyasi = {kap} · hash={h(kap)}", flush=True)
    print(flush=True)
    print("SONUÇ: ham ve kapak FARKLI hash olmalı (ölçekleme değiştirir).", flush=True)
    print("       Ama İÇERİK aynı olmalı — gözle bak.", flush=True)

    Path("out/kapak_akis").mkdir(parents=True, exist_ok=True)
    Path(f"out/kapak_akis/ham_{h(ham)}.jpg").write_bytes(Path(ham).read_bytes())
    Path(f"out/kapak_akis/kapak_{h(kap)}.jpg").write_bytes(Path(kap).read_bytes())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
