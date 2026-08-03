# Use Python 3.9 with packaged onelog for CLI logging

`ff` and its reusable flattening engine target Python 3.9 or newer; the CLI depends on the versioned `botticelle-onelog` distribution, whose own metadata declares Rich. The CLI owns onelog's global configuration and passes a logger into the engine, while the engine never configures root logging or calls `fatal()`, preserving safe in-process use by `esim`; this supersedes ADR-0002's standard-library-only runtime decision.

The initial supported release is `botticelle-onelog` 0.1.0 at commit
`7738cac48b383624b9b5a6bf3434a2a40210c568`. ff constrains the dependency to
the compatible 0.1 series. Release
bundles contain the onelog, Rich, and ff wheels in one wheelhouse so target
machines can install with `--no-index`. The CLI points onelog's file handler at
a same-directory temporary file and atomically publishes that file only after
success or a controlled failure. Summary output is disabled.
