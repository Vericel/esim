from pathlib import Path

import pytest

from esim.errors import ConfigurationError
from esim.model import Flow
from esim.simulators import SimulatorPlanRequest
from esim.simulators.vcs import VcsAdapter
from esim.workspace import WorkspaceLayout


def test_two_step_plan_uses_managed_inputs_outputs_and_logs(tmp_path: Path) -> None:
    simulation_directory = tmp_path / "runs/xxx.yyy/default/func.smoke"
    layout = WorkspaceLayout.for_directory(simulation_directory)

    plan = VcsAdapter().create_plan(
        SimulatorPlanRequest(
            flow=Flow.TWO_STEP,
            layout=layout,
            build_argv=("-full64", "-sverilog"),
            run_argv=("+UVM_TESTNAME=smoke_test", "+ntb_random_seed=1"),
        )
    )

    assert plan.build_steps[0].phase == "build"
    assert plan.build_steps[0].argv == (
        "vcs",
        "-f",
        str(simulation_directory / "flattened.f"),
        "-full64",
        "-sverilog",
        "-o",
        str(simulation_directory / "simv"),
        "-l",
        str(simulation_directory / "vcs.log"),
    )
    assert plan.run_step.argv == (
        str(simulation_directory / "simv"),
        "+UVM_TESTNAME=smoke_test",
        "+ntb_random_seed=1",
        "-l",
        str(simulation_directory / "simv.log"),
    )
    assert plan.build_artifacts == (simulation_directory / "simv",)
    assert plan.primary_log == simulation_directory / "simv.log"


def test_three_step_plan_splits_analyze_and_elaborate_commands(
    tmp_path: Path,
) -> None:
    simulation_directory = tmp_path / "runs/xxx.yyy/three_step/func.smoke"
    layout = WorkspaceLayout.for_directory(simulation_directory)

    plan = VcsAdapter().create_plan(
        SimulatorPlanRequest(
            flow=Flow.THREE_STEP,
            layout=layout,
            analyze_argv=("-full64", "-sverilog"),
            elaborate_argv=("top_tb", "-debug_access+all"),
            run_argv=("+UVM_TESTNAME=smoke_test",),
        )
    )

    assert tuple(step.phase for step in plan.build_steps) == (
        "analyze",
        "elaborate",
    )
    assert plan.build_steps[0].argv == (
        "vlogan",
        "-f",
        str(simulation_directory / "flattened.f"),
        "-full64",
        "-sverilog",
        "-l",
        str(simulation_directory / "vlogan.log"),
    )
    assert plan.build_steps[1].argv == (
        "vcs",
        "top_tb",
        "-debug_access+all",
        "-o",
        str(simulation_directory / "simv"),
        "-l",
        str(simulation_directory / "vcs.log"),
    )


def test_plan_rejects_user_option_that_overrides_a_managed_path(
    tmp_path: Path,
) -> None:
    layout = WorkspaceLayout.for_directory(tmp_path / "simulation")

    with pytest.raises(ConfigurationError) as captured:
        VcsAdapter().create_plan(
            SimulatorPlanRequest(
                flow=Flow.TWO_STEP,
                layout=layout,
                build_argv=("-full64", "-o", "custom-simv"),
            )
        )

    assert str(captured.value) == (
        "VCS option conflicts with an esim-managed path\n  phase: build\n  option: -o"
    )


def test_vcs_steps_detect_fatal_lines_not_found_by_generic_keywords(
    tmp_path: Path,
) -> None:
    plan = VcsAdapter().create_plan(
        SimulatorPlanRequest(
            flow=Flow.TWO_STEP,
            layout=WorkspaceLayout.for_directory(tmp_path / "simulation"),
        )
    )

    assert plan.build_steps[0].detector("Fatal-[SOME_CODE] compilation stopped") == (
        "vcs:fatal",
    )
    assert plan.run_step.detector("UVM_FATAL @ 100: test aborted") == ("vcs:fatal",)
