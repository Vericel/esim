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
