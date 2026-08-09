from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from esim.application import EsimApplication
from esim.configuration import ConfigurationCompiler
from esim.execution import ExecutionEngine
from esim.log_policy import LogPolicy
from esim.model import RunStatus
from esim.simulators import SimulatorRegistry
from esim.workspace import WorkspaceManager
from tests.support.esim import ScriptedProcessRunner


@pytest.mark.parametrize(
    ("run_returncode", "expected_status"),
    ((0, RunStatus.PASS), (9, RunStatus.FAIL)),
)
def test_check_rebuilds_waivers_and_preserves_recorded_run_command_failure(
    tmp_path: Path,
    run_returncode: int,
    expected_status: RunStatus,
) -> None:
    dv_home = tmp_path / "project/dv"
    common_rules = dv_home / "dtb_common/rules"
    entry_rules = dv_home / "xxx/yyy/rules"
    test_directory = dv_home / "xxx/yyy/tests/func"
    common_rules.mkdir(parents=True)
    entry_rules.mkdir(parents=True)
    test_directory.mkdir(parents=True)
    entry_tc = test_directory / "smoke.tc"
    entry_tc.write_text("run: {}\n", encoding="utf-8")
    simulation_directory = tmp_path / "runs/xxx.yyy/default/func.smoke"
    simulation_directory.mkdir(parents=True)
    (simulation_directory / "rules.yaml").write_text(
        "name: default\n",
        encoding="utf-8",
    )
    (simulation_directory / "tc.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "smoke",
                "simulator": "vcs",
                "flow": "two-step",
                "source": {"entry_tc": str(entry_tc)},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (simulation_directory / "result.yaml").write_text(
        yaml.safe_dump(
            {
                "status": "FAIL",
                "action": "full",
                "commands": [
                    {
                        "node": "run",
                        "argv": [str(simulation_directory / "simv")],
                        "returncode": run_returncode,
                        "log": str(simulation_directory / "simv.log"),
                    }
                ],
                "findings": [{"text": "EXPECTED_ERROR"}],
                "ignored_fields": [],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (simulation_directory / "simv.log").write_text(
        "EXPECTED_ERROR from scoreboard\n",
        encoding="utf-8",
    )
    (entry_rules / "waive.txt").write_text(
        "*EXPECTED_ERROR*\n",
        encoding="utf-8",
    )
    runner = ScriptedProcessRunner(())
    policy = LogPolicy()
    application = EsimApplication(
        environment={"DV_HOME": str(dv_home)},
        configuration=ConfigurationCompiler(
            environment={"DV_HOME": str(dv_home), "DV_TMP": str(tmp_path / "runs")}
        ),
        workspaces=WorkspaceManager(),
        execution=ExecutionEngine(process_runner=runner, log_policy=policy),
        log_policy=policy,
        simulators=SimulatorRegistry.default(),
    )

    outcome = application.check(simulation_directory)

    assert outcome.status is expected_status
    assert runner.commands == []
    result = yaml.safe_load(
        (simulation_directory / "result.yaml").read_text(encoding="utf-8")
    )
    assert result["status"] == expected_status.value
    assert result["commands"][0]["returncode"] == run_returncode
    assert result["findings"][0]["waived"] is True
    assert (simulation_directory / "waive.txt").read_text(encoding="utf-8") == (
        f"// source: {entry_rules / 'waive.txt'}\n*EXPECTED_ERROR*\n"
    )


def test_check_warns_and_preserves_status_when_the_primary_log_is_missing(
    tmp_path: Path,
) -> None:
    dv_home = tmp_path / "project/dv"
    common_rules = dv_home / "dtb_common/rules"
    entry_rules = dv_home / "xxx/yyy/rules"
    test_directory = dv_home / "xxx/yyy/tests/func"
    common_rules.mkdir(parents=True)
    entry_rules.mkdir(parents=True)
    test_directory.mkdir(parents=True)
    entry_tc = test_directory / "smoke.tc"
    entry_tc.write_text("run: {}\n", encoding="utf-8")
    simulation_directory = tmp_path / "runs/xxx.yyy/default/func.smoke"
    simulation_directory.mkdir(parents=True)
    (simulation_directory / "rules.yaml").write_text(
        "name: default\n", encoding="utf-8"
    )
    (simulation_directory / "tc.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "smoke",
                "simulator": "vcs",
                "flow": "two-step",
                "source": {"entry_tc": str(entry_tc)},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    original_result = yaml.safe_dump(
        {
            "status": "NOT_RUN",
            "action": "build",
            "commands": [],
            "findings": [],
            "ignored_fields": [],
        },
        sort_keys=False,
    )
    (simulation_directory / "result.yaml").write_text(
        original_result,
        encoding="utf-8",
    )
    (common_rules / "waive.txt").write_text("*KNOWN_ERROR*\n", encoding="utf-8")
    warnings: list[str] = []
    runner = ScriptedProcessRunner(())
    policy = LogPolicy()
    application = EsimApplication(
        environment={"DV_HOME": str(dv_home)},
        configuration=ConfigurationCompiler(
            environment={"DV_HOME": str(dv_home), "DV_TMP": str(tmp_path / "runs")}
        ),
        workspaces=WorkspaceManager(),
        execution=ExecutionEngine(process_runner=runner, log_policy=policy),
        log_policy=policy,
        simulators=SimulatorRegistry.default(),
        warning=warnings.append,
    )

    outcome = application.check(simulation_directory)

    assert outcome.status is RunStatus.NOT_RUN
    assert (simulation_directory / "result.yaml").read_text(
        encoding="utf-8"
    ) == original_result
    assert (simulation_directory / "waive.txt").read_text(encoding="utf-8") == (
        f"// source: {common_rules / 'waive.txt'}\n*KNOWN_ERROR*\n"
    )
    assert warnings == [
        f"simulation primary log does not exist; status unchanged: "
        f"{simulation_directory / 'simv.log'}"
    ]
