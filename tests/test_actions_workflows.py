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


def test_arena_self_repair_monitors_all_other_current_workflows() -> None:
    """The failure listener tracks every current workflow except itself to prevent loops."""
    workflow_dir = Path(".github/workflows")
    repair_path = workflow_dir / "arena_self_repair.yml"
    repair: Any = yaml.load(repair_path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    triggers = repair["on"]["workflow_run"]
    monitored = set(triggers["workflows"])
    existing = {
        workflow["name"]
        for path in workflow_dir.glob("*.yml")
        if path.name != repair_path.name
        if isinstance((workflow := yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)), dict)
    }
    assert monitored == existing
    assert triggers["types"] == ["completed"]
    assert "contents" in repair["permissions"]
