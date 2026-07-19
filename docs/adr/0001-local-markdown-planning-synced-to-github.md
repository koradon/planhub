# Local markdown planning synced to GitHub

## Status

accepted

## Context and Problem Statement

Teams want planning artifacts that are reviewable in git, editable with normal
developer tools, and still visible as GitHub Issues and Milestones for boards
and collaboration. Keeping plans only on GitHub loses local reviewability;
keeping them only in git loses GitHub workflow integration.

## Considered Options

- Store plans only as GitHub Issues (no local files).
- Store plans only as local Markdown (no GitHub sync).
- Store Markdown under `.plan/` in each repo and sync bidirectionally to GitHub
  Issues/Milestones via a CLI.

## Decision Outcome

Chosen option: "Store Markdown under `.plan/` and sync to GitHub via CLI",
because planning stays next to code, diffs are reviewable, and GitHub remains
the collaboration surface.

### Consequences

- Good, because planning changes can go through normal git review.
- Good, because the same files drive GitHub Issues/Milestones.
- Bad, because sync semantics (especially source-of-truth rules) must be
  documented and tested carefully to avoid drift.
- Bad, because users need credentials and a GitHub remote configured.

## Related

- Spec: [plan layout and init](../specs/20260719-plan-layout-and-init.md)
- Spec: [GitHub sync](../specs/20260719-github-sync.md)
- ADR: [0002 GitHub source of truth for state](0002-github-source-of-truth-for-state.md)
