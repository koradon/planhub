# Interactive config prompts for init

## Status

completed

## Related

- Spec: [interactive config prompts](../specs/20260728-interactive-config-prompts.md)
- ADR: [0007 repository-only configuration](../adr/0007-repository-only-configuration.md)
- Issue: `.plan` issue #26

## Scope

Implements interactive onboarding prompts for `planhub init` and, as a
prerequisite decided during design, removes the global config layer
(`~/.planhub/config.yaml`, `planhub setup`) entirely rather than extending it
— see ADR-0007 for why. Out of scope: enforcing which keys "belong" globally
vs. per-repo (there is no global layer left to enforce that against), and a
`ruamel.yaml`-based comment-preserving writer (deferred; see the spec's
comment-handling requirement instead).

## Steps

1. Refactor `config.py`: extract `default_config_data`, `read_config_file`,
   and a shared `_dump_config_yaml` with no behavior change.
2. Add the merge-safe writer: `_nested_from_dotted`, `_split_leading_comments`,
   `write_config_values`, `write_repo_config_values`.
3. Remove the global layer: delete `ensure_global_config`,
   `_global_config_path`, the global overlay in `load_config`, the
   `planhub setup` command and its Typer entry, and their tests.
4. Change `ensure_repo_config` to write a minimal commented stub instead of a
   full default dump.
5. Add `src/planhub/cli/config_prompts.py`: the four `ConfigQuestion`s,
   `parse_csv_list`, `run_config_prompts`, `config_updates_from_answers`,
   `describe_prompts_dry_run`.
6. Wire `init_command`: run the prompts after `ensure_repo_config`, write via
   `write_repo_config_values`, wrap in `except ConfigError` for resilience,
   couple `--yes`/`-y` to both the config prompts and the omitted-flag skills
   default. Add `--yes`/`-y` to `init_entry` in `app.py`.
7. Update docs: this plan, the new spec and feature file, ADR-0007
   (superseding ADR-0003), the layered-configuration and plan-layout-and-init
   specs, README, and the CLI reference.

## Risks

- Comments below a config file's leading block are stripped on merge-write
  (PyYAML can't round-trip them) — mitigated with a one-line warning and by
  keeping the repo stub itself entirely a leading comment block.
- Removing `~/.planhub/config.yaml` support is a breaking change for anyone
  else who had adopted planhub and set a non-default global value — accepted
  given pre-1.0 status, a single confirmed user, and 0 forks at decision time.
- `ensure_repo_config`'s stub changes what a freshly created config file looks
  like — only affects repos with no existing `.plan/config.yaml`, since
  `_write_if_missing` never overwrites.

## Open Questions

- None outstanding; see the spec's Open Questions for the one deferred design
  question (no per-repo default sharing mechanism to replace the removed
  global layer).
