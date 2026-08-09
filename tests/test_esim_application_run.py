from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from esim.application import EsimApplication
from esim.configuration import ConfigurationCompiler
from esim.errors import CacheCompatibilityError
from esim.execution import ExecutionEngine
from esim.log_policy import LogPolicy
from esim.model import Action, RunRequest, RunStatus
from esim.simulators import SimulatorRegistry
from esim.workspace import WorkspaceManager
from tests.support.esim import ScriptedProcessRunner, ScriptedResponse


def test_application_runs_full_two_step_flow_and_publishes_auditable_result(
    tmp_path: Path,
) -> None:
    fixture = Path(__file__).parent / "fixtures" / "esim-demo-project"
    project = tmp_path / "project"
    shutil.copytree(fixture, project)
    dv_home = project / "dv"
    dv_tmp = tmp_path / "runs"
    simulation_directory = dv_tmp / "xxx.yyy/default/func.smoke"
    runner = ScriptedProcessRunner(
        (
            ScriptedResponse(output="ff setup complete\n"),
            ScriptedResponse(
                output="VCS compilation complete\n",
                artifacts=(simulation_directory / "simv",),
            ),
            ScriptedResponse(output="base setup complete\n"),
            ScriptedResponse(output="smoke setup complete\n"),
            ScriptedResponse(output="UVM_INFO simulation complete\n"),
            ScriptedResponse(output="post processing complete\n"),
        )
    )
    environment = {"DV_HOME": str(dv_home), "DV_TMP": str(dv_tmp)}
    log_policy = LogPolicy()
    application = EsimApplication(
        environment=environment,
        configuration=ConfigurationCompiler(environment=environment),
        workspaces=WorkspaceManager(),
        execution=ExecutionEngine(
            process_runner=runner,
            log_policy=log_policy,
        ),
        log_policy=log_policy,
        simulators=SimulatorRegistry.default(),
    )

    outcome = application.run(RunRequest(tc_selector="xxx.yyy:func.smoke"))

    assert outcome.status is RunStatus.PASS
    assert outcome.simulation_directory == simulation_directory
    assert (simulation_directory / "rules.yaml").is_file()
    assert (simulation_directory / "tc.yaml").is_file()
    assert (simulation_directory / "flattened.f").is_file()
    assert (
        (simulation_directory / "waive.txt")
        .read_text(encoding="utf-8")
        .startswith(f"// source: {dv_home / 'dtb_common/rules/waive.txt'}\n")
    )
    result = yaml.safe_load(
        (simulation_directory / "result.yaml").read_text(encoding="utf-8")
    )
    assert result["status"] == "PASS"
    assert result["action"] == "full"
    assert [command["node"] for command in result["commands"]] == [
        "ff.before[0]",
        "ff",
        "build",
        "run.before[0]",
        "run.before[1]",
        "run",
        "run.after[0]",
    ]
    assert result["findings"] == []
    assert result["ignored_fields"] == []
    assert all(command.cwd == simulation_directory for command in runner.commands)


