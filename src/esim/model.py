from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class Action(Enum):
    FULL = "full"
    BUILD = "build"
    RUN = "run"


class Flow(Enum):
    TWO_STEP = "two-step"
    THREE_STEP = "three-step"


class RunStatus(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_RUN = "NOT_RUN"


@dataclass(frozen=True)
class PhaseHooks:
    before: tuple[str, ...] = ()
    after: tuple[str, ...] = ()
    continue_on_error: bool = False


@dataclass(frozen=True)
class RunRequest:
    tc_selector: str
    rules_selector: str | None = None
    action: Action = Action.FULL
    keep: bool = False
    build_args: tuple[str, ...] = ()
    elaborate_args: tuple[str, ...] = ()
    run_args: tuple[str, ...] = ()


@dataclass(frozen=True)
class SimulationIdentity:
    dtb_key: str
    rules_key: str
    test_key: str
    directory: Path


@dataclass(frozen=True)
class LocatedInvocation:
    entry_tc: Path
    entry_rules: Path
    identity: SimulationIdentity


@dataclass(frozen=True)
class PhaseConfiguration:
    args: tuple[str, ...]
    argv: tuple[str, ...]
    hooks: PhaseHooks


@dataclass(frozen=True)
class FfConfiguration:
    args: tuple[str, ...]
    predefined_macros: frozenset[str]
    hooks: PhaseHooks


@dataclass(frozen=True)
class BuildConfiguration:
    args: tuple[str, ...]
    argv: tuple[str, ...]
    hooks: PhaseHooks
    analyze: PhaseConfiguration | None
    elaborate: PhaseConfiguration | None


@dataclass(frozen=True)
class ResolvedRules:
    name: str
    description: str | None
    tags: tuple[str, ...]
    filelist: Path
    simulator: str
    flow: Flow
    ff: FfConfiguration
    build: BuildConfiguration
    run: PhaseConfiguration
    entry_rules: Path
    merge_order: tuple[Path, ...]


@dataclass(frozen=True)
class EffectiveTestcase(ResolvedRules):
    owner: str | None
    entry_tc: Path


@dataclass(frozen=True)
class IgnoredField:
    source: Path
    path: str


@dataclass(frozen=True)
class ConfigurationDiagnostic:
    kind: str
    source: Path
    include_chain: tuple[Path, ...]


@dataclass(frozen=True)
class CompiledInvocation:
    resolved_rules: ResolvedRules
    effective_tc: EffectiveTestcase
    ignored_fields: tuple[IgnoredField, ...]
    diagnostics: tuple[ConfigurationDiagnostic, ...]
    rules_yaml: str
    tc_yaml: str


@dataclass(frozen=True)
class RunOutcome:
    status: RunStatus
    simulation_directory: Path
    result_yaml: str
