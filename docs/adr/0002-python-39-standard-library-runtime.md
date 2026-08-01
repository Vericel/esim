---
status: superseded by ADR-0003
---

# Implement ff with Python 3.9 and the standard library

`ff` and its reusable flattening engine target Python 3.9 or newer and have no third-party runtime dependencies. RockyEDA already provides Python 3.9, and file-system access rather than pure parsing is expected to dominate this workload, so easier deployment and direct integration with `esim` outweigh the lower CPU throughput and slower process startup relative to Go or Rust.
