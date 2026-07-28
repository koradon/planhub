Feature: Interactive config prompts for init
  Ask for common sync defaults during `planhub init`, writing only what changed.

  # Related spec: docs/specs/20260728-interactive-config-prompts.md

  Scenario: Interactive init writes answered values to the repo config
    Given a TTY-attached shell and a repository without .plan/config.yaml
    When the user runs `planhub init` and answers all four prompts
    Then `.plan/config.yaml` contains the answered values
    And no other key in the file is disturbed

  Scenario: Accepting every default on a fresh repo leaves the file untouched
    Given a TTY-attached shell and a freshly created .plan/config.yaml stub
    When the user runs `planhub init` and accepts every default
    Then `.plan/config.yaml` is not rewritten

  Scenario: Existing file values are shown as defaults
    Given a repository config with `sync.github.default_labels: [bug]`
    When the user runs `planhub init` interactively
    Then the labels prompt shows `bug` as its default

  Scenario: --yes skips every prompt and changes nothing
    Given a repository with a repo config already set to non-default values
    When the user runs `planhub init --yes`
    Then no prompts are shown
    And `.plan/config.yaml` is not rewritten

  Scenario: A non-interactive shell skips prompts without --yes
    Given stdin is not a TTY and no `--yes` flag
    When the user runs `planhub init`
    Then no prompts are shown
    And the command exits successfully

  Scenario: --dry-run lists the questions without writing or prompting
    Given any repository
    When the user runs `planhub init --dry-run`
    Then the output lists all four config questions with their current defaults
    And no files are written
    And the user is not prompted

  Scenario: Writing preserves unrelated keys already in the file
    Given a repository config with `sync.closed_issues.archive_dir: custom/dir`
    When the user runs `planhub init` and changes only the verbosity answer
    Then `.plan/config.yaml` still contains `sync.closed_issues.archive_dir: custom/dir`

  Scenario: An invalid enum answer is re-asked, not accepted
    Given a TTY-attached shell
    When the user answers the closed-issues policy prompt with an invalid value
    Then the CLI asks again
    And only `archive` or `delete` is accepted

  Scenario: A pre-existing invalid config file does not abort init
    Given a `.plan/config.yaml` containing an unknown top-level key
    When the user runs `planhub init`
    Then the CLI prints a warning that config prompts were skipped
    And the command still exits successfully

  Scenario: --yes also accepts the default for the omitted skills flag
    Given neither `--skills` nor `--no-skills` was passed
    When the user runs `planhub init --yes`
    Then the Claude/Cursor skill files are installed without a confirmation prompt
