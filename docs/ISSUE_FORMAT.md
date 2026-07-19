# Issue File Format

Each issue is a standalone markdown file under `.plan/issues/` or
`.plan/milestones/<milestone>/issues/` (or under `.plan/archive/` after sync
archives a closed root issue).

Behavior contract: [issue and milestone documents](specs/20260719-issue-and-milestone-documents.md).


## Front Matter
Use YAML front matter to store metadata. The sync tool will map these fields to
GitHub's REST API:

```yaml
---
id: "planhub-issue-001"        # stable local id (before GitHub number exists)
number: 123                    # GitHub issue number (filled after sync)
title: "Stage 1 — Schema + Migrations"
labels: ["schema", "db"]
milestone: "Stage 1"           # or a milestone number (e.g. 12)
assignees: ["your-username"]   # array only; "assignee" is deprecated by GitHub
type: "Task"                   # optional GitHub issue type name
state: "open"                  # open | closed
state_reason: "completed"      # optional: completed | not_planned
---
```

## Body
The markdown body (after front matter) is the issue description. Use checklists
for subtasks when needed.

## Notes
- GitHub's create issue endpoint accepts: `title`, `body`, `labels`,
  `assignees`, `milestone` (number), and `type`.
- `number` is the canonical identity after creation; it should be recorded
  once available to keep sync stable.
- During sync, GitHub is the source of truth for `state` and `state_reason`;
  local values for existing issues are reconciled from GitHub.
- Use `labels: []` or `assignees: []` to clear them on GitHub.
- Use `milestone: null` to remove a milestone.
- `state_reason` requires `state: "closed"`.

## Related

- Spec: [issue and milestone documents](specs/20260719-issue-and-milestone-documents.md)
- Spec: [GitHub sync](specs/20260719-github-sync.md)
- ADR: [0002 GitHub source of truth for state](adr/0002-github-source-of-truth-for-state.md)
