# Require Python 3.11 for the quality toolchain

`ff` 0.2.0 and its reusable flattening engine require CPython 3.11 or newer
on Linux and WSL2. Continuous integration covers CPython 3.11 through 3.14.
This supersedes only the Python-version decision in ADR-0003; its packaged
onelog architecture, dependency range, logging ownership, and offline
wheelhouse requirements remain in force.

Python 3.11 is the oldest supported runtime so the project can use one strict,
current linting, type-checking, coverage, and release toolchain without
maintaining compatibility branches for end-of-life interpreters. Raising the
minimum version is a breaking distribution change and therefore ships with
`ff` 0.2.0. Runtime dependencies remain limited to
`botticelle-onelog>=0.1,<0.2`; Node.js and all quality tools are development and
CI dependencies only. The source repository is BottiCelle/onelog, and the fixed
commit declares `Name: botticelle-onelog` so `pip check` and offline installation
resolve the same authoritative distribution identity.
