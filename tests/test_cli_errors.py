import os
import subprocess
import sys
from pathlib import Path

import pytest


def test_cli_reports_flatten_error_without_python_traceback(tmp_path: Path) -> None:
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("missing.sv\n", encoding="utf-8")
    ff_command = Path(sys.executable).with_name("ff")

    completed = subprocess.run(
        [str(ff_command), str(top_filelist)],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    terminal = completed.stdout + completed.stderr
    assert completed.returncode == 1
    assert "FATAL" in terminal
    assert "source file does not exist" in terminal
    assert "top.f" in terminal
    assert "missing.sv" in terminal
    assert "Traceback" not in terminal
    assert "Log Summary" not in terminal
    assert not (tmp_path / "flattened.f").exists()
    assert not (tmp_path / "app.log").exists()


def test_cli_requires_input_to_be_the_first_argument(tmp_path: Path) -> None:
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("", encoding="utf-8")
    ff_command = Path(sys.executable).with_name("ff")

    completed = subprocess.run(
        [str(ff_command), "-o", "out.f", str(top_filelist)],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert "INPUT must be the first argument" in completed.stderr
    assert not (tmp_path / "out.f").exists()


def test_cli_rejects_log_and_flattened_output_identity_conflict(
    tmp_path: Path,
) -> None:
    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("top.sv\n", encoding="utf-8")
    ff_command = Path(sys.executable).with_name("ff")
    artifact = tmp_path / "artifact.f"

    completed = subprocess.run(
        [
            str(ff_command),
            str(top_filelist),
            "-o",
            str(artifact),
            "-l",
            str(artifact),
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 1
    assert "log path conflicts with flattened output" in (
        completed.stdout + completed.stderr
    )
    assert not artifact.exists()


def test_cli_rejects_log_and_top_filelist_identity_conflict(
    tmp_path: Path,
) -> None:
    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    original_filelist = "top.sv\n"
    top_filelist.write_text(original_filelist, encoding="utf-8")
    ff_command = Path(sys.executable).with_name("ff")

    completed = subprocess.run(
        [str(ff_command), str(top_filelist), "-l", str(top_filelist)],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert "log path conflicts with input filelist" in (
        completed.stdout + completed.stderr
    )
    assert top_filelist.read_text(encoding="utf-8") == original_filelist
    assert not (tmp_path / "flattened.f").exists()


def test_cli_rejects_log_and_nested_filelist_identity_conflict(
    tmp_path: Path,
) -> None:
    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    child_filelist = tmp_path / "child.f"
    original_child = "top.sv\n"
    child_filelist.write_text(original_child, encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("-F child.f\n", encoding="utf-8")
    ff_command = Path(sys.executable).with_name("ff")

    completed = subprocess.run(
        [str(ff_command), str(top_filelist), "-l", str(child_filelist)],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert "log path conflicts with input filelist" in (
        completed.stdout + completed.stderr
    )
    assert child_filelist.read_text(encoding="utf-8") == original_child
    assert not (tmp_path / "flattened.f").exists()


def test_cli_replaces_log_symlink_node_without_touching_target(
    tmp_path: Path,
) -> None:
    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("top.sv\n", encoding="utf-8")
    log_target = tmp_path / "preserved.log"
    log_target.write_text("target stays\n", encoding="utf-8")
    log_file = tmp_path / "ff.log"
    log_file.symlink_to(log_target)
    ff_command = Path(sys.executable).with_name("ff")

    completed = subprocess.run(
        [str(ff_command), str(top_filelist), "-l", str(log_file)],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert not log_file.is_symlink()
    assert log_file.read_text(encoding="utf-8") == ""
    assert log_target.read_text(encoding="utf-8") == "target stays\n"


def test_cli_reports_missing_log_parent_without_traceback(tmp_path: Path) -> None:
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("", encoding="utf-8")
    log_file = tmp_path / "missing" / "ff.log"
    ff_command = Path(sys.executable).with_name("ff")

    completed = subprocess.run(
        [str(ff_command), str(top_filelist), "-l", str(log_file)],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert completed.stdout == ""
    assert "log parent directory does not exist" in completed.stderr
    assert str(log_file.parent) in completed.stderr
    assert "Traceback" not in completed.stderr
    assert not (tmp_path / "flattened.f").exists()


@pytest.mark.parametrize(
    ("case", "expected_error"),
    [
        ("parent_file", "log parent is not a directory"),
        ("read_only_parent", "log parent directory is not writable"),
        ("other_only_parent", "log parent directory is not writable"),
        ("target_directory", "log path is not a regular file"),
    ],
)
def test_cli_validates_log_path_type_and_parent_access(
    tmp_path: Path,
    case: str,
    expected_error: str,
) -> None:
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("", encoding="utf-8")
    if case == "parent_file":
        parent = tmp_path / "parent-file"
        parent.write_text("content\n", encoding="utf-8")
        log_file = parent / "ff.log"
    else:
        parent = tmp_path / "logs"
        parent.mkdir()
        log_file = parent / "ff.log"
        if case in {"read_only_parent", "other_only_parent"}:
            parent.chmod(0o555 if case == "read_only_parent" else 0o003)
        else:
            log_file.mkdir()
    ff_command = Path(sys.executable).with_name("ff")

    completed = subprocess.run(
        [str(ff_command), str(top_filelist), "-l", str(log_file)],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )
    if case in {"read_only_parent", "other_only_parent"}:
        parent.chmod(0o700)

    assert completed.returncode == 1
    assert expected_error in completed.stderr
    assert "Traceback" not in completed.stderr
    assert not (tmp_path / "flattened.f").exists()


def test_cli_returns_three_for_unexpected_internal_failure(tmp_path: Path) -> None:
    source = tmp_path / "top.sv"
    source.write_text("module top; endmodule\n", encoding="utf-8")
    top_filelist = tmp_path / "top.f"
    top_filelist.write_text("top.sv\n", encoding="utf-8")
    fault_injection = tmp_path / "fault-injection"
    fault_injection.mkdir()
    (fault_injection / "sitecustomize.py").write_text(
        "import os\n"
        "_real_replace = os.replace\n"
        "def _injected_replace(source, destination):\n"
        "    if str(destination).endswith('flattened.f'):\n"
        "        raise RuntimeError('injected replace failure')\n"
        "    return _real_replace(source, destination)\n"
        "os.replace = _injected_replace\n",
        encoding="utf-8",
    )
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(fault_injection)
    ff_command = Path(sys.executable).with_name("ff")

    completed = subprocess.run(
        [str(ff_command), str(top_filelist)],
        cwd=tmp_path,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    terminal = completed.stdout + completed.stderr
    assert completed.returncode == 3
    assert "ERROR" in terminal
    assert "ff internal error: RuntimeError: injected replace failure" in terminal
    assert "Traceback" not in terminal
    assert not (tmp_path / "flattened.f").exists()
