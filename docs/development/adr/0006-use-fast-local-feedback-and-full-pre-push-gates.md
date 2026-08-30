# ADR-0006: Use fast local feedback and full pre-push gates

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
- Pre-push runs `bash scripts/check.sh`, which remains the single complete local gate.
- Pull-request CI runs the same complete gate as the remote enforcement boundary.
- Full gates may still be run earlier when a user explicitly requests them or risk warrants it.

## Consequences

Local iteration and ordinary agent handoff are faster. Cross-feature, type, documentation,
coverage and dependency failures may surface later at pre-push, so developers must install
both pre-commit and pre-push hooks and treat required PR checks as mandatory.
