# Pull and push commands

## Status

completed

## Related

- Spec: [GitHub sync](../specs/20260719-github-sync.md)
- ADR: [0006 directional pull and push commands](../adr/0006-directional-pull-and-push-commands.md)
- Idea: [pull and push commands](../ideas/20260719-pull-and-push-commands.md)
- `.plan` issue: #9

## Scope

Implements the ADR: split `planhub sync`'s existing pipeline into
`src/planhub/cli/commands/sync/pull.py` (GitHub → `.plan/`) and
`.../push.py` (`.plan/` → GitHub), add `planhub pull`/`planhub push` CLI
commands, and add `pull --force` for overwriting already-imported local issue
content from GitHub. `sync` keeps running `pull` then `push` with unchanged
behavior and exit codes; its Import line now also carries the `overwrite N,`
segment shared with `pull`'s summary (always `0` for `sync`).

## Steps

1. `sync/pull.py` — `PullStats`, `run_pull()`, `echo_pull_summary()`. Lifts,
   unchanged in order: `reconcile_milestone_states_from_github`,
   `reconcile_milestone_archive_locations` (open), `import_existing_issues`,
   the same archive reconcile again.
2. `sync/push.py` — `PushStats`, `run_push()`, `echo_push_summary()`,
   `echo_verbose_plan()`. Takes an already-parsed `SyncPlan`; applies it, then
   `archive_closed_issues_in_filesystem` and the closed-direction archive
   reconcile. Preserves the pre-split dry-run short-circuit (no apply, no
   archive step, so archive/delete counts stay `0`).
3. Rewrite `sync/__init__.py` as three thin orchestrators (`pull_command`,
   `push_command`, `sync_command`) sharing `_load_layout_and_config`,
   `_resolve_client`, `_report_parse_errors`, `_get_github_client`. Removes
   the old `SyncOutputStats` rebuild chain.
4. `documents.py` — add `rewrite_document(path, updates, body) -> bool`:
   merges front matter like `update_front_matter` but replaces the body too.
5. `importer.py` — `import_existing_issues(..., force=False)`; `ImportResult`
   gains `issues_overwritten`; `_maybe_move_issue` returns `Path | None`
   instead of `bool` so a forced overwrite targets the post-move path; new
   `_overwrite_issue_from_github` helper does the dry-run-safe comparison.
6. CLI wiring: `pull`/`push` entries in `cli/app.py`, sharing a
   `_resolve_verbosity_override` helper with `sync`; export
   `pull_command`/`push_command` from `cli/commands/__init__.py`.
7. Tests: new `tests/test_pull_push_commands.py`; repoint the one
   `reconcile_milestone_states_from_github` patch in `test_sync_command.py`
   to `planhub.cli.commands.sync.pull`; force/move/dry-run cases in
   `test_importer.py`; `rewrite_document` cases in `test_documents.py`.
8. Docs: this plan, ADR-0006, spec + feature updates, idea status flip,
   roadmap move, `docs/reference/cli.md`, `README.md`, and the
   `planhub-plan-artifacts` skill template's "don't auto-sync" section.

## Risks

- `pull --force` overwriting uncommitted local edits: opt-in only, reported
  under `--dry-run` before any write, and `.plan/` lives in git so a bad
  force is one `git checkout` away.
- 33 existing tests patch `planhub.cli.commands.sync.{get_auth_token,
  GitHubClient, get_github_repo_from_git}` — those names stay in
  `__init__.py` so only the one milestone-reconcile patch needed to move.
- Verified via `uv run pytest` (228 passed, including all pre-existing sync
  suites unmodified except the one patch rename) and `uv run ruff check .` /
  `uv run ruff format --check .`.

## Open Questions

- None currently blocking. Deferred: conflict detection when both sides
  changed, `push --force`, dry-run reporting archive/delete counts, and
  refreshing milestone title/description/due_on on `pull --force` — see the
  spec's Open Questions.
