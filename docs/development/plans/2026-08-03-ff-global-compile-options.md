# ff Global Compile Options Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `-d/--define` select filelist branches and emit matching HDL defines, then stably group command-line defines, filelist defines, include directories, and all remaining content in that order.

**Architecture:** Keep the public `FlattenRequest` and `flatten_filelist()` interfaces unchanged. Internally, replace the single flattened line list with categorized rendered sections so nested filelists contribute to one global stable ordering and comments or symlink annotations owned by an `+incdir+` entry move with it. Render sorted command-line defines before the categorized filelist sections.

**Tech Stack:** Python 3.9+, `dataclasses`, `pathlib`, pytest, argparse CLI integration tests, static HTML documentation.

## Global Constraints

- `-d STUB_XXX` both selects custom filelist conditional branches and emits `+define+STUB_XXX` for VCS.
- Output order is command-line defines, original filelist defines, include directories, then all remaining effective content.
- Preserve original order and duplicates inside every filelist-derived group.
- Do not deduplicate a command-line-generated define against an original filelist define.
- Command-line macro input retains its existing set semantics and is rendered in ascending name order.
- Move `+incdir+` trailing comments and symlink annotations with the corresponding include-directory group.
- Standalone comments and blank lines remain in the remaining-content group.
- Tests observe only `flatten_filelist()` and the real `ff` CLI.
- Do not create Git commits and do not push to GitHub.

---

### Task 1: Emit command-line macros as HDL defines

**Files:**
- Modify: `tests/test_engine.py`
- Modify: `tests/test_cli.py`
- Modify: `src/ff/__init__.py`

**Interfaces:**
- Consumes: `FlattenRequest.predefined_macros: FrozenSet[str]` and CLI `-d/--define`.
- Produces: one leading `+define+MACRO` line per unique predefined macro, sorted by macro name.

- [ ] **Step 1: Write the failing engine test**

Replace `test_ifdef_keeps_branch_for_predefined_macro` with an explicit
dual-semantics assertion using two names whose required output order is visible:

```python
def test_predefined_macros_select_branches_and_render_sorted_hdl_defines(
    tmp_path: Path,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    source = tmp_path / "fpga.sv"
    source.write_text("module fpga; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text(
        "`ifdef FPGA\n"
        "fpga.sv\n"
        "`endif\n",
        encoding="utf-8",
    )

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
            predefined_macros=frozenset({"Z_TRACE", "FPGA"}),
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == (
        "+define+FPGA\n"
        "+define+Z_TRACE\n"
        f"{source}\n"
    )
