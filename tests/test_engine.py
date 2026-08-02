from pathlib import Path

import pytest


def test_engine_writes_default_flat_filelist(tmp_path: Path) -> None:
    from ff import FlattenRequest, flatten_filelist

    source = tmp_path / "rtl" / "top.sv"
    source.parent.mkdir()
    source.write_text("module top; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "lists" / "top.f"
    top_filelist.parent.mkdir()
    top_filelist.write_text(f"{source}\n", encoding="utf-8")

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
        )
    )

    assert (
        result.output_filelist,
        result.output_filelist.read_text(encoding="utf-8"),
    ) == (tmp_path / "flattened.f", f"{source}\n")


def test_top_filelist_resolves_relative_source_from_its_directory(
    tmp_path: Path,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    source = tmp_path / "rtl" / "top.sv"
    source.parent.mkdir()
    source.write_text("module top; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "lists" / "top.f"
    top_filelist.parent.mkdir()
    top_filelist.write_text("../rtl/top.sv\n", encoding="utf-8")
    working_directory = tmp_path / "build"
    working_directory.mkdir()

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=working_directory,
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == f"{source}\n"


def test_missing_source_reports_resolved_path_and_origin(tmp_path: Path) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    top_filelist = tmp_path / "lists" / "top.f"
    top_filelist.parent.mkdir()
    top_filelist.write_text("../rtl/missing.sv\n", encoding="utf-8")
    resolved = tmp_path / "rtl" / "missing.sv"

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
            )
        )

    assert str(caught.value) == (
        "source file does not exist\n"
        f"  at: {top_filelist}:1\n"
        "  input: ../rtl/missing.sv\n"
        f"  resolved: {resolved}"
    )


def test_ifdef_keeps_branch_for_predefined_macro(tmp_path: Path) -> None:
    from ff import FlattenRequest, flatten_filelist

    source = tmp_path / "rtl" / "fpga.sv"
    source.parent.mkdir()
    source.write_text("module fpga; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "lists" / "top.f"
    top_filelist.parent.mkdir()
    top_filelist.write_text(
        "`ifdef FPGA\n../rtl/fpga.sv\n`endif\n",
        encoding="utf-8",
    )

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
            predefined_macros=frozenset({"FPGA"}),
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == f"{source}\n"


def test_ifndef_keeps_branch_for_missing_macro(tmp_path: Path) -> None:
    from ff import FlattenRequest, flatten_filelist

    source = tmp_path / "rtl" / "asic.sv"
    source.parent.mkdir()
    source.write_text("module asic; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "lists" / "top.f"
    top_filelist.parent.mkdir()
    top_filelist.write_text(
        "`ifndef FPGA\n../rtl/asic.sv\n`endif\n",
        encoding="utf-8",
    )

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == f"{source}\n"


def test_else_keeps_fallback_branch_when_ifdef_is_not_selected(tmp_path: Path) -> None:
    from ff import FlattenRequest, flatten_filelist

    fpga_source = tmp_path / "rtl" / "fpga.sv"
    fpga_source.parent.mkdir()
    fpga_source.write_text("module fpga; endmodule\n", encoding="utf-8")
    asic_source = tmp_path / "rtl" / "asic.sv"
    asic_source.write_text("module asic; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "lists" / "top.f"
    top_filelist.parent.mkdir()
    top_filelist.write_text(
        "`ifdef FPGA\n"
        "../rtl/fpga.sv\n"
        "`else\n"
        "../rtl/asic.sv\n"
        "`endif\n",
        encoding="utf-8",
    )

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == f"{asic_source}\n"


def test_elsif_keeps_first_matching_alternative_branch(tmp_path: Path) -> None:
    from ff import FlattenRequest, flatten_filelist

    rtl_dir = tmp_path / "rtl"
    rtl_dir.mkdir()
    for name in ("fpga.sv", "asic.sv", "generic.sv"):
        (rtl_dir / name).write_text(
            f"module {Path(name).stem}; endmodule\n",
            encoding="utf-8",
        )
    top_filelist = tmp_path / "lists" / "top.f"
    top_filelist.parent.mkdir()
    top_filelist.write_text(
        "`ifdef FPGA\n"
        "../rtl/fpga.sv\n"
        "`elsif ASIC\n"
        "../rtl/asic.sv\n"
        "`else\n"
        "../rtl/generic.sv\n"
        "`endif\n",
        encoding="utf-8",
    )

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
            predefined_macros=frozenset({"ASIC"}),
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == (
        f"{rtl_dir / 'asic.sv'}\n"
    )


def test_unmatched_endif_reports_structured_filelist_error(tmp_path: Path) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("`endif\n", encoding="utf-8")

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
            )
        )

    assert str(caught.value) == (
        "unexpected `endif without a matching condition\n"
        f"  at: {top_filelist}:1"
    )


def test_unclosed_condition_at_eof_reports_its_opening_line(tmp_path: Path) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("`ifdef FPGA\n", encoding="utf-8")

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
            )
        )

    assert str(caught.value) == (
        "unterminated conditional block\n"
        f"  opened at: {top_filelist}:1"
    )


