# ff Physical File Deduplication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make ff disable repeated physical ordinary-source and `-v` files with traceable comments so VCS compiles each physical file at most once per entry kind.

**Architecture:** Keep `flatten_filelist(FlattenRequest)` unchanged. One private `_FlattenState` travels through recursive expansion and records first occurrences; duplicate detection runs only after normal path validation and immediately before output emission. Ordinary sources and `-v` files use independent identity maps.

**Tech Stack:** Python 3.9+, `pathlib`, dataclasses, pytest, standalone HTML documentation.

## Global Constraints

- Follow the approved design in `docs/development/designs/2026-08-03-ff-physical-file-deduplication-design.md`.
- Test only through `flatten_filelist(FlattenRequest(...))`; do not test private helpers or `_FlattenState` directly.
- Use `Path.resolve()` physical identity stored as `str`; preserve the first logical entry and order.
- Validate every occurrence before duplicate detection.
- Ordinary sources and `-v` library files are independent deduplication domains.
- Duplicate entries become unconditional two-part comments: explanation, then every rendered entry line prefixed by `// `.
- Do not deduplicate `-f/-F`, `-y`, `+incdir+`, pass-through options, comments, or blank lines.
- Keep Python 3.9 compatibility and do not change the public ff/esim interface.
- Preserve the unrelated untracked `.tmp_ff_vcs_duplicate_define/` directory.

## File Structure

- Modify `src/ff/__init__.py`: private per-run state, duplicate rendering, source and `-v` emission policy, DEBUG provenance.
- Modify `tests/test_engine.py`: public-seam RED-GREEN tests for each behavior slice.
- Modify `docs/requirements/ff.md`: replace the old duplicate-preservation contract.
- Modify `docs/user/ff-user-guide.html`: explain physical deduplication and show output examples.
- Modify `CONTEXT.md`: define physical compiled-file identity and duplicate annotation vocabulary.

---

### Task 1: Comment repeated ordinary source entries

**Files:**
- Modify: `tests/test_engine.py:622`
- Modify: `src/ff/__init__.py:278-285, 506-538, 671-706, 787-796`

**Interfaces:**
- Consumes: `flatten_filelist(request: FlattenRequest) -> FlattenResult`.
- Produces: private `_FlattenState` shared across recursive `_flatten_lines()` calls and ordinary-source duplicate comments.

- [ ] **Step 1: Replace the old preservation test with a failing public-seam test**

Use a direct two-line filelist so first and duplicate origins are unambiguous:

```python
def test_repeated_source_is_commented_after_first_occurrence(tmp_path: Path) -> None:
    from ff import FlattenRequest, flatten_filelist

    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("top.sv\ntop.sv\n", encoding="utf-8")

    result = flatten_filelist(
        FlattenRequest(top_filelist=top_filelist, working_directory=tmp_path)
    )

    assert result.output_filelist.read_text(encoding="utf-8") == (
        f"{source}\n"
        "// ff: duplicate physical source; "
        f"first: {top_filelist}:1; duplicate: {top_filelist}:2\n"
        f"// {source}\n"
    )
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
.venv/bin/pytest -q tests/test_engine.py::test_repeated_source_is_commented_after_first_occurrence
```

Expected: FAIL because the current engine emits the active source twice.

- [ ] **Step 3: Add the minimal per-run state and source emission check**

Add a private mutable state while keeping `FlattenRequest` frozen and public:

```python
@dataclass
class _FlattenState:
    input_filelists: dict[Path, Path]
    seen_sources: dict[str, str] = field(default_factory=dict)
```

Replace `_flatten_lines(..., input_filelists)` with `_flatten_lines(..., state)` and use `state.input_filelists` at the existing input-filelist conflict sites. Construct one state in `flatten_filelist()` and pass the same instance through every recursive call.

Immediately before ordinary-source annotation/emission, use the normalized logical path string for this first slice:

```python
origin = f"{filelist}:{line_number}"
identity = str(resolved_source)
first_origin = state.seen_sources.get(identity)
if first_origin is not None:
    flattened_lines.extend(
        [
            "// ff: duplicate physical source; "
            f"first: {first_origin}; duplicate: {origin}",
            f"// {rendered_source}",
        ]
    )
    continue
state.seen_sources[identity] = origin
```

