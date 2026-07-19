# Archive closed artifacts by policy

## Status

accepted

## Context and Problem Statement

After issues and milestones are closed on GitHub, leaving them in active
`.plan/issues` or `.plan/milestones` directories makes local planning noisy and
mixes backlog with completed work.

## Considered Options

- Leave closed artifacts in place forever.
- Always delete closed local files.
- Configurable policy for closed synced root issues (`archive` or `delete`),
  and whole-directory moves for closed milestones under
  `.plan/archive/milestones`.

## Decision Outcome

Chosen option: "Configurable archive/delete for closed root issues, and
whole-directory archival for milestones", because root backlog cleanup should be
policy-driven, while milestone folders must keep `milestone.md`, issues, and
assets together.

Default policy is `archive` to `.plan/archive/issues`.

### Consequences

- Good, because active directories stay focused on open work.
- Good, because milestone assets are not split across archive locations.
- Bad, because archive target collisions need explicit error handling.
- Bad, because closed milestone issues are not individually archived under the
  root issues archive path (by design).

## Related

- Spec: [GitHub sync](../specs/20260719-github-sync.md)
- ADR: [0003 layered configuration](0003-layered-configuration.md)
