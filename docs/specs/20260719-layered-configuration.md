# Layered configuration and setup

## Status

accepted

## Summary

Planhub loads sync defaults from built-in values, then
`~/.planhub/config.yaml`, then `.plan/config.yaml`. `planhub setup` creates the
global config file when missing. Authentication reuses `GITHUB_TOKEN` /
`GH_TOKEN` or the GitHub CLI session.

## User stories

- As a developer, I want global defaults for every repo, so that I do not repeat
  the same sync preferences.
- As a developer, I want per-repo overrides, so that one project can archive
  closed issues differently from another.
- As a developer, I want `planhub setup` after install, so that a global config
  exists before the first sync.

## Requirements

- Config precedence: built-in defaults < global config < repository config.
- Merge strategy: nested mappings merge recursively; scalars and lists replace.
- Unknown keys and invalid types/enums raise a clear config error naming the
  file and dotted path.
- Default schema includes:
  - `sync.closed_issues.policy`: `archive` | `delete` (default `archive`)
  - `sync.closed_issues.archive_dir`: path relative to repo root (default
    `.plan/archive/issues`)
  - `sync.github.default_assignees`: list of strings (default `[]`)
  - `sync.github.default_labels`: list of strings (default `[]`)
  - `sync.behavior.dry_run`: boolean (default `false`)
  - `sync.behavior.verbosity`: `compact` | `verbose` (default `compact`)
- `planhub setup` creates `~/.planhub/config.yaml` if missing; `--dry-run`
  previews only.
- `planhub init` also ensures global and repo configs exist (see layout spec).
- Auth token resolution order: `GITHUB_TOKEN`, then `GH_TOKEN`, then
  `gh auth token`.
- Repository identity comes from `git remote get-url origin` and must parse as a
  GitHub owner/repo.

## Behavior

`load_config(repo_root)` deep-merges validated YAML overlays onto defaults and
resolves relative `archive_dir` against the repository root. Commands that need
GitHub access call auth helpers once per invocation and surface missing
credentials with actionable guidance.

## Acceptance scenarios (BDD)

See `docs/specs/features/20260719-layered-configuration.feature`.

## Related

- Spec: [plan layout and init](20260719-plan-layout-and-init.md)
- Spec: [GitHub sync](20260719-github-sync.md)
- ADR: [0003 layered configuration](../adr/0003-layered-configuration.md)
- Plan: [config and sync hardening](../plans/20260327-config-sync-hardening.completed.md)
- Idea: [interactive config prompts](../ideas/20260719-interactive-config-prompts.md)
- Acceptance: `docs/specs/features/20260719-layered-configuration.feature`

## Open Questions

- Interactive prompts during setup/init are intentionally deferred.
