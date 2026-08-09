# Use PyYAML for esim configuration

This decision supersedes the sentence in ADR-0004 that limited runtime
dependencies to `botticelle-onelog`. It does not change ADR-0004's Python 3.11
baseline, quality toolchain, logging ownership, or offline wheelhouse decisions.

esim uses `PyYAML>=6.0,<7` as a runtime dependency to parse TC/Rules files and
serialize resolved configuration and result snapshots. All source loads use
`safe_load`, and generated YAML uses `safe_dump`; arbitrary Python object tags
are never enabled.

The Python 3.11 standard library has no YAML parser. A project-specific YAML
subset would contradict the accepted requirement that `.tc`, `.rules`, and
`.yaml` files use standard YAML syntax, while implementing and maintaining a
complete parser would add substantial correctness and security risk. PyYAML 6.x
supports the project's CPython 3.11+ baseline and is included in the offline
wheelhouse alongside esim, botticelle-onelog, and Rich.

The dependency is constrained to the compatible 6.x series. Changing the
library or its supported major range requires a new dependency decision and the
same installation, offline-release, requirement, and user-documentation audit.