def test_complete_three_step_demo_runs_every_nested_hook_and_cli_argument(
    tmp_path: Path,
) -> None:
    fixture = Path(__file__).parent / "fixtures" / "esim-demo-project"
    project = tmp_path / "project"
    shutil.copytree(fixture, project)
    dv_home = project / "dv"
    dv_tmp = tmp_path / "runs"
    simulation_directory = dv_tmp / "xxx.zzz/full/features.complete"
    runner = ScriptedProcessRunner(
        (
            ScriptedResponse(output="common ff setup complete\n"),
            ScriptedResponse(output="zzz ff post-processing complete\n"),
            ScriptedResponse(output="zzz build setup complete\n"),
            ScriptedResponse(output="zzz analyze setup complete\n"),
            ScriptedResponse(output="VCS analysis complete\n"),
            ScriptedResponse(output="zzz analyze post-processing complete\n"),
            ScriptedResponse(output="zzz elaborate setup complete\n"),
            ScriptedResponse(
                output="VCS elaboration complete\n",
                artifacts=(simulation_directory / "simv",),
            ),
            ScriptedResponse(output="zzz elaborate post-processing complete\n"),
            ScriptedResponse(output="zzz build post-processing complete\n"),
            ScriptedResponse(output="zzz run setup complete\n"),
            ScriptedResponse(output="UVM_INFO complete simulation\n"),
            ScriptedResponse(output="zzz run post-processing complete\n"),
        )
    )
    environment = {"DV_HOME": str(dv_home), "DV_TMP": str(dv_tmp)}
    log_policy = LogPolicy()
    application = EsimApplication(
        environment=environment,
        configuration=ConfigurationCompiler(environment=environment),
        workspaces=WorkspaceManager(),
        execution=ExecutionEngine(process_runner=runner, log_policy=log_policy),
        log_policy=log_policy,
        simulators=SimulatorRegistry.default(),
    )

    outcome = application.run(
        RunRequest(
            tc_selector="xxx.zzz:features.complete",
            rules_selector="full",
            build_args=("-kdb",),
            elaborate_args=("-debug_access+all",),
            run_args=("+CLI=1",),
        )
    )

    assert outcome.status is RunStatus.PASS
    result = yaml.safe_load(
        (simulation_directory / "result.yaml").read_text(encoding="utf-8")
    )
    assert [command["node"] for command in result["commands"]] == [
        "ff.before[0]",
        "ff",
        "ff.after[0]",
        "build.before[0]",
        "analyze.before[0]",
        "analyze",
        "analyze.after[0]",
        "elaborate.before[0]",
        "elaborate",
        "elaborate.after[0]",
        "build.after[0]",
        "run.before[0]",
        "run",
        "run.after[0]",
    ]
    commands = {command["node"]: command["argv"] for command in result["commands"]}
    assert commands["analyze"][3:-2] == [
        "-full64",
        "-sverilog",
        "+define+COMPLETE_ZZZ",
        "-kdb",
    ]
    assert commands["elaborate"][1:-4] == [
        "-full64",
        "top_tb",
        "-debug_access+all",
    ]
    assert commands["run"][1:-2] == [
        "+UVM_VERBOSITY=UVM_LOW",
        "+ntb_random_seed=31",
        "+ESIM_DEMO_BASE=zzz-complete",
        "+ESIM_DEMO_CASE=complete",
        "+CLI=1",
    ]
    assert result["findings"] == []
    assert (simulation_directory / "vlogan.log").is_file()
    assert (simulation_directory / "vcs.log").is_file()
    assert (simulation_directory / "simv.log").is_file()


