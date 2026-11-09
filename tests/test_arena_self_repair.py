"""Security and parsing tests for the Actions-to-Arena repair bridge."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.arena_self_repair import build_prompt, extract_patch, sanitize_text


def test_sanitize_text_redacts_token_bearer_cookie_and_secret_assignment() -> None:
    """Failure logs are scrubbed before they are sent to Arena."""
    raw = (
        "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890\n"
        "Authorization: Bearer abcdefghijklmnopqrstuvwxyz012345\n"
        "Set-Cookie: arena-auth-prod-v1=do-not-send\n"
        "GH_PAT=some-secret-value"
    )
    safe = sanitize_text(raw)
    assert "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890" not in safe
    assert "abcdefghijklmnopqrstuvwxyz012345" not in safe
    assert "do-not-send" not in safe
    assert "some-secret-value" not in safe
    assert "[REDACTED]" in safe


def test_extract_patch_accepts_plain_or_fenced_unified_diff() -> None:
    """The bridge extracts a standard patch and rejects prose-only answers."""
    diff = (
        "diff --git a/example.py b/example.py\n"
        "index 1111111..2222222 100644\n"
        "--- a/example.py\n"
        "+++ b/example.py\n"
        "@@ -1 +1 @@\n"
        "-bad = True\n"
        "+bad = False\n"
    )
    assert extract_patch(f"```diff\n{diff}```") == diff
    with_explanation = f"Example only: ```text\nnot a patch\n```\n```diff\n{diff}```"
    assert extract_patch(with_explanation) == diff
    try:
        extract_patch("The error is probably a typo; no patch attached.")
    except ValueError as error:
        assert "unified diff" in str(error)
    else:
        raise AssertionError("A prose-only Arena reply must not be pushed.")


def test_build_prompt_redacts_logs_and_includes_incident_metadata(tmp_path: Path) -> None:
    """Arena receives bounded context with a sanitized failure-log section."""
    log_path = tmp_path / "failure.log"
    log_path.write_text("ImportError: missing module\nGH_PAT=do-not-send", encoding="utf-8")
    prompt = build_prompt(
        run_id="123456",
        workflow_name="Test workflow",
        head_sha="abc123",
        conclusion="failure",
        log_text=log_path.read_text(encoding="utf-8"),
    )
    assert "123456" in prompt and "Test workflow" in prompt and "failure" in prompt
    assert "ImportError: missing module" in prompt
    assert "do-not-send" not in prompt
    assert "<failure-log>" in prompt and "<repository-files>" in prompt


def test_extract_patch_cli_writes_only_diff(tmp_path: Path) -> None:
    """GitHub workflow can use the same checked extraction path as unit tests."""
    diff = (
        "diff --git a/example.py b/example.py\n"
        "--- a/example.py\n"
        "+++ b/example.py\n"
        "@@ -1 +1 @@\n"
        "-before\n"
        "+after\n"
    )
    answer = tmp_path / "answer.txt"
    output = tmp_path / "fix.patch"
    answer.write_text(f"```diff\n{diff}```", encoding="utf-8")
    subprocess.run(
        [
            sys.executable,
            "scripts/arena_self_repair.py",
            "extract-patch",
            "--answer-file",
            str(answer),
            "--output",
            str(output),
        ],
        check=True,
    )
    assert output.read_text(encoding="utf-8") == diff
