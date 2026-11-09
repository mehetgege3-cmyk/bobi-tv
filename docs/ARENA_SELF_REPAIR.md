# Arena AI GitHub Actions self-repair

## Flow

`.github/workflows/arena_self_repair.yml` listens for failed, timed-out, startup-failed, or action-required runs from each existing BOBİ TV/Arena workflow. For failures belonging to this repository, it downloads the Actions log, gathers the triggering commit's changed files, workflow definition, and source paths referenced by the log, then sends a bounded, redacted incident prompt to Arena through the existing Playwright session.

Arena is asked for one unified diff. The workflow extracts it, verifies/applies it with `git apply --check`, then installs project dependencies and requires all of these to pass before a direct push to `main`:

```bash
pytest -q
mypy --strict
ruff check
ruff format --check
```

A successful repair becomes a `fix: Arena self-repair for run <id>` commit. The previously failed workflow is not automatically re-run: doing so for publish, cleanup, or batch production could cause duplicate side effects. The repair job itself is not a trigger source, to avoid unbounded self-repair loops.

## GitHub configuration

- Required Actions secret: `ARENA_COOKIES_JSON` for the Arena Playwright session.
- Repository Actions must allow the workflow's declared `actions: read` and `contents: write` permissions.
- Push uses `GH_PAT` when configured; otherwise it uses the run-scoped `GITHUB_TOKEN`. A protected `main` branch or repository policy that denies Actions writes will stop the push.
- Keep credentials in GitHub's secret store; never put a PAT, Arena cookie, YouTube credential, or secret value in a prompt or chat.

## Handling rules

- Failure logs and source context are bounded and scrubbed for common GitHub token, bearer, cookie, and secret-assignment patterns before the Arena request.
- Arena only returns a proposed diff. It has no GitHub token in the request step. The credentialed download and push steps are separate from the Arena request and test steps.
- A missing/expired Arena session, an unparseable answer, invalid patch, failed quality gate, rebase conflict, or denied push fails closed: no patch is pushed.
- Same-repository workflows are eligible. Runs from forks are ignored so untrusted fork code/logs cannot exercise repository secrets.
- The automation can edit tracked source/workflow files because the configured policy is autonomous. The quality gates are the required pre-push check, not a human review.
- `.github/workflows/arena_self_repair.yml` itself is intentionally excluded from its own trigger list. Repairing this automation's failure requires a manual intervention; otherwise it could recursively create failure/retry runs.

## Monitored workflows

The trigger list covers the current Playwright Agent, Arena Senaryo, manual production, hourly production, channel cleanup, test pipeline, and weekly report workflows. Add any future workflow's exact `name:` to `workflow_run.workflows` if its failures should also be repaired.
