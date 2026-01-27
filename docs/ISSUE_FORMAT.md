# Issue File Format

Each issue is a standalone markdown file under `issues/`.

## Front Matter
Use YAML front matter to store metadata. The sync tool will map these fields to
GitHub's REST API:

```yaml
---
id: "planhub-issue-001"        # stable local id (before GitHub number exists)
number: 123                    # GitHub issue number (filled after sync)
owner: "your-org"
repo: "your-repo"
title: "Stage 1 — Schema + Migrations"
labels: ["schema", "db"]
milestone: "Stage 1"           # resolved to milestone number by sync
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
- `state` and `state_reason` are set via the update issue endpoint.
