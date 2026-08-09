from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from esim.execution import ExecutionEngine, ExecutionHooks, PreparedRun
from esim.log_policy import LogPolicy, WaiverSources
from esim.model import Action, Flow, HookSpec, PhaseHooks, RunStatus
from esim.simulators import SimulatorPlanRequest
from esim.simulators.vcs import VcsAdapter
from esim.workspace import WorkspaceLayout
from ff import FlattenError, FlattenRequest, FlattenResult
from tests.support.esim import (
    ScriptedProcessRunner as _ScriptedProcessRunner,
)
from tests.support.esim import ScriptedResponse as _ScriptedResponse


def test_full_two_step_execution_runs_ff_build_and_run_to_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = Path(__file__).parent / "fixtures" / "esim-demo-project"
    project = tmp_path / "project"
    shutil.copytree(fixture, project)
    dv_home = project / "dv"
    monkeypatch.setenv("DV_HOME", str(dv_home))
    simulation_directory = tmp_path / "runs/xxx.yyy/default/func.smoke"
    simulation_directory.mkdir(parents=True)
    layout = WorkspaceLayout.for_directory(simulation_directory)
    plan = VcsAdapter().create_plan(
        SimulatorPlanRequest(
            flow=Flow.TWO_STEP,
            layout=layout,
            build_argv=("-full64", "-sverilog", "-top", "top_tb"),
            run_argv=("+UVM_TESTNAME=smoke_test",),
        )
    )
    runner = _ScriptedProcessRunner(
        (
            _ScriptedResponse(
                output="VCS compilation complete\n",
                artifacts=(layout.simv,),
            ),
            _ScriptedResponse(output="UVM_INFO simulation complete\n"),
        )
    )
    policy = LogPolicy()
    waivers = policy.compile(
        WaiverSources(
            common_rules_directory=dv_home / "dtb_common/rules",
            entry_rules_directory=dv_home / "xxx/yyy/rules",
        )
    )

    report = ExecutionEngine(
        process_runner=runner,
        log_policy=policy,
    ).execute(
        PreparedRun(
            action=Action.FULL,
            layout=layout,
            top_filelist=dv_home / "xxx/yyy/tb/top.f",
            predefined_macros=frozenset({"ESIM_DEMO"}),
            simulator_plan=plan,
            waivers=waivers,
        )
    )

    assert report.status is RunStatus.PASS
    assert tuple(record.node for record in report.commands) == (
        "ff",
        "build",
        "run",
    )
    assert layout.flattened_filelist.read_text(encoding="utf-8").startswith(
        "+define+ESIM_DEMO\n"
    )
    assert layout.vcs_log.read_text(encoding="utf-8") == ("VCS compilation complete\n")
    assert layout.simv_log.read_text(encoding="utf-8") == (
        "UVM_INFO simulation complete\n"
    )


def test_successful_build_without_required_artifact_does_not_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = Path(__file__).parent / "fixtures" / "esim-demo-project"
    project = tmp_path / "project"
    shutil.copytree(fixture, project)
    dv_home = project / "dv"
    monkeypatch.setenv("DV_HOME", str(dv_home))
    simulation_directory = tmp_path / "simulation"
    simulation_directory.mkdir()
    layout = WorkspaceLayout.for_directory(simulation_directory)
    plan = VcsAdapter().create_plan(
        SimulatorPlanRequest(flow=Flow.TWO_STEP, layout=layout)
    )
    runner = _ScriptedProcessRunner(
        (
            _ScriptedResponse(output="VCS returned zero without simv\n"),
            _ScriptedResponse(output="run must not execute\n"),
        )
    )
    policy = LogPolicy()

    report = ExecutionEngine(process_runner=runner, log_policy=policy).execute(
        PreparedRun(
            action=Action.FULL,
            layout=layout,
            top_filelist=dv_home / "xxx/yyy/tb/top.f",
            predefined_macros=frozenset(),
            simulator_plan=plan,
            waivers=policy.compile(
                WaiverSources(
                    common_rules_directory=tmp_path / "common/rules",
                    entry_rules_directory=tmp_path / "local/rules",
                )
            ),
        )
    )

    assert report.status is RunStatus.FAIL
    assert tuple(record.node for record in report.commands) == ("ff", "build")
    assert not layout.simv_log.exists()


