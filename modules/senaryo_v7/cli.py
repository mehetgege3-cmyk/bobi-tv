"""Senaryo v7 migrate/validate/generate komut satırı arayüzü."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from .dogrulama.migration import migrate
from .exceptions import SenaryoHatasi
from .loglama import kur_logger
from .service import SenaryoUretici


def _nesne_oku(path: Path) -> dict[str, object]:
    """UTF-8 JSON nesnesi okur, JSON şekli beklenmiyorsa açıklayıcı hata üretir."""
    try:
        raw: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SenaryoHatasi(f"JSON girdi okunamadı ({path}): {exc}") from exc
    if not isinstance(raw, dict):
        raise SenaryoHatasi(f"JSON kökü nesne olmalı: {path}")
    return raw


def main(argv: Sequence[str] | None = None) -> int:
    """CLI argümanlarını işler; `uret`, `dogrula` ve `migrate` alt komutları sunar."""
    parser = argparse.ArgumentParser(
        prog="senaryo-v7", description="BOBİ TV senaryo üretimi ve v6->v7 migrasyonu"
    )
    subparsers = parser.add_subparsers(dest="komut", required=True)
    generate_parser = subparsers.add_parser("uret", help="Tek senaryo paketi üret")
    generate_parser.add_argument("--video-no", type=int, default=1)
    generate_parser.add_argument("--seed", type=int, default=None)
    validate_parser = subparsers.add_parser("dogrula", help="Senaryo JSON'unu v7'ye yükseltip doğrula")
    validate_parser.add_argument("dosya", type=Path)
    migrate_parser = subparsers.add_parser("migrate", help="v6/satirlar JSON'unu v7 şemasına taşı")
    migrate_parser.add_argument("girdi", type=Path)
    migrate_parser.add_argument("cikti", type=Path)
    args = parser.parse_args(argv)
    logger = kur_logger()
    try:
        if args.komut == "uret":
            package = SenaryoUretici(seed=args.seed).senaryo_paketi_olustur(args.video_no)
            sys.stdout.write(json.dumps(package, ensure_ascii=False, indent=2) + "\n")
            return 0
        if args.komut == "dogrula":
            scenario = SenaryoUretici().senaryo_dogrula_ve_zenginlestir(_nesne_oku(args.dosya))
            sys.stdout.write(json.dumps(scenario.to_dict(), ensure_ascii=False, indent=2) + "\n")
            return 0
        migrated = migrate(_nesne_oku(args.girdi))
        args.cikti.parent.mkdir(parents=True, exist_ok=True)
        args.cikti.write_text(json.dumps(migrated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        logger.info("JSON v7'ye migrate edildi: %s", args.cikti)
        return 0
    except (SenaryoHatasi, OSError, TypeError, ValueError) as exc:
        logger.error("CLI işlemi başarısız: %s", exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
