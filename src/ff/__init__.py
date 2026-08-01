from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import FrozenSet, Optional


class FlattenError(Exception):
    pass


@dataclass(frozen=True)
class FlattenRequest:
    top_filelist: Path
    working_directory: Path
    output_filelist: Optional[Path] = None
    predefined_macros: FrozenSet[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class FlattenResult:
    output_filelist: Path


def flatten_filelist(request: FlattenRequest) -> FlattenResult:
    output_filelist = request.output_filelist or (
        request.working_directory / "flattened.f"
    )
    content = request.top_filelist.read_text(encoding="utf-8")
    flattened_lines = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        source = Path(line)
        if not source.is_absolute():
            source = request.top_filelist.parent / source
        resolved_source = Path(os.path.abspath(source))
        if not resolved_source.is_file():
            raise FlattenError(
                "source file does not exist\n"
                f"  at: {request.top_filelist}:{line_number}\n"
                f"  input: {line}\n"
                f"  resolved: {resolved_source}"
            )
        flattened_lines.append(str(resolved_source))
    flattened_content = "\n".join(flattened_lines)
    if flattened_lines:
        flattened_content += "\n"
    output_filelist.write_text(flattened_content, encoding="utf-8")
    return FlattenResult(output_filelist=output_filelist)


__all__ = [
    "FlattenError",
    "FlattenRequest",
    "FlattenResult",
    "flatten_filelist",
]
