# GitHub sync

## Status

accepted

## Summary

`planhub pull`, `planhub push`, and `planhub sync` reconcile local `.plan/`
Markdown artifacts with GitHub Issues and Milestones. `pull` imports GitHub
state into the filesystem; `push` creates or updates GitHub resources from
local files and applies archive policies for closed artifacts; `sync` runs
`pull` then `push`.

## User stories

- As a developer, I want to edit planning Markdown in git and push it to GitHub,
  so that issues stay reviewable in PRs and visible on GitHub boards.
- As a developer, I want sync to import existing GitHub issues and milestones,
  so that local files stay aligned with remote planning state.
- As a developer, I want dry-run and verbosity controls, so that I can validate
  a sync before writing and inspect planned path-level changes.
- As a developer, I want directional `pull`/`push` commands, so I can choose
  which side updates first instead of always running the full round trip.
- As a developer, I want an opt-in way to refresh a local issue file's content
  from GitHub, so a stale local copy doesn't silently linger.

## Requirements

- `pull`, `push`, and `sync` all require an initialized `.plan/` layout.
- When credentials and `remote.origin.url` are available, `pull`:
  - reconciles milestone files from every GitHub milestone (including empty,
    closed, and open milestones that only contain closed issues);
  - imports open GitHub issues into `.plan/` (closed issues are not imported as
    new files unless they belong to a milestone);
  - moves local issue files to match GitHub milestone assignment;
  - with `--force`, also overwrites an already-imported local issue file's
    title, body, labels, assignees, milestone, and state from its current
    GitHub content — merged onto existing front matter, so local-only keys
    (e.g. `id`) are preserved. Without `--force`, an already-imported issue's
    content is left untouched.
- When credentials and `remote.origin.url` are available, `push`:
  - creates missing GitHub milestones/issues from local files without a
    `number`;
  - updates existing GitHub milestones/issues from local files that already
    have a `number`;
  - writes GitHub `number` back into local front matter after creation;
  - archives or deletes closed synced root issues per config policy;
  - moves closed milestone directories to `.plan/archive/milestones` and open
    ones back under `.plan/milestones`.
- `sync` runs `pull` then `push`, with the same combined behavior as before the
  split.
- GitHub is the source of truth for issue `state` / `state_reason` and for
  milestone `state`. Local values for those fields are reconciled from GitHub
  responses; neither `push` nor `sync` pushes local issue state/state_reason as
  an authoritative override of GitHub.
- `push` (and the push half of `sync`) runs as: parse local files into a sync
  plan → apply the plan (or stop after planning in dry-run).
- CLI flags `--dry-run`, `--verbose`, and `--compact` override config behavior
  for that invocation on all three commands. Flags win over config. `--force`
  is `pull`-only.
- Each command prints explicit operation counts for its own phase(s):
  import/overwrite counts for `pull`; create/update/archive/delete counts for
  `push`; both for `sync`.
- Parse or apply errors are reported and cause a non-zero exit. `push` (and
  `sync`'s push half) exits non-zero if it has pending creates/updates but no
  GitHub credentials are available.

## Behavior

### `planhub pull` (GitHub → `.plan/`)

1. Load layout; resolve GitHub credentials and owner/repo when possible.
2. Reconcile milestone documents and open-milestone archive locations from
   GitHub.
3. Import existing GitHub issues into the local tree (create/move/skip, or
   overwrite content when `--force` is set).
4. Reconcile open-milestone archive locations again (import may have created
   new milestone directories).

Runs its local reconcile steps even without credentials (exit 0); import is
skipped when credentials are unavailable.

### `planhub push` (`.plan/` → GitHub)

1. Parse local milestone and issue documents into a sync plan.
2. If `--dry-run`, print planned counts (and path details when verbose) and
   exit without applying create/update/archive writes.
3. Otherwise create/update milestones and issues on GitHub, then archive
   closed root issues and move closed milestone directories.

### `planhub sync`

Runs the full `pull` pipeline, then the full `push` pipeline, printing both
phases' summaries. Behaves exactly as the pre-split combined `sync` did.

### Import rules (pull)

- Match local files by GitHub `number` when present.
- Create new local files for unmatched open GitHub issues.
- Move existing local files when GitHub milestone assignment differs.
- Skip closed GitHub issues for new imports; reopened issues can reappear via
  import/update flows.
- With `--force`, rewrite an already-matched local file's content from GitHub
  (see Requirements above); without it, only the move (if any) happens.

### Push rules (local → GitHub)

- Local files without `number` are candidates for create.
- Local files with `number` are candidates for update of title, body, labels,
  assignees, milestone, and type as present in front matter.
- Empty `labels: []` / `assignees: []` clear those fields on GitHub.
- `milestone: null` clears the GitHub milestone.

### Filesystem archive rules (push)

- Root issues with a GitHub `number` and `state: closed` are archived under
  `.plan/archive/issues` by default, or deleted when
  `sync.closed_issues.policy: delete`.
- Milestone-scoped issues stay inside their milestone directory; closing the
  milestone moves the whole directory to `.plan/archive/milestones`.

## Acceptance scenarios (BDD)

See `docs/specs/features/20260719-github-sync.feature`.

## Related

- Spec: [plan layout and init](20260719-plan-layout-and-init.md)
- Spec: [issue and milestone documents](20260719-issue-and-milestone-documents.md)
- Spec: [layered configuration](20260719-layered-configuration.md)
- ADR: [0002 GitHub source of truth for state](../adr/0002-github-source-of-truth-for-state.md)
- ADR: [0004 archive closed artifacts by policy](../adr/0004-archive-closed-artifacts-by-policy.md)
- ADR: [0005 three-phase sync pipeline](../adr/0005-three-phase-sync-pipeline.md)
- ADR: [0006 directional pull and push commands](../adr/0006-directional-pull-and-push-commands.md)
- Plan: [config and sync hardening](../plans/20260327-config-sync-hardening.completed.md)
- Plan: [pull and push commands](../plans/20260727-pull-and-push-commands.completed.md)
- Idea: [pull and push commands](../ideas/20260719-pull-and-push-commands.md)
- Acceptance: `docs/specs/features/20260719-github-sync.feature`

## Open Questions

- Milestone archive target collisions (directory already exists under archive)
  need clearer user recovery UX; tracked as an open bug in `.plan/`.
- `push --force` semantics (forcing a local state override onto GitHub) are
  intentionally undefined; not planned.
- Refreshing milestone `title`/`description`/`due_on` from GitHub during
  `pull --force` is out of scope for now — it would require handling the
  directory rename a changed title implies.
