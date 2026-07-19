# Interactive config prompts for setup and init

## Status

draft

## Summary

Add skippable interactive prompts during `planhub setup` and `planhub init` so
users can set common defaults without hand-editing YAML.

## Problem

Onboarding currently creates default config files, but users must know which
keys to edit for assignees, labels, closed-issue policy, and verbosity.

## Audience / value

First-time Planhub users setting global or repository defaults.

## Options

- Prompt only in `setup` (global), leave repo config manual.
- Prompt in both `setup` and `init`, with an init question about also updating
  global config.
- Ship a separate `planhub config` wizard command.

## Constraints

- Prompts must be skippable and show current/default values.
- Non-interactive environments (CI, redirected stdin) must skip prompts
  automatically or via flags.
- Must not overwrite unrelated existing keys unexpectedly.

## Explicit no-gos

- Requiring interactivity for basic `init`/`setup` success in scripts.

## Related

- Spec: [layered configuration](../specs/20260719-layered-configuration.md)
- ADR: [0003 layered configuration](../adr/0003-layered-configuration.md)
- Roadmap: [Now / Next / Later](../roadmap/README.md)
- `.plan` issue: #26
