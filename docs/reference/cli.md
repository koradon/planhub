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
files exist (without overwriting). Also offers to install/update the bundled
`planhub-plan-artifacts` Claude Code / Cursor skill.

| Option | Description |
| --- | --- |
| `--dry-run` | Preview paths; do not write or prompt |
| `--skills` / `--no-skills` | Install/update or skip the skill files; never prompts. Omitted: prompts on a TTY, skips otherwise |

See [plan artifact agent skills](../specs/20260727-plan-artifact-agent-skills.md)
for the install/update decision flow and skill content.

### `planhub pull`

Import GitHub Issues and Milestones into `.plan/`. Never writes to GitHub.

| Option | Description |
| --- | --- |
| `--dry-run` | Report what would be imported/overwritten without writing |
| `--force` | Overwrite an already-imported local issue file's title/body/labels/assignees/milestone/state from its current GitHub content, preserving local-only front matter keys (e.g. `id`). Without it, an already-imported issue's content is left untouched |
| `--verbose` | Accepted for symmetry with `sync`/`push`; no additional output today |
| `--compact` | Accepted for symmetry with `sync`/`push`; no additional output today |

Runs its local reconcile steps even without credentials (exit 0); import is
skipped when credentials are unavailable.

### `planhub push`

Create/update GitHub Issues and Milestones from `.plan/`, then archive closed
issues and milestones locally. Never imports from GitHub.

| Option | Description |
| --- | --- |
| `--dry-run` | Build/report the plan without applying create/update/archive writes |
| `--verbose` | Path-level planned changes (overrides config) |
| `--compact` | Concise summary output (overrides config) |

Requires credentials only when the plan has pending creates/updates; exits
non-zero in that case if credentials are missing. With nothing pending, push
still runs the local archive step and succeeds without credentials.

### `planhub sync`

Runs `planhub pull` then `planhub push`, printing both phases' summaries.
Behavior, output, and exit codes are unchanged from before the pull/push
split.

| Option | Description |
| --- | --- |
| `--dry-run` | Build/report the plan without applying create/update/archive writes |
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
- Spec: [plan artifact agent skills](../specs/20260727-plan-artifact-agent-skills.md)
- Spec: [GitHub sync](../specs/20260719-github-sync.md)
- ADR: [0006 directional pull and push commands](../adr/0006-directional-pull-and-push-commands.md)
- Spec: [create issue command](../specs/20260719-create-issue-command.md)
- Spec: [layered configuration](../specs/20260719-layered-configuration.md)
- User-facing overview: [README.md](../../README.md)
