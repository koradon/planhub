# CLI reference

## Status

active

## Overview

Command-line interface for Planhub (`planhub`), a Typer app installed as the
`planhub` console script.

## Entries

### `planhub setup`

Create `~/.planhub/config.yaml` if missing.

| Option | Description |
| --- | --- |
| `--dry-run` | Preview the path; do not write |

### `planhub init`

Create `.plan/issues` and `.plan/milestones`, and ensure global + repo config
files exist (without overwriting).

| Option | Description |
| --- | --- |
| `--dry-run` | Preview paths; do not write |

### `planhub sync`

Reconcile `.plan/` with GitHub Issues and Milestones.

| Option | Description |
| --- | --- |
| `--dry-run` | Build/report the plan without applying create/update writes |
| `--verbose` | Path-level planned changes (overrides config) |
| `--compact` | Concise summary output (overrides config) |

Requires credentials for import/create/update. Missing credentials print a
warning; create/update that need the API then fail.

### `planhub issue <title>`

Create a GitHub issue immediately and write a root backlog file under
`.plan/issues/`.

Requires credentials and a GitHub `remote.origin.url`.

## Related

- Spec: [plan layout and init](../specs/20260719-plan-layout-and-init.md)
- Spec: [GitHub sync](../specs/20260719-github-sync.md)
- Spec: [create issue command](../specs/20260719-create-issue-command.md)
- Spec: [layered configuration](../specs/20260719-layered-configuration.md)
- User-facing overview: [README.md](../../README.md)