@pytest.mark.parametrize("directive", ["`else", "`elsif FPGA"])
def test_branch_continuation_without_condition_reports_structured_error(
    tmp_path: Path,
    directive: str,
) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    top_filelist = tmp_path / "top.f"
    top_filelist.write_text(f"{directive}\n", encoding="utf-8")

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
            )
        )

    directive_name = directive.split()[0]
    assert str(caught.value) == (
        f"unexpected {directive_name} without a matching condition\n"
        f"  at: {top_filelist}:1"
    )


@pytest.mark.parametrize("directive", ["`else", "`elsif ASIC"])
def test_condition_rejects_branch_directives_after_else(
    tmp_path: Path,
    directive: str,
) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    top_filelist = tmp_path / "top.f"
    top_filelist.write_text(
        "`ifdef FPGA\n"
        "`else\n"
        f"{directive}\n"
        "`endif\n",
        encoding="utf-8",
    )

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
            )
        )

    directive_name = directive.split()[0]
    assert str(caught.value) == (
        f"unexpected {directive_name} after `else\n"
        f"  at: {top_filelist}:3"
    )


@pytest.mark.parametrize(
    ("content", "line_number", "input_line", "expected_usage"),
    [
        ("`ifdef\n", 1, "`ifdef", "`ifdef MACRO"),
        ("`ifndef FPGA EXTRA\n", 1, "`ifndef FPGA EXTRA", "`ifndef MACRO"),
        ("`ifdef FPGA\n`elsif\n`endif\n", 2, "`elsif", "`elsif MACRO"),
        ("`ifdef FPGA\n`else EXTRA\n`endif\n", 2, "`else EXTRA", "`else"),
        ("`ifdef FPGA\n`endif EXTRA\n`endif\n", 2, "`endif EXTRA", "`endif"),
    ],
)
def test_condition_directives_reject_wrong_argument_counts(
    tmp_path: Path,
    content: str,
    line_number: int,
    input_line: str,
    expected_usage: str,
) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    top_filelist = tmp_path / "top.f"
    top_filelist.write_text(content, encoding="utf-8")

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
            )
        )

    assert str(caught.value) == (
        "invalid conditional directive syntax\n"
        f"  at: {top_filelist}:{line_number}\n"
        f"  input: {input_line}\n"
        f"  expected: {expected_usage}"
    )


def test_engine_rejects_invalid_predefined_macro_name(tmp_path: Path) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("", encoding="utf-8")

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
                predefined_macros=frozenset({"WIDTH=32"}),
            )
        )

    assert str(caught.value) == (
        "invalid predefined macro name\n"
        "  macro: WIDTH=32\n"
        "  expected: [A-Za-z_][A-Za-z0-9_$]*"
    )


def test_condition_rejects_invalid_macro_name(tmp_path: Path) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("`ifdef 1BAD\n`endif\n", encoding="utf-8")

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
            )
        )

    assert str(caught.value) == (
        "invalid conditional macro name\n"
        f"  at: {top_filelist}:1\n"
        "  macro: 1BAD\n"
        "  expected: [A-Za-z_][A-Za-z0-9_$]*"
    )


def test_active_unknown_backtick_directive_is_rejected(tmp_path: Path) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("`define FPGA\n", encoding="utf-8")

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
            )
        )

    assert str(caught.value) == (
        "unsupported backtick directive\n"
        f"  at: {top_filelist}:1\n"
        "  input: `define FPGA\n"
        "  supported: `ifdef, `ifndef, `elsif, `else, `endif"
    )