Build `rendered_source` before this check, but keep symlink annotation emission after it so duplicates cannot leave orphan annotations.

- [ ] **Step 4: Run the focused test and verify GREEN**

Run the focused test from Step 2. Expected: PASS.

- [ ] **Step 5: Run nearby recursion and source-rendering tests**

Run:

```bash
.venv/bin/pytest -q tests/test_engine.py -k 'recursive_filelist or source_trailing_comment or symlinked_source'
```

Expected: PASS except any old test whose asserted duplicate-preservation contract must be replaced by Step 1.

- [ ] **Step 6: Commit the slice**

```bash
git add src/ff/__init__.py tests/test_engine.py
git commit -m "feat: comment repeated source entries"
```

---

### Task 2: Deduplicate symlink aliases by physical identity

**Files:**
- Modify: `tests/test_engine.py` near the ordinary duplicate test
- Modify: `src/ff/__init__.py` ordinary-source identity calculation

**Interfaces:**
- Consumes: `_FlattenState.seen_sources: dict[str, str]` from Task 1.
- Produces: physical ordinary-source identity through `str(resolved_source.resolve())`.

- [ ] **Step 1: Write a failing symlink-alias test**

```python
def test_symlink_and_real_source_share_physical_duplicate_identity(
    tmp_path: Path,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    physical = tmp_path / "physical" / "top.sv"
    physical.parent.mkdir()
    physical.write_text("module top; endmodule\n", encoding="utf-8")
    logical = tmp_path / "logical" / "top.sv"
    logical.parent.mkdir()
    logical.symlink_to(physical)
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("logical/top.sv\nphysical/top.sv\n", encoding="utf-8")

    result = flatten_filelist(
        FlattenRequest(top_filelist=top_filelist, working_directory=tmp_path)
    )

    assert result.output_filelist.read_text(encoding="utf-8") == (
        f"// symlink target: {physical}\n"
        f"{logical}\n"
        "// ff: duplicate physical source; "
        f"first: {top_filelist}:1; duplicate: {top_filelist}:2\n"
        f"// {physical}\n"
    )
```

- [ ] **Step 2: Run the focused test and verify RED**

Run the new test. Expected: FAIL because Task 1 compares logical paths.

- [ ] **Step 3: Make the minimal physical-identity change**

Change only the ordinary-source key:

```python
identity = str(resolved_source.resolve())
```

- [ ] **Step 4: Run both ordinary-source duplicate tests and verify GREEN**

Run both tests by exact node ID. Expected: PASS.

- [ ] **Step 5: Commit the slice**

```bash
git add src/ff/__init__.py tests/test_engine.py
git commit -m "feat: deduplicate physical source aliases"
```

---

### Task 3: Add an independent `-v` deduplication domain

**Files:**
- Modify: `tests/test_engine.py` near `test_v_library_file_is_expanded_and_rendered_as_absolute`
- Modify: `src/ff/__init__.py:541-577`

**Interfaces:**
- Consumes: `_FlattenState` and duplicate comment convention from Tasks 1-2.
- Produces: `_FlattenState.seen_library_files: dict[str, str]`; ordinary source and `-v` physical domains remain independent.

- [ ] **Step 1: Write a failing test covering `-v` duplication and cross-domain preservation**

Create one physical file and one symlink alias. Put the physical file first as an ordinary source, then as `-v`, then put the alias as a second `-v` entry:

```python
def test_v_files_deduplicate_separately_from_ordinary_sources(tmp_path: Path) -> None:
    from ff import FlattenRequest, flatten_filelist

    library = tmp_path / "models.v"
    library.write_text("module model; endmodule\n", encoding="utf-8")
    alias = tmp_path / "alias.v"
    alias.symlink_to(library)
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("models.v\n-v models.v\n-v alias.v\n", encoding="utf-8")

    result = flatten_filelist(
        FlattenRequest(top_filelist=top_filelist, working_directory=tmp_path)
    )

    assert result.output_filelist.read_text(encoding="utf-8") == (
        f"{library}\n"
        f"-v {library}\n"
        "// ff: duplicate physical library file; "
        f"first: {top_filelist}:2; duplicate: {top_filelist}:3\n"
        f"// -v {alias}\n"
    )
```

