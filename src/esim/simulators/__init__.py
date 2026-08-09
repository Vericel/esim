from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from esim.model import Flow
from esim.workspace import WorkspaceLayout


@dataclass(frozen=True)
class SimulatorPlanRequest:
    flow: Flow
    layout: WorkspaceLayout
    build_argv: tuple[str, ...] = ()
    analyze_argv: tuple[str, ...] = ()
    elaborate_argv: tuple[str, ...] = ()
    run_argv: tuple[str, ...] = ()


@dataclass(frozen=True)
class ToolStep:
    phase: str
    argv: tuple[str, ...]
    log_path: Path
    detector: Callable[[str], tuple[str, ...]]


@dataclass(frozen=True)
class SimulatorPlan:
    build_steps: tuple[ToolStep, ...]
    run_step: ToolStep
    build_artifacts: tuple[Path, ...]
    artifact_validator: Callable[[Path], bool]
    primary_log: Path


class SimulatorAdapter(Protocol):
    def create_plan(self, request: SimulatorPlanRequest) -> SimulatorPlan: ...


class SimulatorRegistry:
    def __init__(self, adapters: Mapping[str, SimulatorAdapter]) -> None:
        self._adapters = dict(adapters)

    @classmethod
    def default(cls) -> SimulatorRegistry:
        from esim.simulators.vcs import VcsAdapter

        return cls({"vcs": VcsAdapter()})

    def create_plan(
        self,
        simulator: str,
        request: SimulatorPlanRequest,
    ) -> SimulatorPlan:
        adapter = self._adapters.get(simulator)
        if adapter is None:
            from esim.errors import ConfigurationError

            raise ConfigurationError(
                f"unsupported simulator adapter\n  simulator: {simulator}"
            )
        return adapter.create_plan(request)


__all__ = [
    "SimulatorPlan",
    "SimulatorPlanRequest",
    "SimulatorRegistry",
    "ToolStep",
]
