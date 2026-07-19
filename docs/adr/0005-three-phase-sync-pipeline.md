# Three-phase sync pipeline

## Status

accepted

## Context

Sync must validate local files, decide creates/updates/moves, and optionally
apply changes. Mixing discovery with mutation made dry-run and summaries harder
to reason about.

## Decision

We will structure `planhub sync` as a three-phase pipeline:

1. Reconcile/import and parse local documents.
2. Build an explicit sync plan (milestones/issues to create or update).
3. Apply the plan (skipped on `--dry-run`), then run filesystem archive moves.

## Consequences

- Dry-run can report planned counts and path-level verbose details without
  applying create/update mutations.
- Summary counters map cleanly to plan and apply results.
- Contributors can extend sync by adding plan entries rather than scattering
  side effects through parsing.

## Related

- Spec: [GitHub sync](../specs/20260719-github-sync.md)
- ADR: [0001 local markdown planning synced to GitHub](0001-local-markdown-planning-synced-to-github.md)