def test_uppercase_f_recursively_uses_each_filelist_directory(
    tmp_path: Path,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    source = tmp_path / "rtl" / "top.sv"
    source.parent.mkdir()
    source.write_text("module top; endmodule\n", encoding="utf-8")
    child_filelist = tmp_path / "lists" / "sub" / "child.f"
    child_filelist.parent.mkdir(parents=True)
    child_filelist.write_text("../../rtl/top.sv\n", encoding="utf-8")
    top_filelist = tmp_path / "lists" / "top.f"
    top_filelist.write_text("-F sub/child.f\n", encoding="utf-8")
    working_directory = tmp_path / "build"
    working_directory.mkdir()

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=working_directory,
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == f"{source}\n"


def test_lowercase_f_recursively_uses_invocation_working_directory(
    tmp_path: Path,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    working_directory = tmp_path / "build"
    source = working_directory / "rtl" / "top.sv"
    source.parent.mkdir(parents=True)
    source.write_text("module top; endmodule\n", encoding="utf-8")
    child_filelist = working_directory / "child.f"
    child_filelist.write_text("rtl/top.sv\n", encoding="utf-8")
    top_filelist = tmp_path / "lists" / "top.f"
    top_filelist.parent.mkdir()
    top_filelist.write_text("-f child.f\n", encoding="utf-8")

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=working_directory,
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == f"{source}\n"


def test_recursive_filelist_cycle_reports_complete_source_chain(
    tmp_path: Path,
) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    top_filelist = tmp_path / "top.f"
    child_filelist = tmp_path / "child.f"
    top_filelist.write_text("-F child.f\n", encoding="utf-8")
    child_filelist.write_text("-F top.f\n", encoding="utf-8")

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
            )
        )

    assert str(caught.value) == (
        "filelist include cycle\n"
        "  source chain:\n"
        f"    {top_filelist}:1 -> {child_filelist}\n"
        f"    {child_filelist}:1 -> {top_filelist}"
    )


def test_nested_missing_source_reports_complete_source_chain(
    tmp_path: Path,
) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    top_filelist = tmp_path / "top.f"
    middle_filelist = tmp_path / "middle.f"
    leaf_filelist = tmp_path / "leaf.f"
    missing_source = tmp_path / "missing.sv"
    top_filelist.write_text("-F middle.f\n", encoding="utf-8")
    middle_filelist.write_text("-F leaf.f\n", encoding="utf-8")
    leaf_filelist.write_text("missing.sv\n", encoding="utf-8")

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
            )
        )

    assert str(caught.value) == (
        "source file does not exist\n"
        "  source chain:\n"
        f"    {top_filelist}:1 -> {middle_filelist}\n"
        f"    {middle_filelist}:1 -> {leaf_filelist}\n"
        f"  at: {leaf_filelist}:1\n"
        "  input: missing.sv\n"
        f"  resolved: {missing_source}"
    )


def test_active_blank_lines_and_line_comments_preserve_source_order(
    tmp_path: Path,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    first_source = tmp_path / "first.sv"
    first_source.write_text("module first; endmodule\n", encoding="utf-8")
    second_source = tmp_path / "second.sv"
    second_source.write_text("module second; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text(
        "first.sv\n"
        "\n"
        "  // between sources\n"
        "second.sv\n",
        encoding="utf-8",
    )

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == (
        f"{first_source}\n"
        "\n"
        "  // between sources\n"
        f"{second_source}\n"
    )


def test_filelist_reference_trailing_comment_is_promoted_before_expansion(
    tmp_path: Path,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    child_filelist = tmp_path / "child.f"
    child_filelist.write_text("top.sv\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text(
        "-F child.f // expanded child sources\n",
        encoding="utf-8",
    )

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == (
        "// expanded child sources\n"
        f"{source}\n"
    )


def test_source_trailing_comment_follows_normalized_absolute_path(
    tmp_path: Path,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    source = tmp_path / "rtl" / "top.sv"
    source.parent.mkdir()
    source.write_text("module top; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text(
        "rtl/top.sv // primary source\n",
        encoding="utf-8",
    )

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == (
        f"{source} // primary source\n"
    )


@pytest.mark.parametrize(
    "entry",
    ["$PROJ_DIR/rtl/top.sv", "${PROJ_DIR}/rtl/top.sv"],
)
def test_source_path_expands_standard_environment_variable_forms(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    entry: str,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    project_directory = tmp_path / "project"
    source = project_directory / "rtl" / "top.sv"
    source.parent.mkdir(parents=True)
    source.write_text("module top; endmodule\n", encoding="utf-8")
    monkeypatch.setenv("PROJ_DIR", str(project_directory))
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text(f"{entry}\n", encoding="utf-8")

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == f"{source}\n"


def test_missing_environment_variable_reports_its_name_and_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    monkeypatch.delenv("DV_HOME", raising=False)
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("$DV_HOME/rtl/top.sv\n", encoding="utf-8")

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
            )
        )

    assert str(caught.value) == (
        "environment variable is not set\n"
        f"  at: {top_filelist}:1\n"
        "  input: $DV_HOME/rtl/top.sv\n"
        "  variable: DV_HOME\n"
        "  suggestion: export DV_HOME before running ff"
    )


def test_empty_environment_variable_reports_its_name_and_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    monkeypatch.setenv("DV_HOME", "")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("$DV_HOME/rtl/top.sv\n", encoding="utf-8")

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
            )
        )

    assert str(caught.value) == (
        "environment variable is empty\n"
        f"  at: {top_filelist}:1\n"
        "  input: $DV_HOME/rtl/top.sv\n"
        "  variable: DV_HOME\n"
        "  suggestion: export DV_HOME with a non-empty value before running ff"
    )


