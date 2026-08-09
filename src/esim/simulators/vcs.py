from __future__ import annotations

import os
import stat
from pathlib import Path

from esim.errors import ConfigurationError
from esim.model import Flow
from esim.simulators import SimulatorPlan, SimulatorPlanRequest, ToolStep


def _vcs_detector(text: str) -> tuple[str, ...]:
    return ("vcs:fatal",) if "fatal" in text.lower() else ()


def _is_executable_file(path: Path) -> bool:
    if not path.is_file():
        return False
    mode = stat.S_IMODE(path.stat().st_mode)
    return bool(mode & 0o111) and os.access(path, os.X_OK)


class VcsAdapter:
    def create_plan(self, request: SimulatorPlanRequest) -> SimulatorPlan:
        layout = request.layout
        if request.flow is Flow.TWO_STEP:
            self._reject_managed_options("build", request.build_argv)
            build_steps = (
                ToolStep(
                    phase="build",
                    argv=(
                        "vcs",
                        "-f",
                        str(layout.flattened_filelist),
                        *request.build_argv,
                        "-o",
                        str(layout.simv),
                        "-l",
                        str(layout.vcs_log),
                    ),
                    log_path=layout.vcs_log,
                    detector=_vcs_detector,
                ),
            )
        else:
            self._reject_managed_options("analyze", request.analyze_argv)
            self._reject_managed_options("elaborate", request.elaborate_argv)
            build_steps = (
                ToolStep(
                    phase="analyze",
                    argv=(
                        "vlogan",
                        "-f",
                        str(layout.flattened_filelist),
                        *request.analyze_argv,
                        "-l",
                        str(layout.vlogan_log),
                    ),
                    log_path=layout.vlogan_log,
                    detector=_vcs_detector,
                ),
                ToolStep(
                    phase="elaborate",
                    argv=(
                        "vcs",
                        *request.elaborate_argv,
                        "-o",
                        str(layout.simv),
                        "-l",
                        str(layout.vcs_log),
                    ),
                    log_path=layout.vcs_log,
                    detector=_vcs_detector,
                ),
            )
        self._reject_managed_options("run", request.run_argv)
        run_step = ToolStep(
            phase="run",
            argv=(
                str(layout.simv),
                *request.run_argv,
                "-l",
                str(layout.simv_log),
            ),
            log_path=layout.simv_log,
            detector=_vcs_detector,
        )
        return SimulatorPlan(
            build_steps=build_steps,
            run_step=run_step,
            build_artifacts=(layout.simv,),
            artifact_validator=_is_executable_file,
            primary_log=layout.simv_log,
        )

    @staticmethod
    def _reject_managed_options(phase: str, argv: tuple[str, ...]) -> None:
        for option in argv:
            if option not in {"-f", "-o", "-l"}:
                continue
            raise ConfigurationError(
                "VCS option conflicts with an esim-managed path\n"
                f"  phase: {phase}\n"
                f"  option: {option}"
            )


__all__ = ["VcsAdapter"]