```

Update the existing ASIC conditional test expectation to begin with
`+define+ASIC\n`. Do not change the invalid `WIDTH=32` test because invalid
macros must still fail before any output is published.

- [ ] **Step 2: Run the engine tests to verify red**

Run:

```bash
pytest -q tests/test_engine.py::test_predefined_macros_select_branches_and_render_sorted_hdl_defines
```

Expected: FAIL because the current output contains only the selected source path.

- [ ] **Step 3: Add the minimal engine rendering**

In `flatten_filelist()`, after macro validation and `_flatten_lines()` succeeds,
prepend command-line defines without changing the parser:

```python
command_line_defines = [
    f"+define+{macro}" for macro in sorted(request.predefined_macros)
]
flattened_lines = command_line_defines + flattened_lines
```

Place this before top-level output serialization. Keep validation before any
file creation so `WIDTH=32` behavior remains unchanged.

- [ ] **Step 4: Verify engine green and expose the CLI behavior**

Run:

```bash
pytest -q tests/test_engine.py::test_predefined_macros_select_branches_and_render_sorted_hdl_defines tests/test_engine.py::test_elsif_keeps_first_matching_alternative_branch
```

Expected: PASS after updating both literal expectations.

Update `test_cli_define_option_selects_all_named_macro_branches` so its expected
file is:

```python
(
    "+define+FPGA\n"
    "+define+USE_DDR\n"
    f"{fpga_source}\n"
    f"{ddr_source}\n"
)
```

This existing subprocess test is the agreed real-CLI seam and proves that CLI
parsing reaches engine rendering.

- [ ] **Step 5: Run the Task 1 public-seam tests**

Run:

```bash
pytest -q tests/test_engine.py tests/test_cli.py::test_cli_define_option_selects_all_named_macro_branches
```

Expected: all selected tests PASS.

---

### Task 2: Stably promote original filelist defines

**Files:**
- Modify: `tests/test_engine.py`
- Modify: `src/ff/__init__.py`

**Interfaces:**
- Consumes: effective logical entries returned after condition and nested-filelist expansion.
- Produces: command-line defines followed by all original `+define+...` entries in expanded source order, including duplicates.

- [ ] **Step 1: Write the failing grouping test**

Add this public-engine test near the existing simulator pass-through tests:

```python
def test_filelist_defines_are_promoted_after_command_line_defines_stably(
    tmp_path: Path,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    first = tmp_path / "first.sv"
    first.write_text("module first; endmodule\n", encoding="utf-8")
    second = tmp_path / "second.sv"
    second.write_text("module second; endmodule\n", encoding="utf-8")
    child = tmp_path / "child.f"
    child.write_text(
        "second.sv\n"
        "+define+STUB_XXX // from child\n",
        encoding="utf-8",
    )
    top = tmp_path / "top.f"
    top.write_text(
        "first.sv\n"
        "+define+TOP_MODE\n"
        "-F child.f\n"
        "+define+STUB_XXX\n",
        encoding="utf-8",
    )

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top,
            working_directory=tmp_path,
            predefined_macros=frozenset({"STUB_XXX"}),
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == (
        "+define+STUB_XXX\n"
        "+define+TOP_MODE\n"
        "+define+STUB_XXX // from child\n"
        "+define+STUB_XXX\n"
        f"{first}\n"
        f"{second}\n"
    )
```

This literal independently specifies command-line-first order, nested stable
order, inline-comment preservation, and no cross-source deduplication.

- [ ] **Step 2: Run the grouping test to verify red**

Run:

```bash
pytest -q tests/test_engine.py::test_filelist_defines_are_promoted_after_command_line_defines_stably
```

Expected: FAIL because original defines remain interleaved with sources.

- [ ] **Step 3: Introduce categorized flattened sections**

Add a private mutable accumulator next to the existing private helpers:

```python
@dataclass
class _FlattenedSections:
    defines: list[str] = field(default_factory=list)
    incdirs: list[str] = field(default_factory=list)
    others: list[str] = field(default_factory=list)

    def extend(self, child: "_FlattenedSections") -> None:
        self.defines.extend(child.defines)
        self.incdirs.extend(child.incdirs)
        self.others.extend(child.others)

    def render(self, predefined_macros: FrozenSet[str]) -> list[str]:
        return (
            [f"+define+{macro}" for macro in sorted(predefined_macros)]
            + self.defines
            + self.incdirs
            + self.others
        )
```

Change `_flatten_lines()` to return `_FlattenedSections`. Replace its local
`flattened_lines` with `sections`. For this slice:

- active `+define+...` pass-through entries append their original `line` to
  `sections.defines`;
- recursive child results use `sections.extend(child_sections)`;
- blank lines, standalone comments, `-f/-F` promoted comments and annotations,
  `-v/-y` rendered entries and annotations, generic pass-through options,
  source entries and source annotations append to `sections.others` in the same
  places where they currently append to `flattened_lines`;
- incdir output temporarily also targets `sections.others`, preserving behavior
  until Task 3.

At the end of `flatten_filelist()`, insert a top-filelist symlink annotation at
the beginning of `sections.others`, then call:

```python
flattened_lines = sections.render(request.predefined_macros)
```

Remove the temporary Task 1 list concatenation so command-line defines are
emitted exactly once.

- [ ] **Step 4: Run the grouping and regression tests**

Run:

```bash
pytest -q tests/test_engine.py::test_filelist_defines_are_promoted_after_command_line_defines_stably tests/test_engine.py::test_unknown_simulator_options_pass_through_without_defining_ff_macros tests/test_engine.py::test_repeated_filelist_references_and_sources_are_not_deduplicated
```

Expected: PASS. The unknown-options test input already places `+define+FPGA`
before `-sverilog` and the source, so its literal output remains unchanged. It
must still prove that an original `+define+FPGA` does not select the ff
conditional branch.

- [ ] **Step 5: Run the complete engine suite**

Run:

```bash
pytest -q tests/test_engine.py
```

Expected: PASS with no source-order, comment, symlink, path, or atomic-output regressions.

---

### Task 3: Stably promote include directories with owned annotations

**Files:**
- Modify: `tests/test_engine.py`
- Modify: `src/ff/__init__.py`

**Interfaces:**
- Consumes: each validated `+incdir+` logical entry and its expanded directories.
- Produces: all include-directory entry groups after original defines and before remaining content.

- [ ] **Step 1: Write the failing incdir ownership test**

Add a test that forces both comment and symlink annotation ownership:

```python
def test_incdirs_are_promoted_with_comments_and_symlink_annotations(
    tmp_path: Path,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    physical = tmp_path / "physical_include"
    physical.mkdir()
    logical = tmp_path / "logical_include"
    logical.symlink_to(physical, target_is_directory=True)
    plain = tmp_path / "plain_include"
    plain.mkdir()
    top = tmp_path / "top.f"
    top.write_text(
        "top.sv\n"
        "+incdir+logical_include+plain_include // include search order\n",
        encoding="utf-8",
    )

    result = flatten_filelist(
        FlattenRequest(top_filelist=top, working_directory=tmp_path)
    )

    assert result.output_filelist.read_text(encoding="utf-8") == (
        "// include search order\n"
        f"// symlink target: {physical}\n"
        f"+incdir+{logical}\n"
        f"+incdir+{plain}\n"
        f"{source}\n"
    )
```

- [ ] **Step 2: Run the incdir test to verify red**

Run:

```bash
pytest -q tests/test_engine.py::test_incdirs_are_promoted_with_comments_and_symlink_annotations
```

Expected: FAIL because the source currently precedes the include group.

- [ ] **Step 3: Route the complete incdir group to its section**

In the existing `+incdir+` branch, continue building the local
`include_directories` list with each symlink annotation immediately before its
directory. Route the trailing comment and all rendered include-directory lines
to `sections.incdirs`:

```python
if trailing_comment is not None:
    sections.incdirs.append(trailing_comment)
sections.incdirs.extend(include_directories)
```

Do not split one logical multi-directory entry across categories. Do not change
path validation, order, or duplicate retention.

- [ ] **Step 4: Run focused incdir and ordering tests**

Run:

```bash
pytest -q tests/test_engine.py::test_incdirs_are_promoted_with_comments_and_symlink_annotations tests/test_engine.py::test_incdir_splits_directories_preserving_order_duplicates_and_comment tests/test_engine.py::test_all_recognized_simulator_paths_annotate_symlink_targets
```

Expected: PASS after updating any combined-output literal to the new global
define/incdir/other order. Per-entry include search order and duplicates remain unchanged.

- [ ] **Step 5: Run both public test suites**

Run:

```bash
pytest -q tests/test_engine.py tests/test_cli.py
```

Expected: PASS.

---

### Task 4: Update the authoritative and user-facing documentation

**Files:**
- Modify: `CONTEXT.md`
- Modify: `docs/requirements/ff.md`
- Modify: `README.md`
- Modify: `docs/user/ff-user-guide.html`
- Modify: `docs/development/verification.md`

**Interfaces:**
- Consumes: behavior proven by Tasks 1–3.
- Produces: one consistent description of dual macro semantics and global output order.

- [ ] **Step 1: Update domain terminology and authoritative requirements**

In `CONTEXT.md`, revise **Predefined macro** so it states that the macro selects
filelist conditional branches and is emitted as a same-name HDL compilation
define. Remove the old “Avoid: HDL compilation define” distinction. Add a term
for **Global compile option groups** defining the four output groups.

In `docs/requirements/ff.md`:

- update §3.2 to say `-d` both selects branches and emits `+define+MACRO`;
- update §4.2 so original `+define+...` still does not mutate ff's predefined
  macro set, even though it is promoted in output;
- replace §5's global original-order promise with stable order inside each
  output group;
- add §8's exact group order, sorted command-line macros, retained duplicates,
  nested-entry promotion, and comment ownership rules.

- [ ] **Step 2: Update README and User Guide examples**

In `README.md`, follow the existing `-d` command with a short sentence stating
that each macro also becomes a leading `+define+MACRO` in `flattened.f` for HDL
compilation.

In `docs/user/ff-user-guide.html`:

- update the quick-start example so `+incdir+` appears before the source;
- revise the CLI macro explanation around the existing `-d` examples;
- add an input–command–result example containing a selected conditional source,
  one original define, one incdir, and a duplicate same-name command define;
- revise the nested-filelist and path sections wherever they promise global
  original ordering;
- document the four output groups and stable per-group order in the reference
  table;
- state that an original `+define+` still does not select ff conditions.

- [ ] **Step 3: Update the verification matrix**

In `docs/development/verification.md`, add the exact new engine and CLI test names to the
macro and path-option rows, and describe global stable grouping as an explicitly
covered requirement.

- [ ] **Step 4: Check documentation consistency**

Run:

```bash
rg -n "原顺序|预定义宏|HDL|\\+define|\\+incdir|define option" README.md CONTEXT.md docs/requirements/ff.md docs/user/ff-user-guide.html docs/development/verification.md
```

Manually confirm every remaining “original order” statement is scoped to a
single group, not the entire flattened output.

---

### Task 5: Final verification

**Files:**
- Verify only; fix failures in the files owned by Tasks 1–4.

**Interfaces:**
- Consumes: the completed implementation and documentation.
- Produces: evidence that the package still compiles, tests, and builds.

- [ ] **Step 1: Run syntax compilation**

Run:

```bash
python -m compileall -q src
```

Expected: exit code 0 with no output.

- [ ] **Step 2: Run the full test suite**

Run:

```bash
pytest -q
```

Expected: all tests PASS.

- [ ] **Step 3: Build the wheel without dependency resolution**

Run:

```bash
python -m pip wheel . --no-build-isolation --no-deps
```

Expected: exit code 0 and a newly built `esim-0.1.0-py3-none-any.whl` in the
configured wheel output location/current directory.

- [ ] **Step 4: Inspect the final working tree without committing**

Run:

```bash
git diff --check
git status --short
```

Expected: no whitespace errors; only the design, plan, implementation, tests,
and requested documentation are modified/untracked. Do not stage, commit, or push.
