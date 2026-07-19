# Init welcome templates

## Status

draft

## Summary

Extend `planhub init` to create starter milestone/issue Markdown templates with
short usage instructions for new repositories.

## Problem

`init` currently creates empty directories and default configs. New users still
need external docs to learn the first useful issue/milestone shape.

## Audience / value

Repositories adopting Planhub for the first time.

## Options

- Always write a small set of example files (opt-out via flag).
- Write examples only when the layout is brand new and empty.
- Provide `planhub init --templates` as an explicit opt-in.

## Constraints

- Must not overwrite existing user issues/milestones.
- Examples must validate against the document specs.
- Keep examples minimal; link to docs for full reference.

## Explicit no-gos

- Polluting already-populated `.plan/` trees on re-running init.

## Related

- Spec: [plan layout and init](../specs/20260719-plan-layout-and-init.md)
- Idea: [AI rules for planning artifacts](20260719-ai-rules-for-planning-artifacts.md)
- Roadmap: [Now / Next / Later](../roadmap/README.md)
- `.plan` issue: #2
