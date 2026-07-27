# Plan artifact agent skills

## Status

completed

## Related

- Spec: [plan artifact agent skills](../specs/20260727-plan-artifact-agent-skills.md)

## Scope

Implements the spec: a new `planhub.skills` module, a bundled `SKILL.md`
template, and `planhub init` CLI wiring for `--skills`/`--no-skills`. Does
not add a `planhub update`/`upgrade` command — see the spec's Open Questions.

## Steps

1. Add `src/planhub/skills/templates/planhub-plan-artifacts.md` — the
   self-contained skill content (layout, issue/milestone front matter, the
   "don't auto-sync" rule).
2. Add `src/planhub/skills/__init__.py`:
   - `skill_install_paths(repo_root) -> tuple[Path, ...]`
   - `SkillInstallResult` (`created` / `updated` / `unchanged` path tuples)
   - `install_skills(repo_root, *, dry_run=False) -> SkillInstallResult` —
     create-or-update semantics per file.
3. Wire `src/planhub/cli/commands/init/__init__.py`:
   - dry-run branch prints `skill_install_paths`.
   - non-dry-run branch resolves the skills decision (flag / TTY prompt /
     non-TTY default-skip) and calls `install_skills`, echoing
     created/updated/unchanged/skipped.
4. Add `--skills`/`--no-skills` to `init_entry` in `src/planhub/cli/app.py`.
5. Tests:
   - `tests/skills/test_skills.py` for `install_skills`/`skill_install_paths`
     (create, update-on-diff, no-op-when-unchanged, dry-run writes nothing).
   - `tests/commands/test_config_commands.py` additions for the CLI decision
     flow (flag set, flag unset, TTY vs non-TTY, dry-run).
6. Verify packaging: `uv build` and inspect the wheel contains
   `src/planhub/skills/templates/planhub-plan-artifacts.md`; add
   `[tool.hatch.build.targets.wheel] force-include` only if it's missing.
7. Update README `Commands` section for `planhub init` with the new flags.
8. Flip `docs/ideas/20260719-ai-rules-for-planning-artifacts.md` status to
   `accepted`, link the new spec. (Done alongside this plan.)

## Risks

- Overwriting a user's hand-edited `SKILL.md` on `--skills`/a confirmed
  re-run: accepted per explicit user request; content is expected to live in
  git so the diff is visible and revertable.
- `importlib.resources` packaging: templates must ship inside the
  wheel/sdist; verified in step 6 rather than assumed.

## Open Questions

- None currently blocking implementation.