def test_complete_yaml_demo_publishes_every_auditable_workspace_artifact(
    tmp_path: Path,
) -> None:
    fixture = Path(__file__).parent / "fixtures" / "esim-demo-project"
    project = tmp_path / "project"
    shutil.copytree(fixture, project)
    dv_home = project / "dv"
    dv_tmp = tmp_path / "runs"
    yyy_home = dv_home / "xxx/yyy"
    simulation_directory = dv_tmp / "xxx.yyy/full/features.complete"
    simulation_directory.mkdir(parents=True)
    (simulation_directory / "stale.txt").write_text("stale\n", encoding="utf-8")
    responses = [ScriptedResponse(output="phase complete\n") for _ in range(16)]
    responses[6] = ScriptedResponse(
        output="VCS compilation complete\n",
        artifacts=(simulation_directory / "simv",),
    )
    responses[13] = ScriptedResponse(output="UVM_INFO complete simulation\n")
    runner = ScriptedProcessRunner(tuple(responses))
    environment = {
        "DV_HOME": str(dv_home),
        "DV_TMP": str(dv_tmp),
        "ESIM_DEMO_CONFIG_ROOT": str(yyy_home),
        "ESIM_DEMO_YYY_RULES": "$ESIM_DEMO_CONFIG_ROOT/rules",
        "ESIM_DEMO_YYY_TESTS": "${ESIM_DEMO_CONFIG_ROOT}/tests",
        "ESIM_DEMO_FILELIST": "$ESIM_DEMO_CONFIG_ROOT/tb/full.f",
        "ESIM_DEMO_LABEL": "alpha beta",
        "ESIM_DEMO_SEED": "23",
        "FF_DEMO_ROOT": "$ESIM_DEMO_CONFIG_ROOT/tb/ff_features",
        "FF_DEMO_SOURCE_ROOT": "${FF_DEMO_ROOT}/sources",
        "FF_DEMO_INCLUDE_ROOT": "$FF_DEMO_ROOT/include",
        "FF_DEMO_LIBRARY_FILE": "$FF_DEMO_ROOT/library/ff_demo_cells.sv",
        "FF_DEMO_LIBRARY_DIR": "${FF_DEMO_ROOT}/library/search",
        "FF_DEMO_WORKING_FILELIST": "$FF_DEMO_ROOT/working/working.f",
    }
    warnings: list[str] = []
    log_policy = LogPolicy()
    application = EsimApplication(
        environment=environment,
        configuration=ConfigurationCompiler(environment=environment),
        workspaces=WorkspaceManager(),
        execution=ExecutionEngine(process_runner=runner, log_policy=log_policy),
        log_policy=log_policy,
        simulators=SimulatorRegistry.default(),
        warning=warnings.append,
    )

    outcome = application.run(
        RunRequest(
            tc_selector="xxx.yyy:features.complete",
            rules_selector="full",
        )
    )

    assert outcome.status is RunStatus.PASS
    assert not (simulation_directory / "stale.txt").exists()
    flattened = (simulation_directory / "flattened.f").read_text(encoding="utf-8")
    assert "+define+COMPLETE_YYY\n" in flattened
    assert str(yyy_home / "tb/rtl/feature_monitor.sv") in flattened
    assert "inactive_missing.sv" not in flattened
    rules_snapshot = yaml.safe_load(
        (simulation_directory / "rules.yaml").read_text(encoding="utf-8")
    )
    tc_snapshot = yaml.safe_load(
        (simulation_directory / "tc.yaml").read_text(encoding="utf-8")
    )
    assert rules_snapshot["source"]["entry"] == str(yyy_home / "rules/full.yaml")
    assert tc_snapshot["source"]["entry_tc"] == str(
        yyy_home / "tests/features/complete.yaml"
    )
    assert tc_snapshot["source"]["merge_order"][-1] == str(
        yyy_home / "tests/features/complete.yaml"
    )
    result = yaml.safe_load(
        (simulation_directory / "result.yaml").read_text(encoding="utf-8")
    )
    assert result["status"] == "PASS"
    assert {item["path"] for item in result["ignored_fields"]} == {
        "metadata",
        "ff.timeout",
        "run.enabled",
    }
    assert len(warnings) == 7
    duplicate_warnings = [
        warning
        for warning in warnings
        if warning.startswith("duplicate configuration include skipped:")
    ]
    assert len(duplicate_warnings) == 3
    assert all("include chain:" in warning for warning in duplicate_warnings)
    for name in (
        "pre_ff.log",
        "post_ff.log",
        "pre_build.log",
        "post_build.log",
        "pre_run.log",
        "post_run.log",
        "ff.log",
        "vcs.log",
        "simv.log",
        "waive.txt",
        "exclude.txt",
        "simv",
    ):
        assert (simulation_directory / name).exists(), name


