from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile


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