def test_environment_values_are_expanded_recursively(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    source = tmp_path / "project" / "rtl" / "top.sv"
    source.parent.mkdir(parents=True)
    source.write_text("module top; endmodule\n", encoding="utf-8")
    monkeypatch.setenv("BASE_DIR", str(tmp_path))
    monkeypatch.setenv("PROJ_DIR", "$BASE_DIR/project")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("$PROJ_DIR/rtl/top.sv\n", encoding="utf-8")

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == f"{source}\n"


def test_environment_expansion_cycle_reports_expansion_chain(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    monkeypatch.setenv("ROOT_A", "$ROOT_B")
    monkeypatch.setenv("ROOT_B", "${ROOT_A}")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("$ROOT_A/rtl/top.sv\n", encoding="utf-8")

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
            )
        )

    assert str(caught.value) == (
        "environment variable expansion cycle\n"
        f"  at: {top_filelist}:1\n"
        "  input: $ROOT_A/rtl/top.sv\n"
        "  expansion chain: ROOT_A -> ROOT_B -> ROOT_A\n"
        "  suggestion: remove the recursive environment variable reference"
    )


def test_filelist_reference_path_expands_environment_variables(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    lists_directory = tmp_path / "lists"
    lists_directory.mkdir()
    source = lists_directory / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    child_filelist = lists_directory / "child.f"
    child_filelist.write_text("top.sv\n", encoding="utf-8")
    monkeypatch.setenv("LISTS_DIR", str(lists_directory))
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("-F $LISTS_DIR/child.f\n", encoding="utf-8")

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == f"{source}\n"


def test_v_library_file_is_expanded_and_rendered_as_absolute(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    library_directory = tmp_path / "libraries"
    library_directory.mkdir()
    library_file = library_directory / "models.v"
    library_file.write_text("module model; endmodule\n", encoding="utf-8")
    monkeypatch.setenv("LIB_DIR", str(library_directory))
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("-v $LIB_DIR/models.v\n", encoding="utf-8")

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == (
        f"-v {library_file}\n"
    )


def test_y_library_directory_is_expanded_and_rendered_as_absolute(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    library_directory = tmp_path / "libraries"
    library_directory.mkdir()
    monkeypatch.setenv("LIB_ROOT", str(tmp_path))
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("-y $LIB_ROOT/libraries\n", encoding="utf-8")

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == (
        f"-y {library_directory}\n"
    )


def test_incdir_splits_directories_preserving_order_duplicates_and_comment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    include_root = tmp_path / "include"
    first_directory = include_root / "first"
    first_directory.mkdir(parents=True)
    second_directory = include_root / "second"
    second_directory.mkdir()
    monkeypatch.setenv("INC_ROOT", str(include_root))
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text(
        "+incdir+$INC_ROOT/first+$INC_ROOT/second+$INC_ROOT/first "
        "// include search order\n",
        encoding="utf-8",
    )

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == (
        "// include search order\n"
        f"+incdir+{first_directory}\n"
        f"+incdir+{second_directory}\n"
        f"+incdir+{first_directory}\n"
    )


@pytest.mark.parametrize(
    "entry",
    ["+incdir+", "+incdir++include", "+incdir+include+"],
)
def test_incdir_rejects_empty_directory_segments(
    tmp_path: Path,
    entry: str,
) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    (tmp_path / "include").mkdir()
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text(f"{entry}\n", encoding="utf-8")

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
            )
        )

    assert str(caught.value) == (
        "invalid +incdir+ syntax\n"
        f"  at: {top_filelist}:1\n"
        f"  input: {entry}\n"
        "  suggestion: provide a non-empty directory after every + separator"
    )


def test_unknown_simulator_options_pass_through_without_defining_ff_macros(
    tmp_path: Path,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    source = tmp_path / "generic.sv"
    source.write_text("module generic; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text(
        "+define+FPGA\n"
        "-sverilog\n"
        "`ifdef FPGA\n"
        "missing-fpga.sv\n"
        "`endif\n"
        "generic.sv\n",
        encoding="utf-8",
    )

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == (
        "+define+FPGA\n"
        "-sverilog\n"
        f"{source}\n"
    )


@pytest.mark.parametrize(
    ("entry", "expected_usage"),
    [
        ("-f", "-f PATH"),
        ("-F child.f extra.f", "-F PATH"),
        ("-v=models.v", "-v PATH"),
        ("-ylibraries", "-y PATH"),
    ],
)
def test_recognized_path_options_require_one_separated_argument(
    tmp_path: Path,
    entry: str,
    expected_usage: str,
) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    top_filelist = tmp_path / "top.f"
    top_filelist.write_text(f"{entry}\n", encoding="utf-8")

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
            )
        )

    assert str(caught.value) == (
        "invalid path option syntax\n"
        f"  at: {top_filelist}:1\n"
        f"  input: {entry}\n"
        f"  expected: {expected_usage}"
    )


