# Issue File Format

Each issue is a standalone markdown file under `issues/`.

## Front Matter
Use YAML front matter to store metadata. The sync tool will map these fields to
GitHub's REST API:

```yaml
---
title: "Stage 1 — Schema + Migrations"
labels: ["schema", "db"]
milestone: "Stage 1"          # resolved to milestone number by sync
assignees: ["your-username"]  # array only; "assignee" is deprecated by GitHub
type: "Task"                  # optional GitHub issue type name
state: "open"                 # applied via update endpoint if needed
---
```

## Body
The markdown body (after front matter) is the issue description. Use checklists
for subtasks when needed.

## Notes
- GitHub's create issue endpoint accepts: `title`, `body`, `labels`,
  `assignees`, `milestone` (number), and `type`.
- `state` is set via the update issue endpoint (open/closed).
