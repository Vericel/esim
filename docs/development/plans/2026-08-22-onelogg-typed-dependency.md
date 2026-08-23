# onelogg typed dependency migration plan

## Goal

Consume the published `onelogg` 0.1.2 distribution and its PEP 561 inline types,
then remove esim's duplicate `typings/onelog.pyi` stub without weakening type
checking or offline release verification.

## Confirmed public seams

- A built esim wheel declares `onelogg>=0.1.2,<0.2` in its metadata.
- CI and the offline wheelhouse consume the audited onelog commit
  `d60dc49701944d88c90f3bd7fabf5bbbdb7d6f8c` that produced 0.1.2.
- Strict source and basic test/script Pyright checks pass without a local stub path.
- Offline installation continues to provide working `ff` and `esim` entry points.

## Implementation

1. Update the distribution test first and record the expected metadata failure.
2. Change the runtime dependency and fixed onelog commit, then make the focused
   distribution test pass.
3. Remove `typings/onelog.pyi` and `stubPath`; remove the retired directory from
   Ruff entry points and prove both Pyright projects pass against onelogg 0.1.2.
4. Synchronize CI, wheelhouse, README, requirements-facing documentation, ADRs,
   verification guidance, release checklist, and changelog.
5. Run focused tests, affected Ruff checks, documentation checks, `pip check`,
   `git diff --check`, and inspect the final worktree without disturbing unrelated
   user changes.
