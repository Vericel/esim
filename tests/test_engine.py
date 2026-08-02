import os
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


def test_unreadable_source_is_rejected_before_output_is_published(
    tmp_path: Path,
) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    source.chmod(0)
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("top.sv\n", encoding="utf-8")
    output_filelist = tmp_path / "flattened.f"

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
                output_filelist=output_filelist,
            )
        )

    assert str(caught.value) == (
        "source file is not readable\n"
        f"  at: {top_filelist}:1\n"
        "  input: top.sv\n"
        f"  resolved: {source}\n"
        "  suggestion: grant read permission to the source file"
    )
    assert not output_filelist.exists()


def test_unreadable_top_filelist_is_a_structured_engine_error(
    tmp_path: Path,
) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("", encoding="utf-8")
    top_filelist.chmod(0)

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
            )
        )

    assert str(caught.value) == (
        "top filelist is not readable\n"
        f"  input: {top_filelist}\n"
        "  suggestion: grant read permission to the filelist"
    )


def test_missing_top_filelist_is_a_structured_engine_error(tmp_path: Path) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    top_filelist = tmp_path / "missing.f"

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
            )
        )

    assert str(caught.value) == (
        "top filelist does not exist\n"
        f"  input: {top_filelist}\n"
        "  suggestion: provide an existing filelist path"
    )


def test_top_filelist_directory_is_rejected_as_wrong_type(tmp_path: Path) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    top_filelist = tmp_path / "lists"
    top_filelist.mkdir()

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
            )
        )

    assert str(caught.value) == (
        "top filelist is not a regular file\n"
        f"  input: {top_filelist}\n"
        "  suggestion: provide a regular file"
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


def test_unreadable_child_filelist_reports_its_reference(
    tmp_path: Path,
) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    child_filelist = tmp_path / "child.f"
    child_filelist.write_text("", encoding="utf-8")
    child_filelist.chmod(0)
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("-F child.f\n", encoding="utf-8")

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
            )
        )

    assert str(caught.value) == (
        "filelist is not readable\n"
        f"  at: {top_filelist}:1\n"
        "  input: -F child.f\n"
        f"  resolved: {child_filelist}\n"
        "  suggestion: grant read permission to the filelist"
    )