def test_run_action_rejects_changed_build_configuration_before_commands(
    tmp_path: Path,
) -> None:
    fixture = Path(__file__).parent / "fixtures" / "esim-demo-project"
    project = tmp_path / "project"
    shutil.copytree(fixture, project)
    dv_home = project / "dv"
    dv_tmp = tmp_path / "runs"
    simulation_directory = dv_tmp / "xxx.yyy/default/func.smoke"
    environment = {"DV_HOME": str(dv_home), "DV_TMP": str(dv_tmp)}
    initial_runner = ScriptedProcessRunner(
        (
            ScriptedResponse(output="ff setup complete\n"),
            ScriptedResponse(
                output="VCS compilation complete\n",
                artifacts=(simulation_directory / "simv",),
            ),
            ScriptedResponse(output="base setup complete\n"),
            ScriptedResponse(output="smoke setup complete\n"),
            ScriptedResponse(output="UVM_INFO simulation complete\n"),
            ScriptedResponse(output="post processing complete\n"),
        )
    )
    initial_policy = LogPolicy()
    EsimApplication(
        environment=environment,
        configuration=ConfigurationCompiler(environment=environment),
        workspaces=WorkspaceManager(),
        execution=ExecutionEngine(
            process_runner=initial_runner,
            log_policy=initial_policy,
        ),
        log_policy=initial_policy,
        simulators=SimulatorRegistry.default(),
    ).run(RunRequest(tc_selector="xxx.yyy:func.smoke"))
    rules_path = dv_home / "xxx/yyy/rules/default.yaml"
    rules_path.write_text(
        rules_path.read_text(encoding="utf-8").replace(
            "-full64 -sverilog -top top_tb",
            "-full64 -sverilog -top top_tb -debug_access+all",
        ),
        encoding="utf-8",
    )
    action_runner = ScriptedProcessRunner(())
    action_policy = LogPolicy()
    application = EsimApplication(
        environment=environment,
        configuration=ConfigurationCompiler(environment=environment),
        workspaces=WorkspaceManager(),
        execution=ExecutionEngine(
            process_runner=action_runner,
            log_policy=action_policy,
        ),
        log_policy=action_policy,
        simulators=SimulatorRegistry.default(),
    )

    with pytest.raises(CacheCompatibilityError, match="build"):
        application.run(
            RunRequest(
                tc_selector="xxx.yyy:func.smoke",
                action=Action.RUN,
            )
        )

    assert action_runner.commands == []


@pytest.mark.parametrize(
    ("action", "missing_name"),
    (
        (Action.BUILD, "flattened.f"),
        (Action.RUN, "simv"),
    ),
)
def test_stage_action_rejects_missing_required_cache_before_publishing_inputs(
    tmp_path: Path,
    action: Action,
    missing_name: str,
) -> None:
    fixture = Path(__file__).parent / "fixtures" / "esim-demo-project"
    project = tmp_path / "project"
    shutil.copytree(fixture, project)
    dv_home = project / "dv"
    dv_tmp = tmp_path / "runs"
    simulation_directory = dv_tmp / "xxx.yyy/default/func.smoke"
    environment = {"DV_HOME": str(dv_home), "DV_TMP": str(dv_tmp)}
    initial_runner = ScriptedProcessRunner(
        (
            ScriptedResponse(output="ff setup complete\n"),
            ScriptedResponse(
                output="VCS compilation complete\n",
                artifacts=(simulation_directory / "simv",),
            ),
            ScriptedResponse(output="base setup complete\n"),
            ScriptedResponse(output="smoke setup complete\n"),
            ScriptedResponse(output="UVM_INFO simulation complete\n"),
            ScriptedResponse(output="post processing complete\n"),
        )
    )
    initial_policy = LogPolicy()
    EsimApplication(
        environment=environment,
        configuration=ConfigurationCompiler(environment=environment),
        workspaces=WorkspaceManager(),
        execution=ExecutionEngine(
            process_runner=initial_runner,
            log_policy=initial_policy,
        ),
        log_policy=initial_policy,
        simulators=SimulatorRegistry.default(),
    ).run(RunRequest(tc_selector="xxx.yyy:func.smoke"))
    cached_tc = (simulation_directory / "tc.yaml").read_text(encoding="utf-8")
    (simulation_directory / missing_name).unlink()
    action_runner = ScriptedProcessRunner(())
    action_policy = LogPolicy()
    application = EsimApplication(
        environment=environment,
        configuration=ConfigurationCompiler(environment=environment),
        workspaces=WorkspaceManager(),
        execution=ExecutionEngine(
            process_runner=action_runner,
            log_policy=action_policy,
        ),
        log_policy=action_policy,
        simulators=SimulatorRegistry.default(),
    )

    with pytest.raises(CacheCompatibilityError, match=missing_name):
        application.run(RunRequest(tc_selector="xxx.yyy:func.smoke", action=action))

    assert action_runner.commands == []
    assert (simulation_directory / "tc.yaml").read_text(encoding="utf-8") == cached_tc


