import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile


def test_esim_wheel_preserves_the_standalone_ff_command(
    tmp_path: Path,
) -> None:
    project_root = Path(__file__).parents[1]
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            str(project_root),
            "--no-build-isolation",
            "--no-deps",
            "--wheel-dir",
            str(tmp_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    wheel = next(tmp_path.glob("esim-*.whl"))
    with ZipFile(wheel) as archive:
        metadata_name = next(
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        )
        metadata = archive.read(metadata_name).decode("utf-8")
        entry_points_name = next(
            name for name in archive.namelist() if name.endswith("entry_points.txt")
        )
        entry_points = archive.read(entry_points_name).decode("utf-8")

    assert "Name: esim" in metadata
    assert "Version: 0.2.0" in metadata
    assert "Requires-Python: >=3.11" in metadata
    assert "ff = ff.cli:main" in entry_points


def test_wheel_uses_versioned_onelog_dependency(tmp_path: Path) -> None:
    project_root = Path(__file__).parents[1]
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            str(project_root),
            "--no-build-isolation",
            "--no-deps",
            "--wheel-dir",
            str(tmp_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    wheel = next(tmp_path.glob("esim-*.whl"))
    with ZipFile(wheel) as archive:
        names = archive.namelist()
        metadata_name = next(
            name for name in names if name.endswith(".dist-info/METADATA")
        )
        metadata = archive.read(metadata_name).decode("utf-8")

    assert "ff/_vendor/onelog.py" not in names
    assert "Requires-Dist: botticelle-onelog<0.2,>=0.1" in metadata


def test_wheelhouse_builder_preserves_and_rejects_nonempty_output(
    tmp_path: Path,
) -> None:
    project_root = Path(__file__).parents[1]
    output = tmp_path / "wheelhouse"
    output.mkdir()
    existing = output / "existing.whl"
    existing.write_text("keep", encoding="utf-8")

    completed = subprocess.run(
        [
            "bash",
            str(project_root / "scripts" / "build-wheelhouse.sh"),
            str(output),
        ],
        cwd=project_root,
        check=False,
        capture_output=True,
        text=True,
    )

    assert (completed.returncode, completed.stdout, completed.stderr) == (
        2,
        "",
        f"wheelhouse output must be empty: {output}\n",
    )
    assert existing.read_text(encoding="utf-8") == "keep"
