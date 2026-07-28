# Interactive config prompts for init

## Status

accepted

## Summary

`planhub init` interactively prompts for four common sync defaults —
default assignees, default labels, closed-issue policy, and sync verbosity —
writing only what the user actually changes into `.plan/config.yaml` without
disturbing any other key already in that file. Prompts are always skippable:
they auto-skip on a non-interactive shell and can be forced off with
`--yes`/`-y`. There is no global config layer (see
[ADR-0007](../adr/0007-repository-only-configuration.md)); `.plan/config.yaml`
is the only config file planhub reads or writes.

## User stories

- As a first-time user, I want `planhub init` to ask about common settings, so
  that I don't have to know which YAML keys to hand-edit.
- As a scripting/CI user, I want `planhub init` to never block on stdin, so
  that automated runs stay predictable.
- As a returning user, I want prompts to show my current values as defaults,
  so that pressing Enter never changes anything by accident.
- As a reviewer, I want `.plan/config.yaml` to only ever contain keys the
  project deliberately overrides, so that the file is easy to read in a diff.

## Requirements

- Exactly four settings are prompted, in this order: `sync.github.default_assignees`
  (comma-separated), `sync.github.default_labels` (comma-separated),
  `sync.closed_issues.policy` (`archive` | `delete`), `sync.behavior.verbosity`
  (`compact` | `verbose`). `sync.behavior.dry_run` and
  `sync.closed_issues.archive_dir` are intentionally not prompted.
- Each prompt shows the setting's current effective value (from the file if
  already set, otherwise the built-in default) and accepts Enter to keep it.
- Comma-separated answers are trimmed, empty entries dropped, and duplicates
  removed while preserving order.
- Enum prompts re-ask on an invalid answer rather than failing; they never
  accept a value outside the documented choices.
- Prompts run only when stdin is a TTY and `--yes`/`-y` was not passed; both
  conditions independently force the non-interactive path.
- `--yes`/`-y` means "don't ask me; keep current values" — it is never a reset
  to built-in defaults, and on an already-configured repo it is a guaranteed
  no-op write. `--yes` also accepts the default for the `--skills`/`--no-skills`
  prompt when that flag is omitted.
- `--dry-run` prints the paths and the questions that would be asked (with
  their current defaults) and exits without reading stdin or writing files.
- Writing an answer to `.plan/config.yaml` never disturbs any other key
  already in the file, including keys planhub doesn't prompt for.
- An answer is written only if the file already sets that key, or if the
  answer differs from the built-in default — accepting every default on a
  fresh repo leaves the file untouched.
- A pre-existing config file that fails validation does not abort `init`;
  the prompt step is skipped with a warning and the command still exits 0.
- `.plan/config.yaml` is created (if missing) as a minimal commented stub, not
  a full dump of every default — planhub-managed config files are rewritten
  canonically on write, and only that stub's leading comment block is
  preserved; comments elsewhere in the file are not round-tripped, and a
  warning is printed if any would be lost.

## Behavior

`init_command` runs, in order: layout creation, `ensure_repo_config` (writes
the stub if the file is missing), the four prompts (or their skip path), then
the existing skills install step. Prompt logic lives in
`planhub.cli.config_prompts` (`run_config_prompts`, `config_updates_from_answers`,
`describe_prompts_dry_run`) and never touches `sys.stdin` directly — the
command computes `interactive = (not accept_defaults) and sys.stdin.isatty()`
and passes it in, so tests can control interactivity without patching stdin
inside the prompt module.

Writing goes through `planhub.config.write_config_values`: read the file's own
contents, merge the answered subset onto them (never onto built-in defaults),
validate the merged result, and write only if it actually changed. This is
what makes `.plan/config.yaml` minimal and makes `-y` on an unchanged repo a
true no-op.

## Acceptance scenarios (BDD)

See `docs/specs/features/20260728-interactive-config-prompts.feature`.

## Related

- Idea: [interactive config prompts](../ideas/20260719-interactive-config-prompts.md)
- ADR: [0007 repository-only configuration](../adr/0007-repository-only-configuration.md)
  (supersedes [0003](../adr/0003-layered-configuration.md))
- Spec (superseded): [layered configuration](20260719-layered-configuration.md)
- Spec: [plan layout and init](20260719-plan-layout-and-init.md)
- Plan: [interactive config prompts](../plans/20260728-interactive-config-prompts.completed.md)
- Acceptance: `docs/specs/features/20260728-interactive-config-prompts.feature`

## Open Questions

- The global config layer's absence means a developer who wants identical
  defaults across every repo must accept prompts (or pass `-y`) in each one
  individually. Not revisited unless real usage shows this is painful enough
  to justify a different mechanism (e.g. a shell alias wrapping `init -y`
  with flags, rather than a second config file).
