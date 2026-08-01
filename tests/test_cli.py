from pathlib import Path
import subprocess
import sys


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
