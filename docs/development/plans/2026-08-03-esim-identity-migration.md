# esim Identity Migration Implementation Plan

**Goal:** Rename the Python distribution and project identity to esim, preserve the
standalone ff command, consume the clean BottiCelle/onelog distribution metadata, and
remove the retired personal distribution name from controlled text, artifacts, and
Git history.

**Public seams:** Built wheel metadata, installed console entry points, `ff --help`,
offline installation, and reachable Git objects.

## 1. Establish red distribution tests

1. Change the distribution assertions to require `Name: esim` and
   `Requires-Dist: botticelle-onelog<0.2,>=0.1`.
2. Require the wheel to expose the standalone `ff` console entry point.
3. Run only the new distribution test and record the expected failure.

## 2. Migrate project and dependency metadata

1. Change `[project].name` to `esim` and the runtime dependency to
   `botticelle-onelog>=0.1,<0.2`.
2. Keep `ff = "ff.cli:main"`; do not add an incomplete esim entry point.
3. Pin source builds to the audited clean BottiCelle/onelog commit.
4. Make the focused distribution test pass.

## 3. Synchronize authoritative documentation

1. Update README, requirements, user guide, development guide, verification matrix,
   release checklist, changelog, plans and affected ADRs.
2. Describe esim as the product and ff as its independently executable filelist
   preprocessing component.
3. Document centralized offline installation through a versioned prefix and
   PATH/modulefile.

## 4. Restrict wheelhouse to release/manual execution

1. Remove the wheelhouse job from ordinary pull-request and main-push execution.
2. Keep a manually dispatchable/release path that builds, installs with
   `--no-index`, smoke-tests `ff`, uploads the archive, and publishes checksums.
3. Keep normal wheel construction and installation evidence in ordinary CI.

## 5. Verify source and artifacts

1. Run focused distribution and documentation tests.
2. Run the full project check and test suite.
3. Build the wheel and wheelhouse, inspect metadata and archive contents.
4. Search current source and generated artifacts for the retired name.

## 6. Rewrite histories with recovery points

1. Create local mirror backups outside both repositories.
2. Rewrite all controlled local refs so file snapshots and commit metadata no longer
   contain the retired name.
3. Verify every reachable object and checkout.
4. Force-update BottiCelle/onelog remote refs only after explicit approval of the
   public-history rewrite; do not publish esim without an explicit push request.
