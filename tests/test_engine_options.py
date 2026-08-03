import os
from pathlib import Path

import pytest

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


def test_filelist_defines_are_promoted_after_command_line_defines_stably(
    tmp_path: Path,
) -> None:
    from ff import FlattenRequest, flatten_filelist

    first = tmp_path / "first.sv"
    first.write_text("module first; endmodule\n", encoding="utf-8")
    second = tmp_path / "second.sv"
    second.write_text("module second; endmodule\n", encoding="utf-8")
    include = tmp_path / "include"
    include.mkdir()
    child = tmp_path / "child.f"
    child.write_text(
        "second.sv\n"
        "+define+STUB_XXX // from child\n",
        encoding="utf-8",
    )
    top = tmp_path / "top.f"
    top.write_text(
        "first.sv\n"
        "+incdir+include\n"
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
        f"+incdir+{include}\n"
        f"{first}\n"
        f"{second}\n"
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
