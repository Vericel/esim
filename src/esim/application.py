from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import cast

from esim.configuration import CompileRequest, ConfigurationCompiler
from esim.errors import CacheCompatibilityError, InputError
from esim.execution import ExecutionEngine, ExecutionHooks, ExecutionReport, PreparedRun
from esim.log_policy import (
    Finding,
    LogEvaluationRequest,
    LogPolicy,
    WaiverSources,
)
from esim.model import (
    Action,
    Flow,
    IgnoredField,
    PhaseHooks,
    RunOutcome,
    RunRequest,
    RunStatus,
    SimulationIdentity,
)
from esim.simulators import SimulatorPlan, SimulatorPlanRequest, SimulatorRegistry
from esim.workspace import (
    InputSnapshotBundle,
    WorkspaceLayout,
    WorkspaceManager,
    WorkspaceMode,
)
from esim.yaml_codec import decode_mapping, encode_mapping


def _ignore_warning(_message: str) -> None:
    pass


class EsimApplication:
    def __init__(
        self,
        *,
        environment: Mapping[str, str],
        configuration: ConfigurationCompiler,
        workspaces: WorkspaceManager,
        execution: ExecutionEngine,
        log_policy: LogPolicy,
        simulators: SimulatorRegistry,
        warning: Callable[[str], None] | None = None,
    ) -> None:
        self._environment = dict(environment)
        self._configuration = configuration
        self._workspaces = workspaces
        self._execution = execution
        self._log_policy = log_policy
        self._simulators = simulators
        self._warning: Callable[[str], None] = warning or _ignore_warning

    def run(self, request: RunRequest) -> RunOutcome:
        located = self._configuration.locate(request)
        mode = self._workspace_mode(request)
        with self._workspaces.open(located.identity, mode) as workspace:
            cached_state = (
                workspace.load_cached_state()
                if request.action is not Action.FULL
                else None
            )
            compiled = self._configuration.compile(
                CompileRequest(
                    located=located,
                    run_request=request,
                    cached_tc_yaml=(
                        cached_state.tc_yaml if cached_state is not None else None
                    ),
                )
            )
            for ignored in compiled.ignored_fields:
                self._warning(f"ignored field: {ignored.source}: {ignored.path}")
            for diagnostic in compiled.diagnostics:
                chain = " -> ".join(str(path) for path in diagnostic.include_chain)
                self._warning(
                    f"duplicate configuration include skipped: {diagnostic.source}\n"
                    f"  include chain: {chain}"
                )
            testcase = compiled.effective_tc
            analyze_argv = (
                testcase.build.analyze.argv
                if testcase.build.analyze is not None
                else ()
            )
            elaborate_argv = (
                testcase.build.elaborate.argv
                if testcase.build.elaborate is not None
                else ()
            )
            plan = self._simulators.create_plan(
                testcase.simulator,
                SimulatorPlanRequest(
                    flow=testcase.flow,
                    layout=workspace.layout,
                    build_argv=testcase.build.argv,
                    analyze_argv=analyze_argv,
                    elaborate_argv=elaborate_argv,
                    run_argv=testcase.run.argv,
                ),
            )
            self._validate_stage_cache(request.action, workspace.layout, plan)
            dv_home = self._required_path("DV_HOME")
            entry_rules_directory = (
                dv_home / Path(*located.identity.dtb_key.split(".")) / "rules"
            )
            waivers = self._log_policy.compile(
                WaiverSources(
                    common_rules_directory=dv_home / "dtb_common/rules",
                    entry_rules_directory=entry_rules_directory,
                )
            )
            initial_result = self._render_result(
                status=RunStatus.NOT_RUN,
                action=request.action,
                report=None,
                ignored_fields=compiled.ignored_fields,
            )
            workspace.publish_inputs(
                InputSnapshotBundle(
                    rules_yaml=compiled.rules_yaml,
                    tc_yaml=compiled.tc_yaml,
                    waive_text=waivers.rendered_waive,
                    exclude_text=waivers.rendered_exclude,
                )
            )
            workspace.publish_result(initial_result)
            report = self._execution.execute(
                PreparedRun(
                    action=request.action,
                    layout=workspace.layout,
                    top_filelist=testcase.filelist,
                    predefined_macros=testcase.ff.predefined_macros,
                    simulator_plan=plan,
                    waivers=waivers,
                    environment=self._environment,
                    hooks=ExecutionHooks(
                        ff=testcase.ff.hooks,
                        build=testcase.build.hooks,
                        analyze=(
                            testcase.build.analyze.hooks
                            if testcase.build.analyze is not None
                            else PhaseHooks()
                        ),
                        elaborate=(
                            testcase.build.elaborate.hooks
                            if testcase.build.elaborate is not None
                            else PhaseHooks()
                        ),
                        run=testcase.run.hooks,
                    ),
                )
            )
            result_yaml = self._render_result(
                status=report.status,
                action=request.action,
                report=report,
                ignored_fields=compiled.ignored_fields,
            )
            workspace.publish_result(result_yaml)
            return RunOutcome(
                status=report.status,
                simulation_directory=workspace.layout.directory,
                result_yaml=result_yaml,
            )

    def check(self, simulation_directory: Path) -> RunOutcome:
        directory = Path(os.path.abspath(simulation_directory))
        if not simulation_directory.is_absolute():
            raise InputError(
                "check requires an absolute simulation directory\n"
                f"  directory: {simulation_directory}"
            )
        identity = SimulationIdentity(
            dtb_key="check",
            rules_key="check",
            test_key="check",
            directory=directory,
        )
        with self._workspaces.open(identity, WorkspaceMode.CHECK) as workspace:
            cached = workspace.load_cached_state()
            testcase = decode_mapping(cached.tc_yaml, "cached tc.yaml", InputError)
            result = decode_mapping(
                cached.result_yaml, "cached result.yaml", InputError
            )
            simulator = testcase.get("simulator")
            flow_value = testcase.get("flow")
            if not isinstance(simulator, str):
                raise InputError("cached tc.yaml is missing simulator")
            try:
                flow = Flow(flow_value)
            except (TypeError, ValueError) as error:
                raise InputError("cached tc.yaml has an invalid flow") from error
            entry_rules_directory = self._entry_rules_from_snapshot(testcase)
            dv_home = self._required_path("DV_HOME")
            waivers = self._log_policy.compile(
                WaiverSources(
                    common_rules_directory=dv_home / "dtb_common/rules",
                    entry_rules_directory=entry_rules_directory,
                )
            )
            plan = self._simulators.create_plan(
                simulator,
                SimulatorPlanRequest(flow=flow, layout=workspace.layout),
            )
            workspace.publish_waivers(
                waivers.rendered_waive,
                waivers.rendered_exclude,
            )
            if not plan.primary_log.is_file():
                status = self._result_status(result)
                self._warning(
                    "simulation primary log does not exist; status unchanged: "
                    f"{plan.primary_log}"
                )
                return RunOutcome(
                    status=status,
                    simulation_directory=directory,
                    result_yaml=cached.result_yaml,
                )
            evaluation = self._log_policy.evaluate(
                LogEvaluationRequest(
                    phase="run",
                    log_path=plan.primary_log,
                    waivers=waivers,
                    detector=plan.run_step.detector,
                )
            )
            command_failed = self._recorded_run_failed(result)
            status = (
                RunStatus.PASS
                if evaluation.passed and not command_failed
                else RunStatus.FAIL
            )
            result["status"] = status.value
            result["findings"] = [
                self._finding_snapshot(finding) for finding in evaluation.findings
            ]
            result_yaml = encode_mapping(result)
            workspace.publish_result(result_yaml)
            return RunOutcome(
                status=status,
                simulation_directory=directory,
                result_yaml=result_yaml,
            )

    def _entry_rules_from_snapshot(self, testcase: dict[str, object]) -> Path:
        source = testcase.get("source")
        if not isinstance(source, dict):
            raise InputError("cached tc.yaml is missing source.entry_tc")
        entry_tc_value = cast(dict[object, object], source).get("entry_tc")
        if not isinstance(entry_tc_value, str):
            raise InputError("cached tc.yaml is missing source.entry_tc")
        entry_tc = Path(os.path.abspath(entry_tc_value))
        dv_home = self._required_path("DV_HOME")
        try:
            relative = entry_tc.relative_to(dv_home)
            tests_index = relative.parts.index("tests")
        except (ValueError, OSError) as error:
            raise InputError(
                "cached tc.yaml source.entry_tc is outside a legal tests directory\n"
                f"  entry_tc: {entry_tc}"
            ) from error
        if tests_index == 0 or tests_index == len(relative.parts) - 1:
            raise InputError(
                "cached tc.yaml source.entry_tc is outside a legal tests directory\n"
                f"  entry_tc: {entry_tc}"
            )
        return dv_home.joinpath(*relative.parts[:tests_index], "rules")

    @staticmethod
    def _recorded_run_failed(result: dict[str, object]) -> bool:
        commands = result.get("commands")
        if not isinstance(commands, list):
            raise InputError("cached result.yaml commands must be a list")
        for item in cast(list[object], commands):
            if not isinstance(item, dict):
                continue
            command = cast(dict[object, object], item)
            if command.get("node") != "run":
                continue
            returncode = command.get("returncode")
            if not isinstance(returncode, int):
                raise InputError(
                    "cached result.yaml run command has an invalid returncode"
                )
            return returncode != 0
        return False

    @staticmethod
    def _result_status(result: dict[str, object]) -> RunStatus:
        value = result.get("status")
        try:
            return RunStatus(value)
        except (TypeError, ValueError) as error:
            raise InputError("cached result.yaml has an invalid status") from error

    @staticmethod
    def _validate_stage_cache(
        action: Action,
        layout: WorkspaceLayout,
        plan: SimulatorPlan,
    ) -> None:
        if action is Action.FULL:
            return
        if action is Action.BUILD:
            flattened = layout.flattened_filelist
            if not flattened.is_file() or not os.access(flattened, os.R_OK):
                raise CacheCompatibilityError(
                    "required cached flattened filelist is unavailable\n"
                    f"  path: {flattened}"
                )
            return
        invalid = tuple(
            path for path in plan.build_artifacts if not plan.artifact_validator(path)
        )
        if invalid:
            paths = "\n".join(f"  path: {path}" for path in invalid)
            raise CacheCompatibilityError(
                f"required cached simulator artifact is unavailable\n{paths}"
            )

    @staticmethod
    def _workspace_mode(request: RunRequest) -> WorkspaceMode:
        if request.action is not Action.FULL:
            return WorkspaceMode.ACTION
        return WorkspaceMode.KEEP if request.keep else WorkspaceMode.CLEAN

    def _required_path(self, name: str) -> Path:
        value = self._environment.get(name)
        if not value:
            raise InputError(f"missing required environment variable: {name}")
        return Path(os.path.abspath(value))

    @staticmethod
    def _render_result(
        *,
        status: RunStatus,
        action: Action,
        report: ExecutionReport | None,
        ignored_fields: tuple[IgnoredField, ...],
    ) -> str:
        commands = []
        findings: list[dict[str, object]] = []
        if report is not None:
            commands = [
                {
                    "node": command.node,
                    "argv": list(command.argv),
                    "returncode": command.returncode,
                    "log": str(command.log_path),
                }
                for command in report.commands
            ]
            findings = [
                EsimApplication._finding_snapshot(finding)
                for evaluation in report.evaluations
                for finding in evaluation.findings
            ]
        ignored = [
            {"source": str(item.source), "path": item.path} for item in ignored_fields
        ]
        return encode_mapping(
            {
                "status": status.value,
                "action": action.value,
                "commands": commands,
                "findings": findings,
                "ignored_fields": ignored,
            }
        )

    @staticmethod
    def _finding_snapshot(finding: Finding) -> dict[str, object]:
        return {
            "phase": finding.phase,
            "log": str(finding.log_path),
            "line": finding.line_number,
            "text": finding.text,
            "reasons": list(finding.reasons),
            "waived": finding.waived,
            "waiver_hits": [
                {
                    "kind": hit.kind,
                    "pattern": hit.pattern,
                    "source": str(hit.source),
                    "line": hit.line_number,
                }
                for hit in finding.waiver_hits
            ],
        }


__all__ = ["EsimApplication"]
