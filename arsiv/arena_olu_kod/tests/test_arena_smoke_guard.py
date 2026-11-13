"""Arena smoke test workflow salt-okur koruması.

arena_smoke_test.yml asla secret geri yazmamalı; bu testle sabitlenir.
"""
from __future__ import annotations

from pathlib import Path

import yaml

WORKFLOW = Path(".github/workflows/arena_smoke_test.yml")


def _text() -> str:
    assert WORKFLOW.exists(), "arena_smoke_test.yml oluşturulmalı"
    return WORKFLOW.read_text(encoding="utf-8")


def test_smoke_workflow_readonly_permissions() -> None:
    data = yaml.safe_load(_text())
    perms = data.get("permissions")
    assert perms == {"contents": "read"}, (
        f"Smoke workflow salt-okur olmalı, bulundu: {perms!r}"
    )


def test_smoke_workflow_no_secret_write_command() -> None:
    text = _text().lower()
    # Literal "secret set" komutu veya "gh secret" hiç geçmemeli.
    assert "secret set" not in text, "Smoke workflow'da secret yazma komutu olmamalı"
    assert "gh secret" not in text, "Smoke workflow'da gh secret komutu olmamalı"


def test_smoke_workflow_no_workflow_run_trigger() -> None:
    data = yaml.safe_load(_text())
    triggers = data.get(True, data.get("on", {}))  # yaml 'on' -> True
    assert "workflow_run" not in triggers, (
        "Smoke workflow workflow_run ile tetiklenmemeli (salt okur, geri yazmaz)."
    )
    assert "workflow_dispatch" in triggers, "Smoke workflow manuel tetiklenebilir olmalı"


def test_smoke_workflow_uploads_diagnostics_artifact() -> None:
    text = _text()
    assert "arena-diagnostics" in text, "Tanılama çıktısı artifact olarak yüklenmeli"
    assert "actions/upload-artifact" in text, "upload-artifact adımı olmalı"
