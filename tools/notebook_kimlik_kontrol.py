"""Kimlik kontrolü — üretime başlamadan önce çerezleri doğrular.

NİÇİN: Video üretimi 10-11 dakika sürüyor. Çerez ölüyse o süreyi boşa
harcamamak için önce hızlı bir kimlik testi yapılır (defter listesi).

ÇIKIŞ: 0 = hazır, 1 = çerez sorunlu.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.notebook_video import _depo_hazirla  # noqa: E402


async def _test() -> int:
    from notebooklm import NotebookLMClient

    async with NotebookLMClient.from_storage() as c:
        nbs = await c.notebooks.list()
        print(f"✅ kimlik geçerli — {len(nbs)} defter görünüyor")
        return 0


def main() -> int:
    depo = _depo_hazirla()
    print(f"çerez: {len(depo['cookies'])}")
    os.environ["NOTEBOOKLM_AUTH_JSON"] = json.dumps(depo)
    os.environ.setdefault("NOTEBOOKLM_QUIET_DEPRECATIONS", "1")
    try:
        return asyncio.run(_test())
    except Exception as e:
        print(f"❌ KİMLİK HATASI: {type(e).__name__}: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
