# Directional pull and push commands

## Status

accepted

## Context

`planhub sync` combined GitHub-to-local reconciliation and local-to-GitHub
writes in one command, with no way to run either direction alone. Users
treating `.plan/` as a working tree wanted git-like control: refresh from
GitHub without writing anything, or push local changes without an implicit
import first. `docs/ideas/20260719-pull-and-push-commands.md` and `.plan`
issue #9 requested this split; the sync spec listed it as an open question.

`sync_command()` already separated cleanly along this line: the first half
only reads GitHub and writes local files (milestone state reconciliation,
issue import); the second half only reads local files and writes GitHub
(build plan, apply plan, archive closed issues).

## Decision

Split the pipeline into `planhub pull` and `planhub push`, and keep
`planhub sync` as a wrapper that runs `pull` then `push` with identical
observable behavior to before the split (ADR-0005's three phases still
describe the inside of `push`).

- `push` keeps the full write phase — create *and* update issues/milestones,
  plus the local closed-issue archive step — not just creates. Otherwise
  `sync ≠ pull + push` and the CLI would need two divergent write paths.
- `pull` gains an opt-in `--force` flag that overwrites an already-imported
  local issue file's title/body/labels/assignees/milestone/state from its
  current GitHub content, merged onto existing front matter so local-only
  keys (e.g. `id`) survive. Without `--force`, pull keeps the pre-split
  skip-if-exists behavior. The idea doc's explicit no-go is *silent*
  overwriting; `--force` is the opt-in path it asks for.
- `--force` lives on `pull` only, not on `sync` or `push`. Next to a
  push-capable command it would read as force-push, a much more consequential
  and differently-scoped operation. Users who want both run
  `planhub pull --force && planhub push`.
- `push` does not implicitly pull first, and prints no "pull first" hint.
  Combining the two directions is exactly what `sync` is for; keeping `push`
  pure keeps CI usage predictable.
- `pull --force` refreshes issue files only. Milestones keep their existing
  state-only reconciliation (`reconcile_milestone_states_from_github`);
  refreshing a milestone's title would change its directory slug, which
  drags in rename/collision handling out of scope for this change.

## Consequences

- Two new CLI commands, plus one new flag; `sync`'s behavior, output, and
  exit codes are unchanged.
- `src/planhub/cli/commands/sync/pull.py` and `.../push.py` hold the two
  phases; `src/planhub/cli/commands/sync/__init__.py` composes them into
  `pull_command`, `push_command`, and `sync_command`.
- `import_existing_issues` gained a `force` parameter and an
  `issues_overwritten` counter; `documents.py` gained `rewrite_document` to
  replace a file's body while preserving unrelated front matter keys.

## Related

- Spec: [GitHub sync](../specs/20260719-github-sync.md)
- ADR: [0002 GitHub source of truth for state](0002-github-source-of-truth-for-state.md)
- ADR: [0005 three-phase sync pipeline](0005-three-phase-sync-pipeline.md)
- Idea: [pull and push commands](../ideas/20260719-pull-and-push-commands.md)
- Plan: [pull and push commands](../plans/20260727-pull-and-push-commands.completed.md)
- `.plan` issue: #9
