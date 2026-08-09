from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

from esim.cli import main


def test_cli_maps_a_controlled_input_error_to_exit_two(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.delenv("DV_HOME", raising=False)
    monkeypatch.delenv("DV_TMP", raising=False)

    returncode = main(["xxx.yyy:func.smoke"])

    captured = capsys.readouterr()
    assert returncode == 2
    assert "required environment variable is not set" in captured.err
    assert "variable: DV_HOME" in captured.err
    assert "Traceback" not in captured.err


def test_cli_rejects_phase_arguments_that_do_not_belong_to_the_action(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.delenv("DV_HOME", raising=False)
    monkeypatch.delenv("DV_TMP", raising=False)

    returncode = main(["xxx.yyy:func.smoke", "-a", "run", "-b", "-full64"])

    captured = capsys.readouterr()
    assert returncode == 2
    assert "run action only accepts -r" in captured.err
    assert "DV_HOME" not in captured.err


def test_real_cli_runs_the_demo_through_the_vcs_process_boundary(
    tmp_path: Path,
) -> None:
    fixture = Path(__file__).parent / "fixtures" / "esim-demo-project"
    project = tmp_path / "project"
    shutil.copytree(fixture, project)
    bin_directory = tmp_path / "bin"
    bin_directory.mkdir()
    vcs = bin_directory / "vcs"
    vcs.write_text(
        "#!/bin/bash\n"
        "set -eu\n"
        "output=\n"
        "while (($#)); do\n"
        "  if [[ $1 == -o ]]; then output=$2; shift 2; else shift; fi\n"
        "done\n"
        "printf '#!/bin/bash\\necho UVM_INFO simulation complete\\n' > \"$output\"\n"
        'chmod +x "$output"\n'
        "echo VCS compilation complete\n",
        encoding="utf-8",
    )
    vcs.chmod(0o755)
    dv_tmp = tmp_path / "runs"
    environment = dict(os.environ)
    environment.update(
        {
            "DV_HOME": str(project / "dv"),
            "DV_TMP": str(dv_tmp),
            "PATH": f"{bin_directory}:{environment['PATH']}",
            "PYTHONPATH": str(Path(__file__).parents[1] / "src"),
        }
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "esim.cli",
            "xxx.yyy:func.smoke",
            "-b",
            "-debug_access+all",
            "-r",
            "+ntb_random_seed=17",
        ],
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    simulation_directory = dv_tmp / "xxx.yyy/default/func.smoke"
    result = yaml.safe_load(
        (simulation_directory / "result.yaml").read_text(encoding="utf-8")
    )
    assert result["status"] == "PASS"
    testcase = yaml.safe_load(
        (simulation_directory / "tc.yaml").read_text(encoding="utf-8")
    )
    assert testcase["build"]["args"][-1] == "-debug_access+all"
    assert testcase["run"]["args"][-1] == "+ntb_random_seed=17"
    assert (simulation_directory / "simv").is_file()
    assert "UVM_INFO simulation complete" in (
        simulation_directory / "simv.log"
    ).read_text(encoding="utf-8")
