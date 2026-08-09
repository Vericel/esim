from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from esim.process import CommandSpec, ProcessResult


@dataclass(frozen=True)
class ScriptedResponse:
    output: str
    returncode: int = 0
    artifacts: tuple[Path, ...] = ()


class ScriptedProcessRunner:
    def __init__(self, responses: tuple[ScriptedResponse, ...]) -> None:
        self._responses = iter(responses)
        self.commands: list[CommandSpec] = []

    def run(self, command: CommandSpec) -> ProcessResult:
        self.commands.append(command)
        response = next(self._responses)
        mode = "a" if command.append else "w"
        with command.log_path.open(mode, encoding="utf-8") as stream:
            stream.write(response.output)
        for artifact in response.artifacts:
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.write_text("scripted artifact\n", encoding="utf-8")
            artifact.chmod(0o755)
        return ProcessResult(returncode=response.returncode)
