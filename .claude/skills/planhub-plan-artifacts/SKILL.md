---
name: planhub-plan-artifacts
description: >-
  Use when creating or editing files under .plan/ (issues, milestones) in this
  repository, or when asked to plan work, file an issue, or set up a
  milestone. Covers required front matter, file layout, naming, and when
  (and when not) to run `planhub pull`, `planhub push`, or `planhub sync`.
---

# Planning artifacts (Planhub)

This repository tracks planning data as Markdown under `.plan/`, synced to
GitHub Issues and Milestones by [Planhub](https://github.com/your-org/planhub).

## Layout

- `.plan/issues/YYYYMMDD-title.md` — backlog issues, not tied to a milestone.
- `.plan/milestones/<slug>/milestone.md` — one file per milestone.
- `.plan/milestones/<slug>/issues/*.md` — issues that belong to that milestone.
- `.plan/archive/` — closed items moved here by `planhub push` (or `sync`). Don't hand-edit archive contents.

## Issue front matter

```yaml
---
id: "planhub-issue-001"      # stable local id; set for new files
number:                      # leave unset - filled in by sync
title: "Stage 1 - Schema + Migrations"
labels: ["schema", "db"]
milestone: "Stage 1"         # title or number; null to clear
assignees: ["github-username"]
type: "Task"                 # optional
state: "open"                # open | closed
state_reason: "completed"    # optional, requires state: closed
---
```

Body (below the front matter) is the issue description; use checklists for subtasks.

## Milestone front matter

```yaml
---
id: "planhub-milestone-001"
number:
title: "Stage 1"
description: "Schema + migrations for places and facts."
due_on: "2026-03-01T00:00:00Z"
state: "open"
---
```

## Rules

- Fill in `id` and body content for new files; leave `number` blank until sync assigns it.
- For issues/milestones that already have a `number`, don't hand-edit `state` or
  `state_reason` - sync/pull reconciles those from GitHub and will overwrite local edits.
- Use `labels: []` / `assignees: []` to clear a list, `milestone: null` to unset.

## Do not auto-run pull, push, or sync

Creating or editing files under `.plan/` is safe on its own. Never run
`planhub pull`, `planhub push`, or `planhub sync` on the user's behalf unless
they explicitly ask for it in this conversation:

- `planhub push` (and the push half of `sync`) writes real changes to GitHub
  Issues and Milestones.
- `planhub pull` only writes to local files, but `pull --force` overwrites an
  already-imported issue file's title/body with its current GitHub content,
  discarding uncommitted local edits to that file.
