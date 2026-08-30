# ADR-0006: Use fast local feedback and full pre-tag gates

## Status

Accepted on 2026-08-22.

## Context

Running the complete pytest, Pyright, documentation, coverage and dependency gates after
every local feature change slows the red-green loop. Local feature work still needs prompt
evidence from the tests that were added or affected and from Python syntax/lint checks.

## Decision

- Local feature completion requires the new and affected pytest cases plus Ruff format/check
  for changed Python files.
- Pre-commit runs only the fast Ruff hooks.
- Local pre-push does not run the complete coverage gate.
- Immediately before creating a release tag, run ash scripts/check.sh, which remains
  the single complete local gate.
- Pull-request CI runs the same complete gate as the remote enforcement boundary.
- Full gates may still be run earlier when a user explicitly requests them or risk warrants it.

## Consequences

Local iteration and ordinary agent handoff are faster. Cross-feature, type, documentation,
coverage and dependency failures may surface in pull-request CI or the pre-tag release
check, so developers must treat required PR checks and the release checklist as mandatory.