def test_success_atomically_replaces_existing_output_inode(tmp_path: Path) -> None:
    from ff import FlattenRequest, flatten_filelist

    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("top.sv\n", encoding="utf-8")
    output_filelist = tmp_path / "flattened.f"
    output_filelist.write_text("old content\n", encoding="utf-8")
    old_inode = output_filelist.stat().st_ino

    flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
            output_filelist=output_filelist,
        )
    )

    assert output_filelist.read_text(encoding="utf-8") == f"{source}\n"
    assert output_filelist.stat().st_ino != old_inode


def test_replacing_regular_output_preserves_rw_bits_and_clears_execute(
    tmp_path: Path,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("top.sv\n", encoding="utf-8")
    output_filelist = tmp_path / "flattened.f"
    output_filelist.write_text("old content\n", encoding="utf-8")
    output_filelist.chmod(0o765)

    flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
            output_filelist=output_filelist,
        )
    )

    assert output_filelist.stat().st_mode & 0o777 == 0o664


def test_output_cannot_replace_an_input_filelist(tmp_path: Path) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    original_content = "top.sv\n"
    top_filelist.write_text(original_content, encoding="utf-8")

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
                output_filelist=top_filelist,
            )
        )

    assert str(caught.value) == (
        "output conflicts with an input filelist\n"
        f"  output: {top_filelist}\n"
        f"  input: {top_filelist}\n"
        "  suggestion: choose a different output path"
    )
    assert top_filelist.read_text(encoding="utf-8") == original_content


def test_symlinked_source_keeps_logical_path_with_physical_target_comment(
    tmp_path: Path,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    physical_source = tmp_path / "physical" / "top.sv"
    physical_source.parent.mkdir()
    physical_source.write_text("module top; endmodule\n", encoding="utf-8")
    logical_source = tmp_path / "logical" / "top.sv"
    logical_source.parent.mkdir()
    logical_source.symlink_to(physical_source)
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("logical/top.sv\n", encoding="utf-8")

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == (
        f"// symlink target: {physical_source}\n"
        f"{logical_source}\n"
    )


def test_utf8_bom_and_crlf_input_renders_utf8_lf_without_bom(
    tmp_path: Path,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_bytes(b"\xef\xbb\xbftop.sv\r\n")

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
        )
    )

    assert result.output_filelist.read_bytes() == f"{source}\n".encode("utf-8")
