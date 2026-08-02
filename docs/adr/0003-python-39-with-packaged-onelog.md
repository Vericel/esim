# Use Python 3.9 with packaged onelog for CLI logging

`ff` and its reusable flattening engine target Python 3.9 or newer; the CLI uses a fixed vendored copy of `BottiCelle/onelog` and declares its Rich dependency, so onelog itself does not need a separate network installation on target machines. The CLI owns onelog's global configuration and passes a logger into the engine, while the engine never configures root logging or calls `fatal()`, preserving safe in-process use by `esim`; this supersedes ADR-0002's standard-library-only runtime decision.

The upstream repository currently has no tag or Python packaging metadata. `ff`
therefore vendors `onelog.py` at commit
`dd41f9ac9772d9aa9d69a8a40c4ebe9420db6163`, records that identity in
`ff._vendor`, and declares Rich as a wheel runtime dependency. The CLI points
onelog's file handler at a same-directory temporary file and atomically publishes
that file only after success or a controlled failure. Summary output is disabled.
