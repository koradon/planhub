# Data Repo Layout

We store planning files under `.plan/` inside each target repository. Planhub
initializes the layout in the repo and syncs the data from that repo.

```
.plan/
  config.yaml
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
  archive/
    issues/
      20260327-closed-root-issue.md
    milestones/
      stage-0/
        milestone.md
        issues/
          issue-000.md
```

## Notes
- `milestone.md` follows `docs/MILESTONE_FORMAT.md`.
- Each issue file follows `docs/ISSUE_FORMAT.md`, whether it is in the root
  `.plan/issues/` folder or under a milestone. Imported issues use
  `YYYYMMDD-title.md` for readability and chronological ordering.
- Use `.plan/issues/` for backlog issues that are not tied to a milestone.
- Use `assets/` for images or diagrams; Markdown can link to them with a
  relative path, e.g. `![diagram](assets/diagram.png)`.
- Closed synced root issues move under `.plan/archive/issues` by default
  (or are deleted when configured). Closed milestones move as whole directories
  under `.plan/archive/milestones`.

## Related

- Spec: [plan layout and init](specs/20260719-plan-layout-and-init.md)
- Spec: [GitHub sync](specs/20260719-github-sync.md)
