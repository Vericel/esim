from __future__ import annotations

import argparse
import os
import sys
import traceback
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

from esim.application import EsimApplication
from esim.configuration import ConfigurationCompiler
from esim.errors import InputError
from esim.execution import ExecutionEngine
from esim.log_policy import LogPolicy
from esim.model import Action, RunRequest, RunStatus
from esim.process import SubprocessRunner
from esim.simulators import SimulatorRegistry
from esim.workspace import WorkspaceManager


def _warning(message: str) -> None:
    print(f"WARNING: {message}", file=sys.stderr)


def _application(environment: Mapping[str, str]) -> EsimApplication:
    policy = LogPolicy()
    return EsimApplication(
        environment=environment,
        configuration=ConfigurationCompiler(environment=environment),
        workspaces=WorkspaceManager(),
        execution=ExecutionEngine(
            process_runner=SubprocessRunner(),
            log_policy=policy,
        ),
        log_policy=policy,
        simulators=SimulatorRegistry.default(),
        warning=_warning,
    )


def _run_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="esim")
    parser.add_argument("tc")
    parser.add_argument("-f", "--rules")
    parser.add_argument("-a", "--action", choices=("build", "run"))
    parser.add_argument("-k", "--keep", action="store_true")
    parser.add_argument("-b", dest="build_args", action="append", default=[])
    parser.add_argument("-e", dest="elaborate_args", action="append", default=[])
    parser.add_argument("-r", dest="run_args", action="append", default=[])
    parser.add_argument("--debug", action="store_true")
    return parser


def _check_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="esim check")
    parser.add_argument("simulation_directory", type=Path)
    parser.add_argument("--debug", action="store_true")
    return parser


def _normalize_phase_options(arguments: list[str]) -> list[str]:
    phase_options = {"-b", "-e", "-r"}
    cli_options = {
        "-h",
        "--help",
        "-f",
        "--rules",
        "-a",
        "--action",
        "-k",
        "--keep",
        "-b",
        "-e",
        "-r",
        "--debug",
    }
    normalized: list[str] = []
    index = 0
    while index < len(arguments):
        token = arguments[index]
        if (
            token in phase_options
            and index + 1 < len(arguments)
            and arguments[index + 1] not in cli_options
        ):
            normalized.append(f"{token}={arguments[index + 1]}")
            index += 2
            continue
        normalized.append(token)
        index += 1
    return normalized


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(argv) if argv is not None else sys.argv[1:]
    check_mode = bool(arguments and arguments[0] == "check")
    if check_mode:
        parsed = _check_parser().parse_args(arguments[1:])
        debug = cast(bool, parsed.debug)
    else:
        parsed = _run_parser().parse_args(_normalize_phase_options(arguments))
        debug = cast(bool, parsed.debug)
    try:
        if check_mode:
            application = _application(dict(os.environ))
            outcome = application.check(cast(Path, parsed.simulation_directory))
        else:
            action_value = cast(str | None, parsed.action)
            action = Action.FULL if action_value is None else Action(action_value)
            build_args = tuple(cast(list[str], parsed.build_args))
            elaborate_args = tuple(cast(list[str], parsed.elaborate_args))
            run_args = tuple(cast(list[str], parsed.run_args))
            if action is Action.RUN and (build_args or elaborate_args):
                raise InputError("run action only accepts -r phase arguments")
            if action is Action.BUILD and run_args:
                raise InputError("build action does not accept -r phase arguments")
            application = _application(dict(os.environ))
            outcome = application.run(
                RunRequest(
                    tc_selector=cast(str, parsed.tc),
                    rules_selector=cast(str | None, parsed.rules),
                    action=action,
                    keep=cast(bool, parsed.keep),
                    build_args=build_args,
                    elaborate_args=elaborate_args,
                    run_args=run_args,
                )
            )
    except InputError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    except Exception as error:
        print(
            f"ERROR: esim internal error: {type(error).__name__}: {error}",
            file=sys.stderr,
        )
        if debug:
            traceback.print_exc()
        return 3
    print(f"{outcome.status.value}: {outcome.simulation_directory}")
    return 1 if outcome.status is RunStatus.FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["main"]
