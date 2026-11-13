"""Workflow syntax and self-repair trigger coverage."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def test_all_actions_workflows_parse_as_yaml() -> None:
    """Every tracked Actions workflow stays valid YAML after automated edits."""
    workflow_dir = Path(".github/workflows")
    workflows = list(workflow_dir.glob("*.yml"))
    assert workflows
    for path in workflows:
        parsed: object = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
        assert isinstance(parsed, dict), path
        assert isinstance(parsed.get("name"), str), path
        assert "jobs" in parsed, path