def test_build_then_run_actions_reuse_only_their_required_upstream_cache(
    tmp_path: Path,
) -> None:
    fixture = Path(__file__).parent / "fixtures" / "esim-demo-project"
    project = tmp_path / "project"
    shutil.copytree(fixture, project)
    dv_home = project / "dv"
    dv_tmp = tmp_path / "runs"
    simulation_directory = dv_tmp / "xxx.yyy/default/func.smoke"
    environment = {"DV_HOME": str(dv_home), "DV_TMP": str(dv_tmp)}
    initial_runner = ScriptedProcessRunner(
        (
            ScriptedResponse(output="ff setup complete\n"),
            ScriptedResponse(
                output="VCS compilation complete\n",
                artifacts=(simulation_directory / "simv",),
            ),
            ScriptedResponse(output="base setup complete\n"),
            ScriptedResponse(output="smoke setup complete\n"),
            ScriptedResponse(output="UVM_INFO initial simulation complete\n"),
            ScriptedResponse(output="post processing complete\n"),
        )
    )
    initial_policy = LogPolicy()
    EsimApplication(
        environment=environment,
        configuration=ConfigurationCompiler(environment=environment),
        workspaces=WorkspaceManager(),
        execution=ExecutionEngine(
            process_runner=initial_runner,
            log_policy=initial_policy,
        ),
        log_policy=initial_policy,
        simulators=SimulatorRegistry.default(),
    ).run(RunRequest(tc_selector="xxx.yyy:func.smoke"))
    flattened_before = (simulation_directory / "flattened.f").read_text(
        encoding="utf-8"
    )
    simulation_log_before = (simulation_directory / "simv.log").read_text(
        encoding="utf-8"
    )

    build_runner = ScriptedProcessRunner(
        (
            ScriptedResponse(
                output="VCS rebuild complete\n",
                artifacts=(simulation_directory / "simv",),
            ),
        )
    )
    build_policy = LogPolicy()
    build_outcome = EsimApplication(
        environment=environment,
        configuration=ConfigurationCompiler(environment=environment),
        workspaces=WorkspaceManager(),
        execution=ExecutionEngine(
            process_runner=build_runner,
            log_policy=build_policy,
        ),
        log_policy=build_policy,
        simulators=SimulatorRegistry.default(),
    ).run(
        RunRequest(
            tc_selector="xxx.yyy:func.smoke",
            action=Action.BUILD,
        )
    )

    assert build_outcome.status is RunStatus.NOT_RUN
    assert [command.argv[0] for command in build_runner.commands] == ["vcs"]
    assert (simulation_directory / "flattened.f").read_text(
        encoding="utf-8"
    ) == flattened_before
    assert (simulation_directory / "simv.log").read_text(
        encoding="utf-8"
    ) == simulation_log_before

    run_runner = ScriptedProcessRunner(
        (
            ScriptedResponse(output="base setup complete\n"),
            ScriptedResponse(output="smoke setup complete\n"),
            ScriptedResponse(output="UVM_INFO rerun complete\n"),
            ScriptedResponse(output="post processing complete\n"),
        )
    )
    run_policy = LogPolicy()
    run_outcome = EsimApplication(
        environment=environment,
        configuration=ConfigurationCompiler(environment=environment),
        workspaces=WorkspaceManager(),
        execution=ExecutionEngine(
            process_runner=run_runner,
            log_policy=run_policy,
        ),
        log_policy=run_policy,
        simulators=SimulatorRegistry.default(),
    ).run(
        RunRequest(
            tc_selector="xxx.yyy:func.smoke",
            action=Action.RUN,
            run_args=("+ntb_random_seed=99",),
        )
    )

    assert run_outcome.status is RunStatus.PASS
    assert [command.argv[0] for command in run_runner.commands] == [
        "/bin/bash",
        "/bin/bash",
        str(simulation_directory / "simv"),
        "/bin/bash",
    ]
    assert "+ntb_random_seed=99" in run_runner.commands[2].argv
