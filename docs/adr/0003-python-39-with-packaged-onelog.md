# Use Python 3.9 with packaged onelog for CLI logging

`ff` and its reusable flattening engine target Python 3.9 or newer; the CLI uses a versioned, installable release of `BottiCelle/onelog` and its Rich dependency, distributed with ff/esim so target machines do not need network installation. The CLI owns onelog's global configuration and passes a logger into the engine, while the engine never configures root logging or calls `fatal()`, preserving safe in-process use by `esim`; this supersedes ADR-0002's standard-library-only runtime decision.
