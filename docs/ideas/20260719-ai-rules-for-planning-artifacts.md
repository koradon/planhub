# AI rules for creating planning artifacts

## Status

draft

## Summary

Ship agent/editor rule files that teach AI tools how to author valid Planhub
issue and milestone Markdown (layout, front matter, naming).

## Problem

Users increasingly draft plans with AI assistants. Without project-local rules,
generated files often miss required fields, use invalid states, or place files
in the wrong directories.

## Audience / value

Developers using Cursor/Claude/other agents to maintain `.plan/` content.

## Options

- Add Cursor/Claude rule files in this repository only.
- Have `planhub init` optionally install rule templates into the target repo.
- Document conventions only in README/docs (no installable rules).

## Constraints

- Rules must match accepted document and layout specs.
- Avoid leaking secrets; rules should describe formats only.
- Keep rules thin and link to `docs/` for details.

## Explicit no-gos

- Auto-running sync from AI rules without user intent.

## Related

- Spec: [issue and milestone documents](../specs/20260719-issue-and-milestone-documents.md)
- Spec: [plan layout and init](../specs/20260719-plan-layout-and-init.md)
- Idea: [init welcome templates](20260719-init-welcome-templates.md)
- Roadmap: [Now / Next / Later](../roadmap/README.md)
- `.plan` issue: #3
