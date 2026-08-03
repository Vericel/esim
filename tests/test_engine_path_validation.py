from pathlib import Path

import pytest


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


@pytest.mark.parametrize("entry", ["$9BAD/top.sv", "$/top.sv"])
def test_source_path_rejects_malformed_environment_references(
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
        "invalid environment variable syntax in path\n"
        f"  at: {top_filelist}:1\n"
        f"  input: {entry}\n"
        "  supported: $NAME and ${NAME}"
    )