def test_nested_parse_error_reports_complete_filelist_source_chain(
    tmp_path: Path,
) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    leaf_filelist = tmp_path / "leaf.f"
    leaf_filelist.write_text("`define BAD\n", encoding="utf-8")
    child_filelist = tmp_path / "child.f"
    child_filelist.write_text("-F leaf.f\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("-F child.f\n", encoding="utf-8")

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
            )
        )

    assert str(caught.value) == (
        "unsupported backtick directive\n"
        "  source chain:\n"
        f"    {top_filelist}:1 -> {child_filelist}\n"
        f"    {child_filelist}:1 -> {leaf_filelist}\n"
        f"  at: {leaf_filelist}:1\n"
        "  input: `define BAD\n"
        "  supported: `ifdef, `ifndef, `elsif, `else, `endif"
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


def test_multiline_block_comments_follow_conditional_branch_selection(
    tmp_path: Path,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    source = tmp_path / "active.sv"
    source.write_text("module active; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text(
        "`ifdef OMITTED\n"
        "/* removed\n"
        "   comment */\n"
        "`else\n"
        "/* retained\n"
        "   comment */\n"
        "active.sv\n"
        "`endif\n",
        encoding="utf-8",
    )

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == (
        "/* retained\n"
        "   comment */\n"
        f"{source}\n"
    )


def test_multiline_block_comment_follows_normalized_source_path(
    tmp_path: Path,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    source = tmp_path / "rtl" / "top.sv"
    source.parent.mkdir()
    source.write_text("module top; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text(
        "rtl/top.sv /* primary\n"
        "               source */\n",
        encoding="utf-8",
    )

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == (
        f"{source} /* primary\n"
        "               source */\n"
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


def test_filelist_reference_promotes_complete_multiline_block_comment(
    tmp_path: Path,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    child_filelist = tmp_path / "child.f"
    child_filelist.write_text("top.sv\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text(
        "-F child.f /* expanded\n"
        "               child sources */\n",
        encoding="utf-8",
    )

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == (
        "/* expanded\n"
        "               child sources */\n"
        f"{source}\n"
    )


def test_block_comment_must_close_inside_the_filelist_that_opened_it(
    tmp_path: Path,
) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    child_filelist = tmp_path / "child.f"
    child_filelist.write_text("/* not closed here\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text(
        "-F child.f\n"
        "*/\n",
        encoding="utf-8",
    )

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
            )
        )

    assert str(caught.value) == (
        "unterminated block comment\n"
        "  source chain:\n"
        f"    {top_filelist}:1 -> {child_filelist}\n"
        f"  opened at: {child_filelist}:1\n"
        "  suggestion: close the comment with */ in the same filelist"
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


def test_unreadable_v_library_file_is_rejected(tmp_path: Path) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    library_file = tmp_path / "models.v"
    library_file.write_text("module model; endmodule\n", encoding="utf-8")
    library_file.chmod(0)
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("-v models.v\n", encoding="utf-8")

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
            )
        )

    assert str(caught.value) == (
        "library file is not readable\n"
        f"  at: {top_filelist}:1\n"
        "  input: -v models.v\n"
        f"  resolved: {library_file}\n"
        "  suggestion: grant read permission to the library file"
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


def test_new_output_permissions_respect_process_umask(tmp_path: Path) -> None:
    from ff import FlattenRequest, flatten_filelist

    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("top.sv\n", encoding="utf-8")
    output_filelist = tmp_path / "new.f"

    previous_umask = os.umask(0o027)
    try:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
                output_filelist=output_filelist,
            )
        )
    finally:
        os.umask(previous_umask)

    assert output_filelist.stat().st_mode & 0o777 == 0o640


def test_output_parent_directory_must_already_exist(tmp_path: Path) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("top.sv\n", encoding="utf-8")
    output_filelist = tmp_path / "missing" / "flattened.f"

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
                output_filelist=output_filelist,
            )
        )

    assert str(caught.value) == (
        "output parent directory does not exist\n"
        f"  output: {output_filelist}\n"
        f"  parent: {output_filelist.parent}\n"
        "  suggestion: create the parent directory or choose another output"
    )
    assert not output_filelist.parent.exists()


def test_output_parent_must_be_a_writable_directory(tmp_path: Path) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("top.sv\n", encoding="utf-8")
    parent_file = tmp_path / "not-a-directory"
    parent_file.write_text("content\n", encoding="utf-8")
    output_filelist = parent_file / "flattened.f"

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
                output_filelist=output_filelist,
            )
        )

    assert str(caught.value) == (
        "output parent is not a directory\n"
        f"  output: {output_filelist}\n"
        f"  parent: {parent_file}\n"
        "  suggestion: choose an output path inside a directory"
    )


def test_output_parent_directory_must_be_writable(tmp_path: Path) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("top.sv\n", encoding="utf-8")
    output_parent = tmp_path / "read-only"
    output_parent.mkdir()
    output_parent.chmod(0o555)
    output_filelist = output_parent / "flattened.f"

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
                output_filelist=output_filelist,
            )
        )

    assert str(caught.value) == (
        "output parent directory is not writable\n"
        f"  output: {output_filelist}\n"
        f"  parent: {output_parent}\n"
        "  suggestion: grant write and search permission to the directory"
    )


def test_existing_output_directory_is_rejected_before_publication(
    tmp_path: Path,
) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("top.sv\n", encoding="utf-8")
    output_filelist = tmp_path / "flattened.f"
    output_filelist.mkdir()

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
                output_filelist=output_filelist,
            )
        )

    assert str(caught.value) == (
        "output path is not a regular file\n"
        f"  output: {output_filelist}\n"
        "  suggestion: choose a file path for the flattened filelist"
    )
    assert output_filelist.is_dir()


