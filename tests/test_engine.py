from pathlib import Path


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
