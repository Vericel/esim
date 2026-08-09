from pathlib import Path

import pytest

DEMO_DV = Path(__file__).parent / "fixtures/esim-demo-project/dv"


def test_complete_demo_combines_supported_filelist_syntax_for_vcs(
    tmp_path: Path,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    yyy_home = DEMO_DV / "xxx/yyy"
    feature_root = yyy_home / "tb/ff_features"
    output = tmp_path / "complete.f"

    flatten_filelist(
        FlattenRequest(
            top_filelist=yyy_home / "tb/full.f",
            working_directory=yyy_home / "tb",
            output_filelist=output,
            predefined_macros=frozenset(
                {
                    "COMPLETE_YYY",
                    "COMPLETE_LEFT",
                    "COMPLETE_RIGHT",
                    "COMPLETE_LEAF",
                }
            ),
            environment={
                "DV_HOME": str(DEMO_DV),
                "FF_DEMO_ROOT": "$DV_HOME/xxx/yyy/tb/ff_features",
                "FF_DEMO_SOURCE_ROOT": "${FF_DEMO_ROOT}/sources",
                "FF_DEMO_INCLUDE_ROOT": "$FF_DEMO_ROOT/include",
                "FF_DEMO_LIBRARY_FILE": "$FF_DEMO_ROOT/library/ff_demo_cells.sv",
                "FF_DEMO_LIBRARY_DIR": "${FF_DEMO_ROOT}/library/search",
                "FF_DEMO_WORKING_FILELIST": "$FF_DEMO_ROOT/working/working.f",
            },
        )
    )

    lines = output.read_text(encoding="utf-8").splitlines()
    assert lines[:6] == [
        "+define+COMPLETE_LEAF",
        "+define+COMPLETE_LEFT",
        "+define+COMPLETE_RIGHT",
        "+define+COMPLETE_YYY",
        "+define+FF_INPUT_TOP",
        "+define+FF_INPUT_NESTED",
    ]
    assert lines[6:9] == [
        "// complete demo include directories",
        f"+incdir+{feature_root / 'include/primary'}",
        f"+incdir+{feature_root / 'include/secondary'}",
    ]
    assert f"-v {feature_root / 'library/ff_demo_cells.sv'}" in lines
    assert f"-y {feature_root / 'library/search'}" in lines
    assert "+libext+.sv" in lines
    assert "-notice" in lines
    assert f"{feature_root / 'sources/condition_left.sv'} // ifndef branch" in lines
    assert f"{feature_root / 'sources/condition_right.sv'}" in lines
    assert f"{feature_root / 'sources/working_source.sv'}" in lines
    repeated = str(feature_root / "sources/repeated_marker.sv")
    assert lines.count(repeated) == 2
    assert "/* repeated relative filelist begins */" in lines
    assert "inactive_missing.sv" not in "\n".join(lines)


def test_demo_lowercase_f_case_uses_its_launch_directory(tmp_path: Path) -> None:
    from ff import FlattenRequest, flatten_filelist

    case_root = DEMO_DV / "xxx/yyy/tb/ff_cases/working-directory"
    launch_directory = case_root / "launch"
    source = launch_directory / "working_directory_source.sv"

    result = flatten_filelist(
        FlattenRequest(
            top_filelist=case_root / "top.f",
            working_directory=launch_directory,
            output_filelist=tmp_path / "working-directory.f",
        )
    )

    assert result.output_filelist.read_text(encoding="utf-8") == f"{source}\n"


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
