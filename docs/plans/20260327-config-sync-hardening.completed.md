# Config and sync hardening

## Status

completed

## Related

- Spec: [layered configuration](../specs/20260719-layered-configuration.md)
- Spec: [GitHub sync](../specs/20260719-github-sync.md)
- ADR: [0002 GitHub source of truth for state](../adr/0002-github-source-of-truth-for-state.md)
- ADR: [0003 layered configuration](../adr/0003-layered-configuration.md)
- ADR: [0004 archive closed artifacts by policy](../adr/0004-archive-closed-artifacts-by-policy.md)
- ADR: [0005 three-phase sync pipeline](../adr/0005-three-phase-sync-pipeline.md)

## Scope

Harden sync semantics and operability after the initial CLI shipped:

- layered global/repo configuration and `setup` command
- GitHub as source of truth for issue/milestone state
- closed root-issue archive/delete policy
- whole-directory milestone archival
- issue file placement from GitHub milestone assignment
- sync summary counters and compact/verbose output

Out of scope: interactive config prompts, explicit pull/push commands, init
welcome templates.

## Steps

1. Design and implement layered config schema with validation.
2. Add `planhub setup` and ensure configs from `init`.
3. Reconcile issue `state`/`state_reason` from GitHub; reject invalid local
   states.
4. Archive or delete closed synced root issues per policy.
5. Move closed/reopened milestone directories as whole trees.
6. Reconcile local issue paths from GitHub milestone assignment.
7. Add operation counters and verbosity overrides.
8. Expand tests around importer, milestone sync, and archive edge cases.

## Risks

- Archive target collisions when a destination directory already exists.
- Users expecting local state edits to close GitHub issues without a push model.

## Open Questions

- Milestone archive collision UX (open bug).
- Whether sync summary counters should include content-only updates more
  explicitly (open bug).
