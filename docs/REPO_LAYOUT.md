# Data Repo Layout

We store planning files under `.plan/` inside each target repository. Planhub
initializes the layout in the repo and syncs the data from that repo.

```
.plan/
  issues/
    20260127-backlog-issue.md
  milestones/
    stage-1/
      milestone.md
      issues/
        issue-001.md
        issue-002.md
      assets/
        diagram.png
        workflow.svg
```

## Notes
- `milestone.md` follows `docs/MILESTONE_FORMAT.md`.
- Each issue file follows `docs/ISSUE_FORMAT.md`, whether it is in the root
  `.plan/issues/` folder or under a milestone. Imported issues use
  `YYYYMMDD-title.md` for readability and chronological ordering.
- Use `.plan/issues/` for backlog issues that are not tied to a milestone.
- Use `assets/` for images or diagrams; Markdown can link to them with a
  relative path, e.g. `![diagram](assets/diagram.png)`.
