# Milestone File Format

Each milestone is a `milestone.md` file under
`.plan/milestones/<slug>/` (or `.plan/archive/milestones/<slug>/` when closed).

Behavior contract: [issue and milestone documents](specs/20260719-issue-and-milestone-documents.md).

## Front Matter
Use YAML front matter to store metadata. The sync tool will map these fields to
GitHub's REST API:

```yaml
---
id: "planhub-milestone-001"     # stable local id (before GitHub number exists)
number: 12                      # GitHub milestone number (filled after sync)
title: "Stage 1"
description: "Schema + migrations for places and facts."
due_on: "2026-03-01T00:00:00Z"  # ISO 8601 timestamp
state: "open"                   # open | closed
---
```

## Body
The markdown body can include scope, acceptance criteria, or notes.

## Notes
- GitHub's create milestone endpoint accepts: `title`, `state`, `description`,
  and `due_on`.
- `number` is the canonical identity after creation; it should be recorded
  once available to keep sync stable.
- During sync, GitHub is the source of truth for milestone `state`; closed
  milestone directories are moved as a whole under `.plan/archive/milestones`.

## Related

- Spec: [GitHub sync](specs/20260719-github-sync.md)
- ADR: [0004 archive closed artifacts by policy](adr/0004-archive-closed-artifacts-by-policy.md)
