from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from esim.log_policy import (
    CompiledWaivers,
    LogEvaluation,
    LogEvaluationRequest,
    LogPolicy,
)
from esim.model import Action, PhaseHooks, RunStatus
from esim.process import CommandSpec, ProcessRunner
from esim.simulators import SimulatorPlan, ToolStep
from esim.workspace import WorkspaceLayout
from ff import FlattenError, FlattenRequest, FlattenResult, flatten_filelist


@dataclass(frozen=True)
class ExecutionHooks:
    ff: PhaseHooks = field(default_factory=PhaseHooks)
    build: PhaseHooks = field(default_factory=PhaseHooks)
    analyze: PhaseHooks = field(default_factory=PhaseHooks)
    elaborate: PhaseHooks = field(default_factory=PhaseHooks)
    run: PhaseHooks = field(default_factory=PhaseHooks)


@dataclass(frozen=True)
class PreparedRun:
    action: Action
    layout: WorkspaceLayout
    top_filelist: Path
    predefined_macros: frozenset[str]
    simulator_plan: SimulatorPlan
    waivers: CompiledWaivers
    hooks: ExecutionHooks = field(default_factory=ExecutionHooks)
    environment: Mapping[str, str] | None = None


@dataclass(frozen=True)
class CommandRecord:
    node: str
    argv: tuple[str, ...]
    returncode: int
    log_path: Path


@dataclass(frozen=True)
class ExecutionReport:
    status: RunStatus
    commands: tuple[CommandRecord, ...]
    evaluations: tuple[LogEvaluation, ...]


Flattener = Callable[[FlattenRequest], FlattenResult]


