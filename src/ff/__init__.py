from dataclasses import dataclass, field
import os
from pathlib import Path
import re
from typing import FrozenSet, Optional


_MACRO_NAME_SYNTAX = r"[A-Za-z_][A-Za-z0-9_$]*"
_MACRO_NAME_PATTERN = re.compile(_MACRO_NAME_SYNTAX)


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


def _absolute_logical_path(path: Path, base_directory: Path) -> Path:
    if not path.is_absolute():
        path = base_directory / path
    return Path(os.path.abspath(path))


def _flatten_lines(
    filelist: Path,
    path_base: Path,
    request: FlattenRequest,
) -> list[str]:
    content = filelist.read_text(encoding="utf-8")
    flattened_lines = []
    active_states = [True]
    branch_taken_states = [False]
    else_seen_states = [False]
    condition_open_lines = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        tokens = stripped.split()
        expected_condition_usage = {
            "`ifdef": "`ifdef MACRO",
            "`ifndef": "`ifndef MACRO",
            "`elsif": "`elsif MACRO",
            "`else": "`else",
            "`endif": "`endif",
        }
        if tokens and tokens[0] in expected_condition_usage:
            expected_token_count = (
                1 if tokens[0] in {"`else", "`endif"} else 2
            )
            if len(tokens) != expected_token_count:
                raise FlattenError(
                    "invalid conditional directive syntax\n"
                    f"  at: {filelist}:{line_number}\n"
                    f"  input: {stripped}\n"
                    f"  expected: {expected_condition_usage[tokens[0]]}"
                )
            if (
                expected_token_count == 2
                and _MACRO_NAME_PATTERN.fullmatch(tokens[1]) is None
            ):
                raise FlattenError(
                    "invalid conditional macro name\n"
                    f"  at: {filelist}:{line_number}\n"
                    f"  macro: {tokens[1]}\n"
                    f"  expected: {_MACRO_NAME_SYNTAX}"
                )
        if stripped.startswith("`ifdef "):
            macro = stripped.split(maxsplit=1)[1]
            branch_selected = (
                active_states[-1] and macro in request.predefined_macros
            )
            active_states.append(branch_selected)
            branch_taken_states.append(branch_selected)
            else_seen_states.append(False)
            condition_open_lines.append(line_number)
            continue
        if stripped.startswith("`ifndef "):
            macro = stripped.split(maxsplit=1)[1]
            branch_selected = (
                active_states[-1] and macro not in request.predefined_macros
            )
            active_states.append(branch_selected)
            branch_taken_states.append(branch_selected)
            else_seen_states.append(False)
            condition_open_lines.append(line_number)
            continue
        if stripped.startswith("`elsif "):
            if len(active_states) == 1:
                raise FlattenError(
                    "unexpected `elsif without a matching condition\n"
                    f"  at: {filelist}:{line_number}"
                )
            if else_seen_states[-1]:
                raise FlattenError(
                    "unexpected `elsif after `else\n"
                    f"  at: {filelist}:{line_number}"
                )
            macro = stripped.split(maxsplit=1)[1]
            branch_selected = (
                active_states[-2]
                and not branch_taken_states[-1]
                and macro in request.predefined_macros
            )
            active_states[-1] = branch_selected
            branch_taken_states[-1] = (
                branch_taken_states[-1] or branch_selected
            )
            continue
        if stripped == "`else":
            if len(active_states) == 1:
                raise FlattenError(
                    "unexpected `else without a matching condition\n"
                    f"  at: {filelist}:{line_number}"
                )
            if else_seen_states[-1]:
                raise FlattenError(
                    "unexpected `else after `else\n"
                    f"  at: {filelist}:{line_number}"
                )
            else_seen_states[-1] = True
            branch_selected = (
                active_states[-2] and not branch_taken_states[-1]
            )
            active_states[-1] = branch_selected
            branch_taken_states[-1] = (
                branch_taken_states[-1] or branch_selected
            )
            continue
        if stripped == "`endif":
            if len(active_states) == 1:
                raise FlattenError(
                    "unexpected `endif without a matching condition\n"
                    f"  at: {filelist}:{line_number}"
                )
            active_states.pop()
            branch_taken_states.pop()
            else_seen_states.pop()
            condition_open_lines.pop()
            continue
        if not active_states[-1]:
            continue
        if stripped.startswith("`"):
            raise FlattenError(
                "unsupported backtick directive\n"
                f"  at: {filelist}:{line_number}\n"
                f"  input: {stripped}\n"
                "  supported: `ifdef, `ifndef, `elsif, `else, `endif"
            )
        if len(tokens) == 2 and tokens[0] in {"-f", "-F"}:
            child_reference_base = (
                request.working_directory
                if tokens[0] == "-f"
                else filelist.parent
            )
            child_content_base = (
                request.working_directory
                if tokens[0] == "-f"
                else None
            )
            child_filelist = _absolute_logical_path(
                Path(tokens[1]),
                child_reference_base,
            )
            if not child_filelist.is_file():
                raise FlattenError(
                    "filelist does not exist\n"
                    f"  at: {filelist}:{line_number}\n"
                    f"  input: {line}\n"
                    f"  resolved: {child_filelist}"
                )
            flattened_lines.extend(
                _flatten_lines(
                    child_filelist,
                    child_content_base or child_filelist.parent,
                    request,
                )
            )
            continue
        resolved_source = _absolute_logical_path(Path(line), path_base)
        if not resolved_source.is_file():
            raise FlattenError(
                "source file does not exist\n"
                f"  at: {filelist}:{line_number}\n"
                f"  input: {line}\n"
                f"  resolved: {resolved_source}"
            )
        flattened_lines.append(str(resolved_source))
    if condition_open_lines:
        raise FlattenError(
            "unterminated conditional block\n"
            f"  opened at: {filelist}:{condition_open_lines[-1]}"
        )
    return flattened_lines


def flatten_filelist(request: FlattenRequest) -> FlattenResult:
    for macro in sorted(request.predefined_macros):
        if _MACRO_NAME_PATTERN.fullmatch(macro) is None:
            raise FlattenError(
                "invalid predefined macro name\n"
                f"  macro: {macro}\n"
                f"  expected: {_MACRO_NAME_SYNTAX}"
            )
    output_filelist = request.output_filelist or (
        request.working_directory / "flattened.f"
    )
    flattened_lines = _flatten_lines(
        request.top_filelist,
        request.top_filelist.parent,
        request,
    )
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