def test_run_hooks_use_independent_bash_commands_and_aggregate_logs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = Path(__file__).parent / "fixtures" / "esim-demo-project"
    project = tmp_path / "project"
    shutil.copytree(fixture, project)
    dv_home = project / "dv"
    monkeypatch.setenv("DV_HOME", str(dv_home))
    simulation_directory = tmp_path / "simulation"
    simulation_directory.mkdir()
    layout = WorkspaceLayout.for_directory(simulation_directory)
    plan = VcsAdapter().create_plan(
        SimulatorPlanRequest(flow=Flow.TWO_STEP, layout=layout)
    )
    runner = _ScriptedProcessRunner(
        (
            _ScriptedResponse(output="build complete\n", artifacts=(layout.simv,)),
            _ScriptedResponse(output="before one\n"),
            _ScriptedResponse(output="before two\n"),
            _ScriptedResponse(output="simulation complete\n"),
            _ScriptedResponse(output="after run\n"),
        )
    )
    policy = LogPolicy()

    report = ExecutionEngine(process_runner=runner, log_policy=policy).execute(
        PreparedRun(
            action=Action.FULL,
            layout=layout,
            top_filelist=dv_home / "xxx/yyy/tb/top.f",
            predefined_macros=frozenset(),
            simulator_plan=plan,
            waivers=policy.compile(
                WaiverSources(
                    common_rules_directory=tmp_path / "common/rules",
                    entry_rules_directory=tmp_path / "local/rules",
                )
            ),
            hooks=ExecutionHooks(
                run=PhaseHooks(
                    before=HookSpec(commands=("echo before-one", "echo before-two")),
                    after=HookSpec(commands=("echo after-run",)),
                )
            ),
        )
    )

    assert report.status is RunStatus.PASS
    assert tuple(record.node for record in report.commands) == (
        "ff",
        "build",
        "run.before[0]",
        "run.before[1]",
        "run",
        "run.after[0]",
    )
    assert runner.commands[1].argv == (
        "/bin/bash",
        "-o",
        "pipefail",
        "-c",
        "echo before-one",
    )
    assert all(command.cwd == simulation_directory for command in runner.commands)
    assert (simulation_directory / "pre_run.log").read_text(encoding="utf-8") == (
        "before one\nbefore two\n"
    )
    assert (simulation_directory / "post_run.log").read_text(encoding="utf-8") == (
        "after run\n"
    )


def test_build_action_reuses_flat_filelist_and_preserves_existing_run_log(
    tmp_path: Path,
) -> None:
    simulation_directory = tmp_path / "simulation"
    simulation_directory.mkdir()
    layout = WorkspaceLayout.for_directory(simulation_directory)
    layout.flattened_filelist.write_text(
        "/project/dut.sv\n",
        encoding="utf-8",
    )
    layout.simv_log.write_text("previous simulation\n", encoding="utf-8")
    plan = VcsAdapter().create_plan(
        SimulatorPlanRequest(flow=Flow.TWO_STEP, layout=layout)
    )
    runner = _ScriptedProcessRunner(
        (
            _ScriptedResponse(output="pre build\n"),
            _ScriptedResponse(output="build complete\n", artifacts=(layout.simv,)),
            _ScriptedResponse(output="post build\n"),
        )
    )
    policy = LogPolicy()

    report = ExecutionEngine(process_runner=runner, log_policy=policy).execute(
        PreparedRun(
            action=Action.BUILD,
            layout=layout,
            top_filelist=tmp_path / "unused.f",
            predefined_macros=frozenset(),
            simulator_plan=plan,
            waivers=policy.compile(
                WaiverSources(
                    common_rules_directory=tmp_path / "common/rules",
                    entry_rules_directory=tmp_path / "local/rules",
                )
            ),
            hooks=ExecutionHooks(
                build=PhaseHooks(
                    before=HookSpec(commands=("echo pre-build",)),
                    after=HookSpec(commands=("echo post-build",)),
                )
            ),
        )
    )

    assert report.status is RunStatus.NOT_RUN
    assert tuple(record.node for record in report.commands) == (
        "build.before[0]",
        "build",
        "build.after[0]",
    )
    assert layout.flattened_filelist.read_text(encoding="utf-8") == (
        "/project/dut.sv\n"
    )
    assert layout.simv_log.read_text(encoding="utf-8") == "previous simulation\n"


