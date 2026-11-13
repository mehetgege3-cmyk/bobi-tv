"""Arena seçici ayrışma testi.

JS tek kaynağı (skills/arena-playwright-agent/scripts/arena-dom.mjs) içindeki
listeler ile Python sabitleri (modules/arena_api.py ARENA_*) birebir eşleşmeli.
Ayrışma olursa bu test KIRILIR — iki tarafı da güncellemek zorunludur.
"""
from __future__ import annotations

import re
from pathlib import Path

from modules import arena_api

JS_PATH = Path("skills/arena-playwright-agent/scripts/arena-dom.mjs")


def _read_js() -> str:
    assert JS_PATH.exists(), f"{JS_PATH} bulunamadı"
    return JS_PATH.read_text(encoding="utf-8")


def _extract_scalar(text: str, name: str) -> str:
    m = re.search(rf"export const {name}\s*=\s*'([^']+)';", text)
    assert m, f"{name} sabiti JS'te bulunamadı"
    return m.group(1)


def _extract_array(text: str, name: str, editor_selector: str) -> list[str]:
    """`export const NAME = [ ... ];` bloğunu sırayla ayrıştırır.

    Tek tırnaklı string literal'leri ve EDITOR_SELECTOR çıplak tanımlayıcısını
    (değeriyle değiştirilerek) döndürür. Sıra korunur.
    """
    m = re.search(rf"export const {name}\s*=\s*\[(.*?)\];", text, flags=re.S)
    assert m, f"{name} dizisi JS'te bulunamadı"
    body = m.group(1)
    items: list[str] = []
    # Token token tara: ya tek tırnaklı string ya da EDITOR_SELECTOR tanımlayıcısı.
    token_re = re.compile(r"'([^']*)'|\bEDITOR_SELECTOR\b")
    for tm in token_re.finditer(body):
        if tm.group(1) is not None:
            items.append(tm.group(1))
        else:
            items.append(editor_selector)
    assert items, f"{name} dizisi boş ayrıştırıldı"
    return items


def test_editor_selector_parity() -> None:
    text = _read_js()
    assert _extract_scalar(text, "EDITOR_SELECTOR") == arena_api.ARENA_EDITOR_SELECTOR


def test_editor_fallbacks_parity() -> None:
    text = _read_js()
    editor = _extract_scalar(text, "EDITOR_SELECTOR")
    js_list = _extract_array(text, "EDITOR_FALLBACKS", editor)
    assert js_list == list(arena_api.ARENA_EDITOR_FALLBACKS), (
        "EDITOR_FALLBACKS ayrıştı — JS ve Python sabitlerini eşitle."
    )


def test_send_selectors_parity() -> None:
    text = _read_js()
    editor = _extract_scalar(text, "EDITOR_SELECTOR")
    js_list = _extract_array(text, "SEND_SELECTORS", editor)
    assert js_list == list(arena_api.ARENA_SEND_SELECTORS), (
        "SEND_SELECTORS ayrıştı — JS ve Python sabitlerini eşitle."
    )


def test_consent_button_labels_parity() -> None:
    text = _read_js()
    editor = _extract_scalar(text, "EDITOR_SELECTOR")
    js_list = _extract_array(text, "CONSENT_BUTTON_LABELS", editor)
    assert js_list == list(arena_api.ARENA_CONSENT_BUTTON_LABELS), (
        "CONSENT_BUTTON_LABELS ayrıştı — JS ve Python sabitlerini eşitle."
    )
