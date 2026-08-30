# Isolated wheel build implementation plan

## Goal

Keep setuptools intermediate artifacts out of the project root while preserving
the existing esim wheel contents and offline wheelhouse behavior.

## Public seams

- `scripts/build-wheel.sh <output-directory>` builds the local project wheel.
- `scripts/build-wheelhouse.sh <output-directory>` continues to build and verify
  the complete offline wheelhouse.
- Distribution tests verify wheel metadata, entry points, dependencies, and that
  local wheel construction does not create or update project-root build
  artifacts.

## Steps

1. Add a failing distribution test for isolated local wheel construction.
2. Add the minimal isolated build entry point and route wheelhouse construction
   through it.
3. Update development and verification documentation.
4. Run affected tests, Ruff checks for changed Python, shell syntax checks, and
   repository hygiene checks.

## GitHub Actions impact

CI retains the same wheel assertions and output. Only setuptools' working source
tree changes from the checkout to a temporary copy, which is removed on exit.
