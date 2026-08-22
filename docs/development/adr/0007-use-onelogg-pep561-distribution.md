# Use the onelogg PEP 561 distribution

The BottiCelle/onelog project now publishes distribution `onelogg` 0.1.2 while
preserving the Python import package `onelog`. This release ships inline type
annotations and an `onelog/py.typed` marker, so downstream projects no longer
need a duplicate local stub.

esim depends on `onelogg>=0.1.2,<0.2`. CI and offline wheelhouse construction use
audited source commit `d60dc49701944d88c90f3bd7fabf5bbbdb7d6f8c`, which is the
commit tagged and published as onelogg 0.1.2. Pyright consumes the installed
package's PEP 561 types directly; the repository does not configure a local
`stubPath` for onelog.

This supersedes only the onelog distribution identity, minimum version, and
fixed-commit details in ADR-0003 and ADR-0004, plus the old distribution name in
ADR-0005. Their logging ownership, CPython 3.11 baseline, quality-toolchain,
PyYAML, and offline wheelhouse decisions remain in force.