- [ ] **Step 2: Run the focused test and verify RED**

Expected: FAIL because both `-v` entries remain active and the alias gets a symlink annotation.

- [ ] **Step 3: Implement the independent library-file map**

Add to `_FlattenState`:

```python
seen_library_files: dict[str, str] = field(default_factory=dict)
```

After the existing `-v` validation and after constructing `rendered_library`, but before symlink annotation emission:

```python
origin = f"{filelist}:{line_number}"
identity = str(library_file.resolve())
first_origin = state.seen_library_files.get(identity)
if first_origin is not None:
    flattened_lines.extend(
        [
            "// ff: duplicate physical library file; "
            f"first: {first_origin}; duplicate: {origin}",
            f"// {rendered_library}",
        ]
    )
    continue
state.seen_library_files[identity] = origin
```

Do not read or write `seen_sources` in this branch.

- [ ] **Step 4: Run the focused `-v` test and ordinary-source duplicate tests**

Expected: all PASS.

- [ ] **Step 5: Run all existing path-option tests**

```bash
.venv/bin/pytest -q tests/test_engine.py -k 'library_file or library_directory or incdir'
```

Expected: PASS.

- [ ] **Step 6: Commit the slice**

```bash
git add src/ff/__init__.py tests/test_engine.py
git commit -m "feat: deduplicate physical library files"
```

---

### Task 4: Safely comment multiline duplicate entries

**Files:**
- Modify: `tests/test_engine.py` near multiline block-comment tests
- Modify: `src/ff/__init__.py` duplicate rendering helper and both duplicate branches

**Interfaces:**
- Consumes: rendered ordinary-source and `-v` logical entries.
- Produces: `_comment_duplicate(kind: str, first_origin: str, duplicate_origin: str, rendered_entry: str) -> list[str]`.

- [ ] **Step 1: Write a failing multiline duplicate test**

```python
def test_multiline_trailing_comment_is_fully_commented_on_duplicate(
    tmp_path: Path,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text(
        "top.sv\n"
        "top.sv /* duplicate from\n"
        "          integration */\n",
        encoding="utf-8",
    )

    result = flatten_filelist(
        FlattenRequest(top_filelist=top_filelist, working_directory=tmp_path)
    )

    assert result.output_filelist.read_text(encoding="utf-8") == (
        f"{source}\n"
        "// ff: duplicate physical source; "
        f"first: {top_filelist}:1; duplicate: {top_filelist}:2\n"
        f"// {source} /* duplicate from\n"
        "//           integration */\n"
    )
```

- [ ] **Step 2: Run the focused test and verify RED**

Expected: FAIL because the continuation line is not prefixed with `// `.

- [ ] **Step 3: Centralize safe duplicate rendering**

```python
def _comment_duplicate(
    kind: str,
    first_origin: str,
    duplicate_origin: str,
    rendered_entry: str,
) -> list[str]:
    explanation = (
        f"// ff: duplicate physical {kind}; "
        f"first: {first_origin}; duplicate: {duplicate_origin}"
    )
    return [explanation, *(f"// {line}" for line in rendered_entry.splitlines())]
```

Use `kind="source"` in the ordinary branch and `kind="library file"` in the `-v` branch. Replace both inline two-line lists with this helper.

- [ ] **Step 4: Run multiline, ordinary-source, symlink, and `-v` tests**

Expected: all PASS.

- [ ] **Step 5: Commit the slice**

```bash
git add src/ff/__init__.py tests/test_engine.py
git commit -m "feat: safely comment multiline duplicates"
```

---

### Task 5: Report duplicate provenance through DEBUG

**Files:**
- Modify: `tests/test_engine.py` near duplicate tests
- Modify: `src/ff/__init__.py` duplicate branches or a private logging helper

**Interfaces:**
- Consumes: `FlattenRequest.logger` with `debug(message: str) -> None`.
- Produces: one exact DEBUG event per disabled duplicate.

- [ ] **Step 1: Write a failing logger test through `FlattenRequest`**

