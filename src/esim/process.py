from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class CommandSpec:
    argv: tuple[str, ...]
    cwd: Path
    log_path: Path
    append: bool = False


@dataclass(frozen=True)
class ProcessResult:
    returncode: int


class ProcessRunner(Protocol):
    def run(self, command: CommandSpec) -> ProcessResult: ...


class SubprocessRunner:
    def run(self, command: CommandSpec) -> ProcessResult:
        mode = "ab" if command.append else "wb"
        with command.log_path.open(mode) as log:
            try:
                completed = subprocess.run(
                    command.argv,
                    cwd=command.cwd,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    check=False,
                    close_fds=True,
                )
            except OSError as error:
                executable = command.argv[0] if command.argv else "<empty argv>"
                log.write(f"cannot execute command: {executable}: {error}\n".encode())
                return ProcessResult(returncode=127)
        return ProcessResult(returncode=completed.returncode)


__all__ = [
    "CommandSpec",
    "ProcessResult",
    "ProcessRunner",
    "SubprocessRunner",
]
