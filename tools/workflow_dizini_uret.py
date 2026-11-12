"""`.github/workflows/` dizinini okuyup `docs/WORKFLOW_DIZINI.md` üretir.

NEDEN: 24 workflow var; hangisi ne yapıyor, hangisi manuel tetiklenebiliyor,
hangi cron'da çalışıyor — tek bakışta görülsün. Elle yazmak kaçınılmaz olarak
eskir; bu script her seferinde gerçeği yazar.

KULLANIM:
    python3 tools/workflow_dizini_uret.py          # yazar
    python3 tools/workflow_dizini_uret.py --kontrol # fark varsa çıkış 1
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

YOL = Path(".github/workflows")
HEDEF = Path("docs/WORKFLOW_DIZINI.md")


def uret() -> str:
    satirlar = [
        "# Workflow Dizini (otomatik üretildi)",
        "",
        "**Elle düzenlemeyin.** Yenilemek için: `python3 tools/workflow_dizini_uret.py`",
        "",
        "| Dosya | Ad | Manuel | Cron |",
        "|---|---|---|---|",
    ]
    for f in sorted(YOL.glob("*.yml")):
        s = f.read_text(encoding="utf-8")
        ad = re.search(r'^name:\s*["\']?(.+?)["\']?\s*$', s, re.M)
        ad = ad.group(1) if ad else f.stem
        manuel = "✅" if "workflow_dispatch" in s else "—"
        cron = re.search(r'cron:\s*["\']([^"\']+)', s)
        satirlar.append(
            f"| `{f.name}` | {ad} | {manuel} | {cron.group(1) if cron else '—'} |"
        )
    satirlar += [
        "",
        "## Notlar",
        "",
        "- **Manuel ✅** = `workflow_dispatch` var, GitHub API ile tetiklenebilir.",
        "- Yeni workflow eklendiğinde `arena_self_repair.yml` izleme listesine de",
        "  eklenmeli; `tests/test_actions_workflows.py` bunu şart koşar.",
        "- Üretim tetikleme: `canli_test.yml` (bkz. `docs/ARENA_DERSLER.md` §6).",
        "- Arena görsel hattı: `skills/arena-http-gorsel/SKILL.md`.",
    ]
    return "\n".join(satirlar) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kontrol", action="store_true", help="fark varsa çıkış 1")
    a = ap.parse_args()
    yeni = uret()
    if a.kontrol:
        eski = HEDEF.read_text(encoding="utf-8") if HEDEF.exists() else ""
        if eski != yeni:
            print("⚠️ docs/WORKFLOW_DIZINI.md güncel değil — yenileyin")
            return 1
        print("✅ güncel")
        return 0
    HEDEF.parent.mkdir(parents=True, exist_ok=True)
    HEDEF.write_text(yeni, encoding="utf-8")
    print(f"✅ yazıldı: {HEDEF} ({len(yeni.splitlines())} satır)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
