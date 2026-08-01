from dataclasses import dataclass, field
from pathlib import Path
from typing import FrozenSet, Optional


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
    output_filelist.write_text(content, encoding="utf-8")
    return FlattenResult(output_filelist=output_filelist)


__all__ = ["FlattenRequest", "FlattenResult", "flatten_filelist"]