def test_run_action_rejects_invalid_vcs_build_artifact_before_execution(
    tmp_path: Path,
) -> None:
    simulation_directory = tmp_path / "simulation"
    simulation_directory.mkdir()
    layout = WorkspaceLayout.for_directory(simulation_directory)
    layout.simv.mkdir()
    plan = VcsAdapter().create_plan(
        SimulatorPlanRequest(flow=Flow.TWO_STEP, layout=layout)
    )
    runner = _ScriptedProcessRunner(
        (_ScriptedResponse(output="run must not execute\n"),)
    )
    policy = LogPolicy()

    report = ExecutionEngine(process_runner=runner, log_policy=policy).execute(
        PreparedRun(
            action=Action.RUN,
            layout=layout,
            top_filelist=tmp_path / "unused.f",
            predefined_macros=frozenset(),
            simulator_plan=plan,
            waivers=policy.compile(
                WaiverSources(
                    common_rules_directory=tmp_path / "common/rules",
                    entry_rules_directory=tmp_path / "local/rules",
                )
            ),
        )
    )

    assert report.status is RunStatus.FAIL
    assert report.commands == ()
    assert not layout.simv_log.exists()


def test_nonzero_tool_exit_still_records_log_findings_and_stops(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = Path(__file__).parent / "fixtures" / "esim-demo-project"
    project = tmp_path / "project"
    shutil.copytree(fixture, project)
    dv_home = project / "dv"
    monkeypatch.setenv("DV_HOME", str(dv_home))
    simulation_directory = tmp_path / "simulation"
    simulation_directory.mkdir()
    layout = WorkspaceLayout.for_directory(simulation_directory)
    plan = VcsAdapter().create_plan(
        SimulatorPlanRequest(flow=Flow.TWO_STEP, layout=layout)
    )
    runner = _ScriptedProcessRunner(
        (_ScriptedResponse(output="Fatal-[COMP] build aborted\n", returncode=2),)
    )
    policy = LogPolicy()

    report = ExecutionEngine(process_runner=runner, log_policy=policy).execute(
        PreparedRun(
            action=Action.FULL,
            layout=layout,
            top_filelist=dv_home / "xxx/yyy/tb/top.f",
            predefined_macros=frozenset(),
            simulator_plan=plan,
            waivers=policy.compile(
                WaiverSources(
                    common_rules_directory=tmp_path / "common/rules",
                    entry_rules_directory=tmp_path / "local/rules",
                )
            ),
        )
    )

    assert report.status is RunStatus.FAIL
    assert tuple(record.node for record in report.commands) == ("ff", "build")
    assert report.commands[-1].returncode == 2
    assert report.evaluations[-1].findings[0].text == "Fatal-[COMP] build aborted"
    assert report.evaluations[-1].findings[0].reasons == ("vcs:fatal",)
    assert not layout.simv_log.exists()


def test_flatten_failure_still_records_ff_log_findings_and_stops(
    tmp_path: Path,
) -> None:
    simulation_directory = tmp_path / "simulation"
    simulation_directory.mkdir()
    layout = WorkspaceLayout.for_directory(simulation_directory)
    plan = VcsAdapter().create_plan(
        SimulatorPlanRequest(flow=Flow.TWO_STEP, layout=layout)
    )
    runner = _ScriptedProcessRunner(())
    policy = LogPolicy()

    def fail_flatten(_request: FlattenRequest) -> FlattenResult:
        raise FlattenError("error while flattening")

    report = ExecutionEngine(
        process_runner=runner,
        log_policy=policy,
        flattener=fail_flatten,
    ).execute(
        PreparedRun(
            action=Action.FULL,
            layout=layout,
            top_filelist=tmp_path / "top.f",
            predefined_macros=frozenset(),
            simulator_plan=plan,
            waivers=policy.compile(
                WaiverSources(
                    common_rules_directory=tmp_path / "common/rules",
                    entry_rules_directory=tmp_path / "local/rules",
                )
            ),
        )
    )

    assert report.status is RunStatus.FAIL
    assert tuple(record.node for record in report.commands) == ("ff",)
    assert report.commands[0].returncode == 1
    assert report.evaluations[-1].findings[0].text == "error while flattening"
    assert report.evaluations[-1].findings[0].reasons == ("generic:error",)
    assert runner.commands == []


def test_three_step_execution_preserves_nested_build_hook_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = Path(__file__).parent / "fixtures" / "esim-demo-project"
    project = tmp_path / "project"
    shutil.copytree(fixture, project)
    dv_home = project / "dv"
    monkeypatch.setenv("DV_HOME", str(dv_home))
    simulation_directory = tmp_path / "simulation"
    simulation_directory.mkdir()
    layout = WorkspaceLayout.for_directory(simulation_directory)
    plan = VcsAdapter().create_plan(
        SimulatorPlanRequest(flow=Flow.THREE_STEP, layout=layout)
    )
    runner = _ScriptedProcessRunner(
        (
            _ScriptedResponse(output="build before\n"),
            _ScriptedResponse(output="analyze before\n"),
            _ScriptedResponse(output="analysis complete\n"),
            _ScriptedResponse(output="analyze after\n"),
            _ScriptedResponse(output="elaborate before\n"),
            _ScriptedResponse(
                output="elaboration complete\n",
                artifacts=(layout.simv,),
            ),
            _ScriptedResponse(output="elaborate after\n"),
            _ScriptedResponse(output="build after\n"),
            _ScriptedResponse(output="run before\n"),
            _ScriptedResponse(output="simulation complete\n"),
            _ScriptedResponse(output="run after\n"),
        )
    )
    policy = LogPolicy()

    def one_command(text: str) -> HookSpec:
        return HookSpec(commands=(f"echo {text}",))

    report = ExecutionEngine(process_runner=runner, log_policy=policy).execute(
        PreparedRun(
            action=Action.FULL,
            layout=layout,
            top_filelist=dv_home / "xxx/yyy/tb/top.f",
            predefined_macros=frozenset(),
            simulator_plan=plan,
            waivers=policy.compile(
                WaiverSources(
                    common_rules_directory=tmp_path / "common/rules",
                    entry_rules_directory=tmp_path / "local/rules",
                )
            ),
            hooks=ExecutionHooks(
                build=PhaseHooks(
                    before=one_command("build-before"),
                    after=one_command("build-after"),
                ),
                analyze=PhaseHooks(
                    before=one_command("analyze-before"),
                    after=one_command("analyze-after"),
                ),
                elaborate=PhaseHooks(
                    before=one_command("elaborate-before"),
                    after=one_command("elaborate-after"),
                ),
                run=PhaseHooks(
                    before=one_command("run-before"),
                    after=one_command("run-after"),
                ),
            ),
        )
    )

    assert report.status is RunStatus.PASS
    assert tuple(record.node for record in report.commands) == (
        "ff",
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
    )


def test_hook_continue_on_error_finishes_only_the_current_hook_then_stops(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = Path(__file__).parent / "fixtures" / "esim-demo-project"
    project = tmp_path / "project"
    shutil.copytree(fixture, project)
    dv_home = project / "dv"
    monkeypatch.setenv("DV_HOME", str(dv_home))
    simulation_directory = tmp_path / "simulation"
    simulation_directory.mkdir()
    layout = WorkspaceLayout.for_directory(simulation_directory)
    plan = VcsAdapter().create_plan(
        SimulatorPlanRequest(flow=Flow.TWO_STEP, layout=layout)
    )
    runner = _ScriptedProcessRunner(
        (
            _ScriptedResponse(output="first command stopped\n", returncode=9),
            _ScriptedResponse(output="cleanup command completed\n"),
        )
    )
    policy = LogPolicy()

    report = ExecutionEngine(process_runner=runner, log_policy=policy).execute(
        PreparedRun(
            action=Action.FULL,
            layout=layout,
            top_filelist=dv_home / "xxx/yyy/tb/top.f",
            predefined_macros=frozenset(),
            simulator_plan=plan,
            waivers=policy.compile(
                WaiverSources(
                    common_rules_directory=tmp_path / "common/rules",
                    entry_rules_directory=tmp_path / "local/rules",
                )
            ),
            hooks=ExecutionHooks(
                build=PhaseHooks(
                    before=HookSpec(
                        commands=("command-one", "command-two"),
                        continue_on_error=True,
                    )
                )
            ),
        )
    )

    assert report.status is RunStatus.FAIL
    assert tuple(record.node for record in report.commands) == (
        "ff",
        "build.before[0]",
        "build.before[1]",
    )
    assert tuple(record.returncode for record in report.commands) == (0, 9, 0)
    assert layout.hook_log("build", "before").read_text(encoding="utf-8") == (
        "first command stopped\ncleanup command completed\n"
    )
    assert not layout.vcs_log.exists()
