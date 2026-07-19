Feature: Create issue command
  Create a GitHub issue and a matching local root backlog file.

  # Related spec: docs/specs/20260719-create-issue-command.md

  Scenario: Create issue writes local file with GitHub number
    Given a repository with a GitHub remote and valid credentials
    When the user runs `planhub issue "Ship docs"`
    Then a GitHub issue titled "Ship docs" is created
    And a file under `.plan/issues/` contains `number` from GitHub
    And the CLI prints the issue URL and saved path

  Scenario: Missing credentials fail clearly
    Given no `GITHUB_TOKEN`, `GH_TOKEN`, or `gh` session
    When the user runs `planhub issue "Nope"`
    Then the command exits with a non-zero status
    And the output explains how to authenticate