def test_output_symlink_node_is_replaced_without_touching_target(
    tmp_path: Path,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("top.sv\n", encoding="utf-8")
    output_target = tmp_path / "preserved.f"
    output_target.write_text("target stays\n", encoding="utf-8")
    output_filelist = tmp_path / "flattened.f"
    output_filelist.symlink_to(output_target)

    flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
            output_filelist=output_filelist,
        )
    )

    assert not output_filelist.is_symlink()
    assert output_filelist.read_text(encoding="utf-8") == f"{source}\n"
    assert output_target.read_text(encoding="utf-8") == "target stays\n"


def test_flatten_failure_preserves_existing_output_bytes_and_inode(
    tmp_path: Path,
) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("missing.sv\n", encoding="utf-8")
    output_filelist = tmp_path / "flattened.f"
    original_content = b"existing output\n"
    output_filelist.write_bytes(original_content)
    original_inode = output_filelist.stat().st_ino

    with pytest.raises(FlattenError):
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
                output_filelist=output_filelist,
            )
        )

    assert output_filelist.read_bytes() == original_content
    assert output_filelist.stat().st_ino == original_inode


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


def test_all_recognized_simulator_paths_annotate_symlink_targets(
    tmp_path: Path,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    physical_directory = tmp_path / "physical"
    physical_directory.mkdir()
    physical_library = physical_directory / "models.v"
    physical_library.write_text("module model; endmodule\n", encoding="utf-8")
    logical_directory = tmp_path / "logical"
    logical_directory.symlink_to(physical_directory, target_is_directory=True)
    logical_library = logical_directory / "models.v"
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text(
        "-v logical/models.v\n"
        "-y logical\n"
        "+incdir+logical\n",
        encoding="utf-8",
    )

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == (
        f"// symlink target: {physical_library}\n"
        f"-v {logical_library}\n"
        f"// symlink target: {physical_directory}\n"
        f"-y {logical_directory}\n"
        f"// symlink target: {physical_directory}\n"
        f"+incdir+{logical_directory}\n"
    )


def test_symlinked_child_filelist_is_annotated_before_its_expansion(
    tmp_path: Path,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    source = tmp_path / "lists" / "top.sv"
    source.parent.mkdir()
    source.write_text("module top; endmodule\n", encoding="utf-8")
    physical_child = tmp_path / "physical" / "child.f"
    physical_child.parent.mkdir()
    physical_child.write_text("../lists/top.sv\n", encoding="utf-8")
    logical_child = tmp_path / "lists" / "child.f"
    logical_child.symlink_to(physical_child)
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("-F lists/child.f\n", encoding="utf-8")

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == (
        f"// symlink target: {physical_child}\n"
        f"{source}\n"
    )


def test_symlinked_top_filelist_is_annotated_before_flattened_content(
    tmp_path: Path,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    source = tmp_path / "logical" / "top.sv"
    source.parent.mkdir()
    source.write_text("module top; endmodule\n", encoding="utf-8")
    physical_filelist = tmp_path / "physical" / "top.f"
    physical_filelist.parent.mkdir()
    physical_filelist.write_text("top.sv\n", encoding="utf-8")
    logical_filelist = tmp_path / "logical" / "top.f"
    logical_filelist.symlink_to(physical_filelist)

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=logical_filelist,
            working_directory=tmp_path,
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == (
        f"// symlink target: {physical_filelist}\n"
        f"{source}\n"
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


def test_non_utf8_filelist_reports_structured_error(tmp_path: Path) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    top_filelist = tmp_path / "top.f"
    top_filelist.write_bytes(b"top.sv\xff\n")

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
            )
        )

    assert str(caught.value) == (
        "filelist is not valid UTF-8\n"
        f"  input: {top_filelist}\n"
        "  suggestion: convert the filelist to UTF-8"
    )


def test_source_path_rejects_whitespace_even_when_file_exists(
    tmp_path: Path,
) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    source = tmp_path / "with space.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("with space.sv\n", encoding="utf-8")

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
            )
        )

    assert str(caught.value) == (
        "source path contains whitespace\n"
        f"  at: {top_filelist}:1\n"
        "  input: with space.sv\n"
        "  suggestion: use a path without spaces or tabs"
    )