```python
def test_duplicate_source_reports_physical_and_origin_debug_trace(
    tmp_path: Path,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    class RecordingLogger:
        def __init__(self) -> None:
            self.messages: list[str] = []

        def debug(self, message: str) -> None:
            self.messages.append(message)

    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("top.sv\ntop.sv\n", encoding="utf-8")
    logger = RecordingLogger()

    flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
            logger=logger,
        )
    )

    assert (
        "skipping duplicate physical source: "
        f"identity={source}; first={top_filelist}:1; "
        f"duplicate={top_filelist}:2; entry={source}"
    ) in logger.messages
```

- [ ] **Step 2: Run the focused test and verify RED**

Expected: FAIL because only source-resolution messages exist.

- [ ] **Step 3: Add the minimal DEBUG event**

When a duplicate is found and `request.logger` is present, emit the exact message asserted above. For `-v`, use `physical library file` as the kind and include the rendered `-v` entry. Keep flat-filelist comments unconditional.

- [ ] **Step 4: Run duplicate tests and verify GREEN**

Expected: all duplicate tests PASS.

- [ ] **Step 5: Run all engine tests**

```bash
.venv/bin/pytest -q tests/test_engine.py
```

Expected: PASS.

- [ ] **Step 6: Commit the slice**

```bash
git add src/ff/__init__.py tests/test_engine.py
git commit -m "feat: trace duplicate file provenance"
```

---

### Task 6: Update the behavior contract and user documentation

**Files:**
- Modify: `CONTEXT.md`
- Modify: `docs/requirements/ff.md:154-178`
- Modify: `docs/user/ff-user-guide.html:976-982`

**Interfaces:**
- Consumes: final output and DEBUG behavior from Tasks 1-5.
- Produces: authoritative terminology and user-facing rules consistent with the implementation.

- [ ] **Step 1: Update domain vocabulary**

Add concise definitions to `CONTEXT.md`:

- **Physical compiled-file identity**: `Path.resolve()` identity used only within an entry kind.
- **Duplicate file annotation**: generated comments that explain first/duplicate origins and comment out the later normalized logical entry.

- [ ] **Step 2: Replace the old requirements rule**

Replace “重复源码或选项保留原顺序和次数，不自动去重” with exact rules:

- repeated child filelists still expand at every reference;
- ordinary sources and `-v` files deduplicate separately by physical identity;
- first occurrence stays active and later occurrences become traceable comments;
- all occurrences validate before deduplication;
- other options and directories preserve order and repetitions;
- DEBUG reports physical identity and both origins.

- [ ] **Step 3: Update the HTML User Guide**

Rewrite the “循环与重复” list and include one ordinary-source output example showing the explanation and commented duplicate. Keep the page standalone with no scripts or external resources.

- [ ] **Step 4: Verify documentation**

```bash
xmllint --noout docs/user/ff-user-guide.html
rg -n "重复源码和选项也保留|不自动去重" CONTEXT.md docs/requirements/ff.md docs/user/ff-user-guide.html
git diff --check
```

Expected: XML validation passes, obsolete rules produce no matches, and `git diff --check` is clean.

- [ ] **Step 5: Commit the documentation**

```bash
git add CONTEXT.md docs/requirements/ff.md docs/user/ff-user-guide.html
git commit -m "docs: document physical file deduplication"
```

---

### Task 7: Full verification

**Files:**
- Verify only; modify files only if a failing test reveals a requirement defect.

**Interfaces:**
- Consumes: all implementation and documentation tasks.
- Produces: evidence that the merged public behavior and distribution remain healthy.

- [ ] **Step 1: Run Python compilation and the full test suite**

```bash
.venv/bin/python -m compileall -q src
.venv/bin/pytest -q
```

Expected: compilation succeeds and all tests pass.

- [ ] **Step 2: Verify HTML and repository hygiene**

```bash
xmllint --noout docs/user/ff-user-guide.html
git diff --check
git status --short --branch
```

Expected: HTML and diff checks pass. Only the pre-existing unrelated `.tmp_ff_vcs_duplicate_define/` may remain untracked.

- [ ] **Step 3: Review the final diff against the spec**

Confirm:

- no public interface change;
- separate ordinary-source and `-v` maps;
- physical `resolve()` identity;
- first occurrence active;
- later entries fully commented;
- no orphan symlink annotation;
- all occurrences validated first;
- exact DEBUG provenance;
- documentation no longer claims compiled-file duplicates remain active.
