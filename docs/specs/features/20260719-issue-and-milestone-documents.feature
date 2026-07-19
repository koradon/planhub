Feature: Issue and milestone documents
  Parse and validate Markdown planning files with YAML front matter.

  # Related spec: docs/specs/20260719-issue-and-milestone-documents.md

  Scenario: Issue requires a title
    Given an issue Markdown file whose front matter omits `title`
    When Planhub loads the issue document
    Then loading fails with a document error

  Scenario: Unknown issue state is rejected
    Given an issue file with `state: done`
    When Planhub loads the issue document
    Then loading fails instead of mapping the value to GitHub

  Scenario: Milestone description falls back to body
    Given a milestone file without a `description` key
    And a non-empty Markdown body
    When Planhub loads the milestone document
    Then the document description equals the body text