@pytest.mark.parametrize("entry", ["*.sv", "top?.sv", "top[01].sv"])
def test_source_path_rejects_glob_metacharacters_even_when_file_exists(
    tmp_path: Path,
    entry: str,
) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    (tmp_path / entry).write_text("module top; endmodule\n", encoding="utf-8")
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
        "glob patterns are not supported in paths\n"
        f"  at: {top_filelist}:1\n"
        f"  input: {entry}\n"
        "  suggestion: list each path explicitly"
    )


@pytest.mark.parametrize(
    ("entry", "literal_name", "is_directory"),
    [
        ("-F child*.f", "child*.f", False),
        ("-v model?.v", "model?.v", False),
        ("-y lib[01]", "lib[01]", True),
        ("+incdir+inc*", "inc*", True),
    ],
)
def test_all_recognized_path_entries_reject_glob_metacharacters(
    tmp_path: Path,
    entry: str,
    literal_name: str,
    is_directory: bool,
) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    literal_path = tmp_path / literal_name
    if is_directory:
        literal_path.mkdir()
    else:
        literal_path.write_text("", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text(f"{entry}\n", encoding="utf-8")

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
            )
        )

    assert "glob patterns are not supported in paths" in str(caught.value)
    assert f"  input: {literal_name}" in str(caught.value)


def test_environment_expansion_cannot_introduce_path_whitespace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    project_directory = tmp_path / "project with space"
    source = project_directory / "top.sv"
    source.parent.mkdir()
    source.write_text("module top; endmodule\n", encoding="utf-8")
    monkeypatch.setenv("PROJ_DIR", str(project_directory))
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("$PROJ_DIR/top.sv\n", encoding="utf-8")

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
            )
        )

    assert str(caught.value) == (
        "path contains whitespace\n"
        f"  at: {top_filelist}:1\n"
        "  input: $PROJ_DIR/top.sv\n"
        f"  expanded: {source}\n"
        "  suggestion: use paths without spaces or tabs"
    )


def test_incdir_path_rejects_literal_whitespace_even_when_directory_exists(
    tmp_path: Path,
) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    include_directory = tmp_path / "include dir"
    include_directory.mkdir()
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("+incdir+include dir\n", encoding="utf-8")

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
            )
        )

    assert "path contains whitespace" in str(caught.value)
    assert "  input: include dir" in str(caught.value)


def test_backslash_line_continuation_is_rejected_explicitly(tmp_path: Path) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("top.sv \\\n", encoding="utf-8")

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
            )
        )

    assert str(caught.value) == (
        "backslash line continuation is not supported\n"
        f"  at: {top_filelist}:1\n"
        "  input: top.sv \\\n"
        "  suggestion: put one complete logical entry on each line"
    )


@pytest.mark.parametrize(
    "entry",
    [r"C:\project\rtl\top.sv", r"\\server\share\top.sv"],
)
def test_source_path_rejects_non_posix_path_syntax(
    tmp_path: Path,
    entry: str,
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
        "non-POSIX path syntax is not supported\n"
        f"  at: {top_filelist}:1\n"
        f"  input: {entry}\n"
        "  suggestion: use a Linux/POSIX path such as /mnt/c/project"
    )


@pytest.mark.parametrize(
    "entry",
    ["~/rtl/top.sv", "${DV_HOME:-/tmp}/top.sv", "$(pwd)/top.sv"],
)
def test_source_path_rejects_shell_expansion_syntax(
    tmp_path: Path,
    entry: str,
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
        "shell expansion syntax is not supported in paths\n"
        f"  at: {top_filelist}:1\n"
        f"  input: {entry}\n"
        "  supported: $NAME and ${NAME}"
    )
