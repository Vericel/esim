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
        f"  resolved: {resolved}\n"
        "  suggestion: correct the path or restore the source file"
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


def test_source_readability_uses_effective_process_access(tmp_path: Path) -> None:
    from ff import FlattenError, FlattenRequest, flatten_filelist

    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    source.chmod(0o004)
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("top.sv\n", encoding="utf-8")

    with pytest.raises(FlattenError) as caught:
        flatten_filelist(
            FlattenRequest(
                top_filelist=top_filelist,
                working_directory=tmp_path,
            )
        )

    assert "source file is not readable" in str(caught.value)


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
