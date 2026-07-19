# GitHub sync

## Status

accepted

## Summary

`planhub sync` reconciles local `.plan/` Markdown artifacts with GitHub Issues
and Milestones. It imports missing GitHub items into the filesystem, creates or
updates GitHub resources from local files, and applies archive policies for
closed artifacts.

## User stories

- As a developer, I want to edit planning Markdown in git and push it to GitHub,
  so that issues stay reviewable in PRs and visible on GitHub boards.
- As a developer, I want sync to import existing GitHub issues and milestones,
  so that local files stay aligned with remote planning state.
- As a developer, I want dry-run and verbosity controls, so that I can validate
  a sync before writing and inspect planned path-level changes.

## Requirements

- Sync requires an initialized `.plan/` layout.
- When credentials and `remote.origin.url` are available, sync:
  - reconciles milestone files from every GitHub milestone (including empty,
    closed, and open milestones that only contain closed issues);
  - imports open GitHub issues into `.plan/` (closed issues are not imported as
    new files);
  - creates missing GitHub milestones/issues from local files without a
    `number`;
  - updates existing GitHub milestones/issues from local files that already have
    a `number`;
  - writes GitHub `number` back into local front matter after creation;
  - moves local issue files to match GitHub milestone assignment;
  - archives or deletes closed synced root issues per config policy;
  - moves closed milestone directories to `.plan/archive/milestones` and open
    ones back under `.plan/milestones`.
- GitHub is the source of truth for issue `state` / `state_reason` and for
  milestone `state` during sync. Local values for those fields are reconciled
  from GitHub responses; sync does not push local issue state/state_reason as
  an authoritative override of GitHub.
- Sync runs as: load/reconcile → build a sync plan → apply the plan (or stop
  after planning in dry-run).
- CLI flags `--dry-run`, `--verbose`, and `--compact` override config behavior
  for that invocation. Flags win over config.
- Sync prints explicit operation counts for import/create/update/archive/delete.
- Parse or apply errors are reported and cause a non-zero exit.

## Behavior

### High-level pipeline

1. Load layout and layered config; resolve verbosity.
2. Authenticate (token via `GITHUB_TOKEN`/`GH_TOKEN` or `gh auth token`) and
   resolve owner/repo from git remote when possible.
3. Reconcile milestone documents and open-milestone archive locations from
   GitHub.
4. Import existing open GitHub issues into the local tree (create/move/skip).
5. Parse local milestone and issue documents into a sync plan.
6. If `--dry-run`, print planned counts (and path details when verbose) and exit
   without applying create/update/archive writes from the plan.
7. Otherwise apply create/update operations, then archive closed root issues and
   move closed milestone directories.

### Import rules

- Match local files by GitHub `number` when present.
- Create new local files for unmatched open GitHub issues.
- Move existing local files when GitHub milestone assignment differs.
- Skip closed GitHub issues for new imports; reopened issues can reappear via
  import/update flows.

### Push rules (local → GitHub)

- Local files without `number` are candidates for create.
- Local files with `number` are candidates for update of title, body, labels,
  assignees, milestone, and type as present in front matter.
- Empty `labels: []` / `assignees: []` clear those fields on GitHub.
- `milestone: null` clears the GitHub milestone.

### Filesystem archive rules

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
- Plan: [config and sync hardening](../plans/20260327-config-sync-hardening.completed.md)
- Acceptance: `docs/specs/features/20260719-github-sync.feature`

## Open Questions

- Separate `pull` / `push` commands (see ideas) may later split this combined
  sync behavior.
- Milestone archive target collisions (directory already exists under archive)
  need clearer user recovery UX; tracked as an open bug in `.plan/`.