class ExecutionEngine:
    def __init__(
        self,
        *,
        process_runner: ProcessRunner,
        log_policy: LogPolicy,
        flattener: Flattener = flatten_filelist,
    ) -> None:
        self._process_runner = process_runner
        self._log_policy = log_policy
        self._flattener = flattener

    def execute(self, run: PreparedRun) -> ExecutionReport:
        commands: list[CommandRecord] = []
        evaluations: list[LogEvaluation] = []
        if run.action is Action.FULL and not self._execute_ff(
            run,
            commands,
            evaluations,
        ):
            return self._report(RunStatus.FAIL, commands, evaluations)
        if run.action in {Action.FULL, Action.BUILD} and not self._execute_build(
            run,
            commands,
            evaluations,
        ):
            return self._report(RunStatus.FAIL, commands, evaluations)
        if run.action is Action.BUILD:
            return self._report(RunStatus.NOT_RUN, commands, evaluations)
        if not self._execute_run(run, commands, evaluations):
            return self._report(RunStatus.FAIL, commands, evaluations)
        return self._report(RunStatus.PASS, commands, evaluations)

    def _execute_ff(
        self,
        run: PreparedRun,
        commands: list[CommandRecord],
        evaluations: list[LogEvaluation],
    ) -> bool:
        if not self._hook(
            run,
            "ff",
            "before",
            run.hooks.ff.before,
            run.hooks.ff.continue_on_error,
            commands,
            evaluations,
        ):
            return False
        command_passed = self._flatten(run, commands)
        log_passed = self._evaluate_log(
            run,
            "ff",
            run.layout.ff_log,
            None,
            evaluations,
        )
        if not command_passed or not log_passed:
            return False
        return self._hook(
            run,
            "ff",
            "after",
            run.hooks.ff.after,
            run.hooks.ff.continue_on_error,
            commands,
            evaluations,
        )

    def _execute_build(
        self,
        run: PreparedRun,
        commands: list[CommandRecord],
        evaluations: list[LogEvaluation],
    ) -> bool:
        if not self._hook(
            run,
            "build",
            "before",
            run.hooks.build.before,
            run.hooks.build.continue_on_error,
            commands,
            evaluations,
        ):
            return False
        for step in run.simulator_plan.build_steps:
            phase_hooks = getattr(run.hooks, step.phase)
            if step.phase != "build" and not self._hook(
                run,
                step.phase,
                "before",
                phase_hooks.before,
                phase_hooks.continue_on_error,
                commands,
                evaluations,
            ):
                return False
            if not self._tool(run, step, commands, evaluations):
                return False
            if step.phase != "build" and not self._hook(
                run,
                step.phase,
                "after",
                phase_hooks.after,
                phase_hooks.continue_on_error,
                commands,
                evaluations,
            ):
                return False
        if not self._artifacts_valid(run.simulator_plan):
            return False
        return self._hook(
            run,
            "build",
            "after",
            run.hooks.build.after,
            run.hooks.build.continue_on_error,
            commands,
            evaluations,
        )

    def _execute_run(
        self,
        run: PreparedRun,
        commands: list[CommandRecord],
        evaluations: list[LogEvaluation],
    ) -> bool:
        if not self._artifacts_valid(run.simulator_plan):
            return False
        return (
            self._hook(
                run,
                "run",
                "before",
                run.hooks.run.before,
                run.hooks.run.continue_on_error,
                commands,
                evaluations,
            )
            and self._tool(
                run,
                run.simulator_plan.run_step,
                commands,
                evaluations,
            )
            and self._hook(
                run,
                "run",
                "after",
                run.hooks.run.after,
                run.hooks.run.continue_on_error,
                commands,
                evaluations,
            )
        )

    @staticmethod
    def _artifacts_valid(plan: SimulatorPlan) -> bool:
        return all(plan.artifact_validator(path) for path in plan.build_artifacts)

    def _flatten(
        self,
        run: PreparedRun,
        commands: list[CommandRecord],
    ) -> bool:
        run.layout.ff_log.write_text("", encoding="utf-8")
        argv = (
            "ff",
            str(run.top_filelist),
            "-o",
            str(run.layout.flattened_filelist),
            "-l",
            str(run.layout.ff_log),
        )
        try:
            self._flattener(
                FlattenRequest(
                    top_filelist=run.top_filelist,
                    working_directory=run.layout.directory,
                    output_filelist=run.layout.flattened_filelist,
                    predefined_macros=run.predefined_macros,
                    log_file=run.layout.ff_log,
                    environment=run.environment,
                )
            )
        except FlattenError as error:
            run.layout.ff_log.write_text(f"{error}\n", encoding="utf-8")
            commands.append(
                CommandRecord(
                    node="ff",
                    argv=argv,
                    returncode=1,
                    log_path=run.layout.ff_log,
                )
            )
            return False
        commands.append(
            CommandRecord(
                node="ff",
                argv=argv,
                returncode=0,
                log_path=run.layout.ff_log,
            )
        )
        return True

    def _tool(
        self,
        run: PreparedRun,
        step: ToolStep,
        commands: list[CommandRecord],
        evaluations: list[LogEvaluation],
    ) -> bool:
        result = self._process_runner.run(
            CommandSpec(
                argv=step.argv,
                cwd=run.layout.directory,
                log_path=step.log_path,
            )
        )
        commands.append(
            CommandRecord(
                node=step.phase,
                argv=step.argv,
                returncode=result.returncode,
                log_path=step.log_path,
            )
        )
        log_passed = self._evaluate_log(
            run,
            step.phase,
            step.log_path,
            step.detector,
            evaluations,
        )
        return result.returncode == 0 and log_passed

    def _hook(
        self,
        run: PreparedRun,
        phase: str,
        timing: str,
        hook_commands: tuple[str, ...],
        continue_on_error: bool,
        commands: list[CommandRecord],
        evaluations: list[LogEvaluation],
    ) -> bool:
        if not hook_commands:
            return True
        log_path = run.layout.hook_log(phase, timing)
        command_failed = False
        for index, command in enumerate(hook_commands):
            argv = ("/bin/bash", "-o", "pipefail", "-c", command)
            result = self._process_runner.run(
                CommandSpec(
                    argv=argv,
                    cwd=run.layout.directory,
                    log_path=log_path,
                    append=index > 0,
                )
            )
            commands.append(
                CommandRecord(
                    node=f"{phase}.{timing}[{index}]",
                    argv=argv,
                    returncode=result.returncode,
                    log_path=log_path,
                )
            )
            if result.returncode != 0:
                command_failed = True
                if not continue_on_error:
                    break
        log_passed = self._evaluate_log(
            run,
            f"{phase}.{timing}",
            log_path,
            None,
            evaluations,
        )
        return not command_failed and log_passed

    def _evaluate_log(
        self,
        run: PreparedRun,
        phase: str,
        log_path: Path,
        detector: Callable[[str], tuple[str, ...]] | None,
        evaluations: list[LogEvaluation],
    ) -> bool:
        evaluation = self._log_policy.evaluate(
            LogEvaluationRequest(
                phase=phase,
                log_path=log_path,
                waivers=run.waivers,
                detector=detector,
            )
        )
        evaluations.append(evaluation)
        return evaluation.passed

    @staticmethod
    def _report(
        status: RunStatus,
        commands: list[CommandRecord],
        evaluations: list[LogEvaluation],
    ) -> ExecutionReport:
        return ExecutionReport(
            status=status,
            commands=tuple(commands),
            evaluations=tuple(evaluations),
        )


__all__ = [
    "CommandRecord",
    "ExecutionEngine",
    "ExecutionHooks",
    "ExecutionReport",
    "PreparedRun",
]
