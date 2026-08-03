import subprocess
import sys
from pathlib import Path


def test_cli_log_flag_without_path_atomically_publishes_ff_log(
    tmp_path: Path,
) -> None:
    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("top.sv\n", encoding="utf-8")
    ff_command = Path(sys.executable).with_name("ff")

    completed = subprocess.run(
        [str(ff_command), str(top_filelist), "-l"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    log_file = tmp_path / "ff.log"
    assert (
        completed.returncode,
        completed.stdout,
        completed.stderr,
        log_file.exists(),
        log_file.read_text(encoding="utf-8") if log_file.exists() else None,
        (tmp_path / "app.log").exists(),
    ) == (0, "", "", True, "", False)


def test_cli_debug_emits_trace_to_terminal_without_creating_log(
    tmp_path: Path,
) -> None:
    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("top.sv\n", encoding="utf-8")
    ff_command = Path(sys.executable).with_name("ff")

    completed = subprocess.run(
        [str(ff_command), str(top_filelist), "--debug"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    terminal = completed.stdout + completed.stderr
    assert completed.returncode == 0
    assert "DEBUG" in terminal
    assert "flattening input:" in terminal
    assert "top.f" in terminal
    assert "INFO" in terminal
    assert "flattened output:" in terminal
    assert "flattened.f" in terminal
    assert not (tmp_path / "ff.log").exists()
    assert not (tmp_path / "app.log").exists()


def test_cli_debug_traces_recursive_filelist_and_source_resolution(
    tmp_path: Path,
) -> None:
    source = tmp_path / "rtl" / "top.sv"
    source.parent.mkdir()
    source.write_text("module top; endmodule\n", encoding="utf-8")
    child_filelist = tmp_path / "lists" / "child.f"
    child_filelist.parent.mkdir()
    child_filelist.write_text("../rtl/top.sv\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("-F lists/child.f\n", encoding="utf-8")
    ff_command = Path(sys.executable).with_name("ff")

    completed = subprocess.run(
        [str(ff_command), str(top_filelist), "--debug"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    terminal = completed.stdout + completed.stderr
    assert completed.returncode == 0
    for trace_message in (
        "reading filelist:",
        "expanding filelist:",
        "resolved source:",
    ):
        assert trace_message in terminal
    assert "child.f" in terminal
    assert "top.sv" in terminal


def test_cli_debug_and_custom_log_receive_the_same_trace_levels(
    tmp_path: Path,
) -> None:
    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("top.sv\n", encoding="utf-8")
    ff_command = Path(sys.executable).with_name("ff")
    log_file = tmp_path / "logs" / "trace.log"
    log_file.parent.mkdir()

    completed = subprocess.run(
        [
            str(ff_command),
            str(top_filelist),
            "--debug",
            "-l",
            str(log_file),
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    terminal = completed.stdout + completed.stderr
    log_content = log_file.read_text(encoding="utf-8")
    assert completed.returncode == 0
    for level, message in (
        ("DEBUG", "flattening input:"),
        ("INFO", "flattened output:"),
    ):
        assert level in terminal
        assert message in terminal
        assert level in log_content
        assert message in log_content
    assert "Log Summary" not in terminal
    assert "Log Summary" not in log_content


def test_cli_controlled_failure_publishes_overwritten_fatal_log(
    tmp_path: Path,
) -> None:
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("missing.sv\n", encoding="utf-8")
    log_file = tmp_path / "failure.log"
    log_file.write_text("stale log\n", encoding="utf-8")
    old_inode = log_file.stat().st_ino
    ff_command = Path(sys.executable).with_name("ff")

    completed = subprocess.run(
        [str(ff_command), str(top_filelist), "-l", str(log_file)],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    terminal = completed.stdout + completed.stderr
    log_content = log_file.read_text(encoding="utf-8")
    assert completed.returncode == 1
    assert "FATAL" in terminal
    assert "source file does not exist" in terminal
    assert "FATAL" in log_content
    assert "source file does not exist" in log_content
    assert "stale log" not in log_content
    assert "Log Summary" not in terminal
    assert "Traceback" not in terminal
    assert log_file.stat().st_ino != old_inode
    assert not (tmp_path / "flattened.f").exists()
