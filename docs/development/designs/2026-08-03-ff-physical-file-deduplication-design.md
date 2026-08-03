# ff Physical File Deduplication Design

## Status

Approved in discussion on 2026-08-03.

## Goal

Prevent VCS from compiling the same physical source file more than once while
keeping every duplicate visible and traceable in the generated flat filelist.

VCS W-2024.09-SP1 was observed parsing an identical source path twice and
emitting `Warning-[OPD] Override previous declaration`; it did not silently
deduplicate the input. ff therefore owns this normalization.

## Scope

Deduplication applies to both compiled-file entry kinds that ff recognizes:

- ordinary source path entries;
- `-v` Verilog library file entries.

Each kind has an independent deduplication domain. The same physical file used
once as an ordinary source and once through `-v` remains active in both forms
because VCS assigns them different semantics.

The following remain unchanged and are not deduplicated directly:

- `-f` and `-F` filelist references;
- `-y` library directories;
- `+incdir+` include directories;
- pass-through simulator options;
- comments and blank lines.

A repeated child filelist is still expanded at every reference. Compiled-file
entries produced by those expansions are then handled by the ordinary source
or `-v` rules.

## Physical Identity and Ordering

After environment expansion, logical absolute-path normalization, existence
checking, type checking, and readability checking, ff obtains a file's physical
identity with `Path.resolve()` and stores it as a string.

The first entry in each deduplication domain remains active at its original
position. Every later entry with the same physical identity is disabled. This
also deduplicates a real path and one or more symlink paths that reach the same
physical file.

All occurrences are validated before duplicate detection. A malformed,
missing, wrong-type, or unreadable later occurrence still fails flattening and
is not hidden by an earlier valid occurrence.

## Flat Filelist Rendering

ff does not silently remove a duplicate. It replaces the duplicate with a
generated explanation followed by the normalized logical entry commented out.

Ordinary source example:

```text
/proj/rtl/top.sv
// ff: duplicate physical source; first: /proj/lists/a.f:12; duplicate: /proj/lists/b.f:27
// /proj/link/top.sv
```

`-v` example:

```text
-v /proj/lib/models.v
// ff: duplicate physical library file; first: /proj/lists/a.f:8; duplicate: /proj/lists/b.f:15
// -v /proj/lib-link/models.v
```

`first` and `duplicate` are absolute `filelist:line` locations. The commented
entry uses the same normalized logical absolute path that would otherwise have
been active.

If the duplicate has a single-line or multiline trailing comment, ff prefixes
every rendered physical line with `// `. No line from a disabled logical entry
may remain active. Independent comments, blank lines, and comments promoted
from `-f` or `-F` references remain unchanged.

The first occurrence of a symlink keeps the existing symlink target annotation
and logical path. A duplicate symlink does not receive a separate symlink target
annotation; its duplicate explanation and commented logical entry replace the
whole active entry.

## Internal Design

The public interface remains unchanged:

```python
flatten_filelist(FlattenRequest(...)) -> FlattenResult
```

Each call creates one private flattening state shared by recursive filelist
expansion:

```python
@dataclass
class _FlattenState:
    input_filelists: dict[Path, Path]
    seen_sources: dict[str, str]
    seen_library_files: dict[str, str]
```

The two `seen_*` mappings contain physical absolute-path strings mapped to the
first absolute `filelist:line` location. No per-file state object or general
structured flat-entry hierarchy is introduced.

Duplicate detection happens immediately before an already validated source or
`-v` entry would be emitted. This keeps conditional parsing, recursive
filelist expansion, environment expansion, and path validation independent of
the output policy while avoiding a second parse of the final text.

## Logging

When a logger is supplied, every disabled duplicate produces a DEBUG message
containing:

- entry kind;
- physical identity;
- first location;
- duplicate location;
- duplicate logical entry.

The generated flat-filelist comments are unconditional and do not depend on
`--debug`. Existing CLI log-level and `-l/--log` behavior remains unchanged.

## Complexity

The algorithm is O(n) in compiled-file entries. The retained state is O(u),
where `u` is the number of unique physical ordinary-source and `-v` files.

Using string keys and string locations measured approximately 1.85 MiB for
10,000 representative entries in the project's Python environment. Only one
`_FlattenState` instance exists per flatten operation.

## TDD and Verification

Tests exercise only the agreed public seam:

```python
flatten_filelist(FlattenRequest(...))
```

They observe the published flat filelist and DEBUG messages through the logger
accepted by `FlattenRequest`. Private state and helpers are not tested directly.

Implementation proceeds in vertical RED-GREEN slices:

1. repeated ordinary source entries become traceable comments;
2. a symlink and real path to the same ordinary source are deduplicated;
3. repeated `-v` entries become traceable comments;
4. ordinary source and `-v` domains remain independent;
5. multiline trailing comments are safely disabled and DEBUG provenance is
   reported.

After the focused tests pass, run the complete engine, CLI, and distribution
test suite and update the requirements and HTML User Guide to replace the old
"duplicates are preserved" contract.

## Non-goals

- Detecting files that merely share a basename.
- Parsing HDL declarations to detect duplicate modules, packages, interfaces,
  classes, or other language-level definitions.
- Deduplicating arbitrary simulator options or directories.
- Adding CLI switches to enable or disable deduplication.
- Changing the ff/esim public interface.
