from dataclasses import dataclass, field
import os
from pathlib import Path
import re
from typing import FrozenSet, Optional


_MACRO_NAME_SYNTAX = r"[A-Za-z_][A-Za-z0-9_$]*"
_MACRO_NAME_PATTERN = re.compile(_MACRO_NAME_SYNTAX)
_ENVIRONMENT_VARIABLE_PATTERN = re.compile(
    r"\$(?:([A-Za-z_][A-Za-z0-9_]*)|\{([A-Za-z_][A-Za-z0-9_]*)\})"
)


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


def _source_chain_section(source_chain: tuple[str, ...]) -> str:
    if not source_chain:
        return ""
    rendered_entries = "\n".join(f"    {entry}" for entry in source_chain)
    return f"  source chain:\n{rendered_entries}\n"


def _split_trailing_line_comment(line: str) -> tuple[str, Optional[str]]:
    for index in range(len(line) - 1):
        if line[index : index + 2] != "//":
            continue
        if index == 0 or line[index - 1].isspace():
            return line[:index].rstrip(), line[index:]
    return line, None


def _expand_environment_variables(
    value: str,
    filelist: Path,
    line_number: int,
    source_chain: tuple[str, ...],
) -> str:
    def expand(current_value: str, expansion_chain: tuple[str, ...]) -> str:
        def replace(match: re.Match[str]) -> str:
            name = match.group(1) or match.group(2)
            if name in expansion_chain:
                cycle = expansion_chain + (name,)
                raise FlattenError(
                    "environment variable expansion cycle\n"
                    f"{_source_chain_section(source_chain)}"
                    f"  at: {filelist}:{line_number}\n"
                    f"  input: {value}\n"
                    f"  expansion chain: {' -> '.join(cycle)}\n"
                    "  suggestion: remove the recursive environment "
                    "variable reference"
                )
            if name not in os.environ:
                raise FlattenError(
                    "environment variable is not set\n"
                    f"{_source_chain_section(source_chain)}"
                    f"  at: {filelist}:{line_number}\n"
                    f"  input: {value}\n"
                    f"  variable: {name}\n"
                    f"  suggestion: export {name} before running ff"
                )
            if not os.environ[name]:
                raise FlattenError(
                    "environment variable is empty\n"
                    f"{_source_chain_section(source_chain)}"
                    f"  at: {filelist}:{line_number}\n"
                    f"  input: {value}\n"
                    f"  variable: {name}\n"
                    f"  suggestion: export {name} with a non-empty value "
                    "before running ff"
                )
            return expand(os.environ[name], expansion_chain + (name,))

        return _ENVIRONMENT_VARIABLE_PATTERN.sub(replace, current_value)

    return expand(value, ())


