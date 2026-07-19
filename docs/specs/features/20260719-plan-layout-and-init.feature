Feature: Plan layout and init
  Initialize a standard .plan directory so planning files can sync to GitHub.

  # Related spec: docs/specs/20260719-plan-layout-and-init.md

  Scenario: Init creates the plan layout and default configs
    Given a git repository without a .plan directory
    When the user runs `planhub init`
    Then `.plan/issues` and `.plan/milestones` exist
    And `.plan/config.yaml` exists if it was missing
    And `~/.planhub/config.yaml` exists if it was missing

  Scenario: Init dry-run does not write files
    Given a git repository without a .plan directory
    When the user runs `planhub init --dry-run`
    Then the CLI lists the paths that would be created
    And no `.plan` directory is created

  Scenario: Sync requires an initialized layout
    Given a repository without a `.plan` directory
    When the user runs `planhub sync`
    Then the command exits with a non-zero status
    And the output tells the user to run `planhub init`
