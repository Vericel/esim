import subprocess
import sys
from pathlib import Path

DEMO_DV = Path(__file__).parent / "fixtures/esim-demo-project/dv"


def test_demo_empty_source_case_writes_default_flat_filelist(
    tmp_path: Path,
) -> None:
    ff_command = Path(sys.executable).with_name("ff")
    top_filelist = DEMO_DV / "xxx/yyy/tb/ff_cases/empty.f"

    completed = subprocess.run(
        [str(ff_command), str(top_filelist)],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    output = tmp_path / "flattened.f"
    assert (
        completed.returncode,
        completed.stderr,
        output.read_text(encoding="utf-8") if output.exists() else None,
    ) == (0, "", "// A valid filelist may select zero source paths.\n")


def test_cli_writes_default_flat_filelist(tmp_path: Path) -> None:
    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text(f"{source}\n", encoding="utf-8")
    ff_command = Path(sys.executable).with_name("ff")

    completed = subprocess.run(
        [str(ff_command), str(top_filelist)],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    output = tmp_path / "flattened.f"
    assert (
        completed.returncode,
        completed.stderr,
        output.read_text(encoding="utf-8") if output.exists() else None,
    ) == (0, "", f"{source}\n")


def test_cli_writes_explicit_output_filelist(tmp_path: Path) -> None:
    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text(f"{source}\n", encoding="utf-8")
    ff_command = Path(sys.executable).with_name("ff")

    completed = subprocess.run(
        [str(ff_command), str(top_filelist), "-o", "custom.f"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    output = tmp_path / "custom.f"
    assert (
        completed.returncode,
        completed.stderr,
        output.read_text(encoding="utf-8") if output.exists() else None,
    ) == (0, "", f"{source}\n")


def test_cli_define_option_selects_all_named_macro_branches(tmp_path: Path) -> None:
    fpga_source = tmp_path / "fpga.sv"
    fpga_source.write_text("module fpga; endmodule\n", encoding="utf-8")
    ddr_source = tmp_path / "ddr.sv"
    ddr_source.write_text("module ddr; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text(
        f"`ifdef FPGA\n{fpga_source}\n`endif\n`ifdef USE_DDR\n{ddr_source}\n`endif\n",
        encoding="utf-8",
    )
    ff_command = Path(sys.executable).with_name("ff")

    completed = subprocess.run(
        [
            str(ff_command),
            str(top_filelist),
            "-d",
            "FPGA",
            "USE_DDR",
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    output = tmp_path / "flattened.f"
    assert (
        completed.returncode,
        completed.stderr,
        output.read_text(encoding="utf-8") if output.exists() else None,
    ) == (
        0,
        "",
        f"+define+FPGA\n+define+USE_DDR\n{fpga_source}\n{ddr_source}\n",
    )
