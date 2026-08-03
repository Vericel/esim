import os
from pathlib import Path

import pytest

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
        f"    {child_filelist}:1 -> {top_filelist}\n"
        "  suggestion: remove the recursive -f/-F reference"
    )


def test_repeated_filelist_references_and_sources_are_not_deduplicated(
    tmp_path: Path,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    child_filelist = tmp_path / "child.f"
    child_filelist.write_text("top.sv\ntop.sv\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("-F child.f\n-F child.f\n", encoding="utf-8")

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=top_filelist,
            working_directory=tmp_path,
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == f"{source}\n" * 4


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
        f"  resolved: {missing_source}\n"
        "  suggestion: correct the path or restore the source file"
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