def _flatten_lines(
    filelist: Path,
    path_base: Path,
    request: FlattenRequest,
    filelist_stack: tuple[Path, ...],
    source_chain: tuple[str, ...],
) -> list[str]:
    content = filelist.read_text(encoding="utf-8")
    flattened_lines = []
    active_states = [True]
    branch_taken_states = [False]
    else_seen_states = [False]
    condition_open_lines = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        entry, trailing_comment = _split_trailing_line_comment(line)
        stripped = entry.strip()
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
        if not stripped or stripped.startswith("//"):
            flattened_lines.append(line)
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
            expanded_child_reference = _expand_environment_variables(
                tokens[1],
                filelist,
                line_number,
                source_chain,
            )
            child_filelist = _absolute_logical_path(
                Path(expanded_child_reference),
                child_reference_base,
            )
            if not child_filelist.is_file():
                raise FlattenError(
                    "filelist does not exist\n"
                    f"  at: {filelist}:{line_number}\n"
                    f"  input: {line}\n"
                    f"  resolved: {child_filelist}"
                )
            child_identity = child_filelist.resolve()
            reference = f"{filelist}:{line_number} -> {child_filelist}"
            next_source_chain = source_chain + (reference,)
            if child_identity in filelist_stack:
                rendered_source_chain = "\n".join(
                    f"    {entry}" for entry in next_source_chain
                )
                raise FlattenError(
                    "filelist include cycle\n"
                    "  source chain:\n"
                    f"{rendered_source_chain}"
                )
            if trailing_comment is not None:
                flattened_lines.append(trailing_comment)
            flattened_lines.extend(
                _flatten_lines(
                    child_filelist,
                    child_content_base or child_filelist.parent,
                    request,
                    filelist_stack + (child_identity,),
                    next_source_chain,
                )
            )
            continue
        if len(tokens) == 2 and tokens[0] == "-v":
            expanded_library = _expand_environment_variables(
                tokens[1],
                filelist,
                line_number,
                source_chain,
            )
            library_file = _absolute_logical_path(
                Path(expanded_library),
                path_base,
            )
            if not library_file.is_file():
                raise FlattenError(
                    "library file does not exist\n"
                    f"{_source_chain_section(source_chain)}"
                    f"  at: {filelist}:{line_number}\n"
                    f"  input: {line}\n"
                    f"  resolved: {library_file}"
                )
            rendered_library = f"-v {library_file}"
            if trailing_comment is not None:
                rendered_library = f"{rendered_library} {trailing_comment}"
            flattened_lines.append(rendered_library)
            continue
        if len(tokens) == 2 and tokens[0] == "-y":
            expanded_library_directory = _expand_environment_variables(
                tokens[1],
                filelist,
                line_number,
                source_chain,
            )
            library_directory = _absolute_logical_path(
                Path(expanded_library_directory),
                path_base,
            )
            if not library_directory.is_dir():
                raise FlattenError(
                    "library directory does not exist\n"
                    f"{_source_chain_section(source_chain)}"
                    f"  at: {filelist}:{line_number}\n"
                    f"  input: {line}\n"
                    f"  resolved: {library_directory}"
                )
            rendered_library_directory = f"-y {library_directory}"
            if trailing_comment is not None:
                rendered_library_directory = (
                    f"{rendered_library_directory} {trailing_comment}"
                )
            flattened_lines.append(rendered_library_directory)
            continue
        if stripped.startswith("+incdir+"):
            include_directories = []
            directory_entries = stripped[len("+incdir+") :].split("+")
            if any(not directory_entry for directory_entry in directory_entries):
                raise FlattenError(
                    "invalid +incdir+ syntax\n"
                    f"{_source_chain_section(source_chain)}"
                    f"  at: {filelist}:{line_number}\n"
                    f"  input: {stripped}\n"
                    "  suggestion: provide a non-empty directory after "
                    "every + separator"
                )
            for directory_entry in directory_entries:
                expanded_include_directory = _expand_environment_variables(
                    directory_entry,
                    filelist,
                    line_number,
                    source_chain,
                )
                include_directory = _absolute_logical_path(
                    Path(expanded_include_directory),
                    path_base,
                )
                if not include_directory.is_dir():
                    raise FlattenError(
                        "include directory does not exist\n"
                        f"{_source_chain_section(source_chain)}"
                        f"  at: {filelist}:{line_number}\n"
                        f"  input: {line}\n"
                        f"  resolved: {include_directory}"
                    )
                include_directories.append(f"+incdir+{include_directory}")
            if trailing_comment is not None:
                flattened_lines.append(trailing_comment)
            flattened_lines.extend(include_directories)
            continue
        if stripped.startswith(("-", "+")):
            flattened_lines.append(line)
            continue
        expanded_source = _expand_environment_variables(
            stripped,
            filelist,
            line_number,
            source_chain,
        )
        resolved_source = _absolute_logical_path(Path(expanded_source), path_base)
        if not resolved_source.is_file():
            raise FlattenError(
                "source file does not exist\n"
                f"{_source_chain_section(source_chain)}"
                f"  at: {filelist}:{line_number}\n"
                f"  input: {line}\n"
                f"  resolved: {resolved_source}"
            )
        rendered_source = str(resolved_source)
        if trailing_comment is not None:
            rendered_source = f"{rendered_source} {trailing_comment}"
        flattened_lines.append(rendered_source)
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
        (request.top_filelist.resolve(),),
        (),
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
