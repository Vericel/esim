from dataclasses import dataclass, field
import os
from pathlib import Path
import re
import stat
import tempfile
from typing import FrozenSet, Optional, Protocol


_MACRO_NAME_SYNTAX = r"[A-Za-z_][A-Za-z0-9_$]*"
_MACRO_NAME_PATTERN = re.compile(_MACRO_NAME_SYNTAX)
_ENVIRONMENT_VARIABLE_PATTERN = re.compile(
    r"\$(?:([A-Za-z_][A-Za-z0-9_]*)|\{([A-Za-z_][A-Za-z0-9_]*)\})"
)
_WINDOWS_DRIVE_PATH_PATTERN = re.compile(r"^[A-Za-z]:[\\/]")


class FlattenError(Exception):
    def __init__(self, message: str, *, log_publish_safe: bool = True) -> None:
        super().__init__(message)
        self.log_publish_safe = log_publish_safe


class _DebugLogger(Protocol):
    def debug(self, message: str) -> None:
        ...


@dataclass(frozen=True)
class FlattenRequest:
    top_filelist: Path
    working_directory: Path
    output_filelist: Optional[Path] = None
    predefined_macros: FrozenSet[str] = field(default_factory=frozenset)
    log_file: Optional[Path] = None
    logger: Optional[_DebugLogger] = None


@dataclass(frozen=True)
class FlattenResult:
    output_filelist: Path


def _absolute_logical_path(path: Path, base_directory: Path) -> Path:
    if not path.is_absolute():
        path = base_directory / path
    return Path(os.path.abspath(path))


def _symlink_target_annotation(path: Path) -> Optional[str]:
    physical_path = path.resolve()
    if physical_path == path:
        return None
    return f"// symlink target: {physical_path}"


def _has_read_permission(path: Path) -> bool:
    return bool(stat.S_IMODE(path.stat().st_mode) & 0o444) and os.access(
        path,
        os.R_OK,
    )


def _source_chain_section(source_chain: tuple[str, ...]) -> str:
    if not source_chain:
        return ""
    rendered_entries = "\n".join(f"    {entry}" for entry in source_chain)
    return f"  source chain:\n{rendered_entries}\n"


def _split_trailing_comment(line: str) -> tuple[str, Optional[str]]:
    for index in range(len(line) - 1):
        if line[index : index + 2] not in {"//", "/*"}:
            continue
        if index == 0 or line[index - 1].isspace():
            return line[:index].rstrip(), line[index:]
    return line, None


def _logical_entries(
    content: str,
    filelist: Path,
    source_chain: tuple[str, ...],
) -> list[tuple[int, str, str, Optional[str]]]:
    physical_lines = content.splitlines()
    entries = []
    line_index = 0
    while line_index < len(physical_lines):
        line_number = line_index + 1
        first_line = physical_lines[line_index]
        entry, trailing_comment = _split_trailing_comment(first_line)
        original_lines = [first_line]
        block_comment_closing_line = first_line
        block_comment_closing_line_number = line_number
        if (
            trailing_comment is not None
            and trailing_comment.startswith("/*")
            and "*/" not in trailing_comment
        ):
            comment_lines = [trailing_comment]
            while "*/" not in comment_lines[-1]:
                line_index += 1
                if line_index == len(physical_lines):
                    raise FlattenError(
                        "unterminated block comment\n"
                        f"{_source_chain_section(source_chain)}"
                        f"  opened at: {filelist}:{line_number}\n"
                        "  suggestion: close the comment with */ in the "
                        "same filelist"
                    )
                next_line = physical_lines[line_index]
                original_lines.append(next_line)
                comment_lines.append(next_line)
            trailing_comment = "\n".join(comment_lines)
            block_comment_closing_line = comment_lines[-1]
            block_comment_closing_line_number = line_index + 1
        if trailing_comment is not None and trailing_comment.startswith("/*"):
            content_after_comment = block_comment_closing_line.split("*/", 1)[1]
            if content_after_comment.strip():
                raise FlattenError(
                    "content after block comment is not supported\n"
                    f"{_source_chain_section(source_chain)}"
                    f"  at: {filelist}:{block_comment_closing_line_number}\n"
                    f"  input: {block_comment_closing_line}\n"
                    "  suggestion: put the next logical entry on a separate line"
                )
        entries.append(
            (
                line_number,
                "\n".join(original_lines),
                entry,
                trailing_comment,
            )
        )
        line_index += 1
    return entries


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


def _expand_path_value(
    value: str,
    filelist: Path,
    line_number: int,
    source_chain: tuple[str, ...],
) -> str:
    if "*" in value or "?" in value or ("[" in value and "]" in value):
        raise FlattenError(
            "glob patterns are not supported in paths\n"
            f"{_source_chain_section(source_chain)}"
            f"  at: {filelist}:{line_number}\n"
            f"  input: {value}\n"
            "  suggestion: list each path explicitly"
        )
    braced_references = re.findall(r"\$\{[^}]*\}", value)
    has_unsupported_shell_syntax = (
        value.startswith("~")
        or "$(" in value
        or "`" in value
        or "${" in _ENVIRONMENT_VARIABLE_PATTERN.sub("", value)
        or any(
            _ENVIRONMENT_VARIABLE_PATTERN.fullmatch(reference) is None
            for reference in braced_references
        )
    )
    if has_unsupported_shell_syntax:
        raise FlattenError(
            "shell expansion syntax is not supported in paths\n"
            f"{_source_chain_section(source_chain)}"
            f"  at: {filelist}:{line_number}\n"
            f"  input: {value}\n"
            "  supported: $NAME and ${NAME}"
        )
    if "$" in _ENVIRONMENT_VARIABLE_PATTERN.sub("", value):
        raise FlattenError(
            "invalid environment variable syntax in path\n"
            f"{_source_chain_section(source_chain)}"
            f"  at: {filelist}:{line_number}\n"
            f"  input: {value}\n"
            "  supported: $NAME and ${NAME}"
        )
    expanded_value = _expand_environment_variables(
        value,
        filelist,
        line_number,
        source_chain,
    )
    if "$" in _ENVIRONMENT_VARIABLE_PATTERN.sub("", expanded_value):
        raise FlattenError(
            "invalid environment variable syntax in path\n"
            f"{_source_chain_section(source_chain)}"
            f"  at: {filelist}:{line_number}\n"
            f"  input: {value}\n"
            f"  expanded: {expanded_value}\n"
            "  supported: $NAME and ${NAME}"
        )
    if any(character.isspace() for character in expanded_value):
        expanded_section = (
            f"  expanded: {expanded_value}\n" if expanded_value != value else ""
        )
        raise FlattenError(
            "path contains whitespace\n"
            f"{_source_chain_section(source_chain)}"
            f"  at: {filelist}:{line_number}\n"
            f"  input: {value}\n"
            f"{expanded_section}"
            "  suggestion: use paths without spaces or tabs"
        )
    invalid_value = next(
        (
            candidate
            for candidate in (value, expanded_value)
            if _WINDOWS_DRIVE_PATH_PATTERN.match(candidate)
            or candidate.startswith("\\\\")
            or candidate.startswith("//")
        ),
        None,
    )
    if invalid_value is not None:
        expanded_section = (
            f"  expanded: {expanded_value}\n" if expanded_value != value else ""
        )
        raise FlattenError(
            "non-POSIX path syntax is not supported\n"
            f"{_source_chain_section(source_chain)}"
            f"  at: {filelist}:{line_number}\n"
            f"  input: {value}\n"
            f"{expanded_section}"
            "  suggestion: use a Linux/POSIX path such as /mnt/c/project"
        )
    return expanded_value


def _flatten_lines(
    filelist: Path,
    path_base: Path,
    request: FlattenRequest,
    filelist_stack: tuple[Path, ...],
    source_chain: tuple[str, ...],
    input_filelists: dict[Path, Path],
) -> list[str]:
    if request.logger is not None:
        request.logger.debug(f"reading filelist: {filelist}")
    try:
        content = filelist.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as error:
        raise FlattenError(
            "filelist is not valid UTF-8\n"
            f"{_source_chain_section(source_chain)}"
            f"  input: {filelist}\n"
            "  suggestion: convert the filelist to UTF-8"
        ) from error
    flattened_lines = []
    active_states = [True]
    branch_taken_states = [False]
    else_seen_states = [False]
    condition_open_lines = []
    for line_number, line, entry, trailing_comment in _logical_entries(
        content,
        filelist,
        source_chain,
    ):
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
                    f"{_source_chain_section(source_chain)}"
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
                    f"{_source_chain_section(source_chain)}"
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
                    f"{_source_chain_section(source_chain)}"
                    f"  at: {filelist}:{line_number}"
                )
            if else_seen_states[-1]:
                raise FlattenError(
                    "unexpected `elsif after `else\n"
                    f"{_source_chain_section(source_chain)}"
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
                    f"{_source_chain_section(source_chain)}"
                    f"  at: {filelist}:{line_number}"
                )
            if else_seen_states[-1]:
                raise FlattenError(
                    "unexpected `else after `else\n"
                    f"{_source_chain_section(source_chain)}"
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
                    f"{_source_chain_section(source_chain)}"
                    f"  at: {filelist}:{line_number}"
                )
            active_states.pop()
            branch_taken_states.pop()
            else_seen_states.pop()
            condition_open_lines.pop()
            continue
        if not active_states[-1]:
            continue
        if stripped.endswith("\\"):
            raise FlattenError(
                "backslash line continuation is not supported\n"
                f"{_source_chain_section(source_chain)}"
                f"  at: {filelist}:{line_number}\n"
                f"  input: {stripped}\n"
                "  suggestion: put one complete logical entry on each line"
            )
        if not stripped or stripped.startswith("//"):
            flattened_lines.append(line)
            continue
        if stripped.startswith("/*"):
            flattened_lines.append(line)
            continue
        if stripped.startswith("`"):
            raise FlattenError(
                "unsupported backtick directive\n"
                f"{_source_chain_section(source_chain)}"
                f"  at: {filelist}:{line_number}\n"
                f"  input: {stripped}\n"
                "  supported: `ifdef, `ifndef, `elsif, `else, `endif"
            )
        path_option_usage = {
            "-f": "-f PATH",
            "-F": "-F PATH",
            "-v": "-v PATH",
            "-y": "-y PATH",
        }
        for option, expected_usage in path_option_usage.items():
            separated_form = bool(tokens) and tokens[0] == option
            compact_form = (
                stripped.startswith(option)
                and stripped != option
                and not stripped.startswith(f"{option} ")
            )
            if (separated_form and len(tokens) != 2) or compact_form:
                raise FlattenError(
                    "invalid path option syntax\n"
                    f"{_source_chain_section(source_chain)}"
                    f"  at: {filelist}:{line_number}\n"
                    f"  input: {stripped}\n"
                    f"  expected: {expected_usage}"
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
            expanded_child_reference = _expand_path_value(
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
                    f"{_source_chain_section(source_chain)}"
                    f"  at: {filelist}:{line_number}\n"
                    f"  input: {line}\n"
                    f"  resolved: {child_filelist}"
                )
            if not _has_read_permission(child_filelist):
                raise FlattenError(
                    "filelist is not readable\n"
                    f"{_source_chain_section(source_chain)}"
                    f"  at: {filelist}:{line_number}\n"
                    f"  input: {line}\n"
                    f"  resolved: {child_filelist}\n"
                    "  suggestion: grant read permission to the filelist"
                )
            child_identity = child_filelist.resolve()
            input_filelists.setdefault(child_identity, child_filelist)
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
            if request.logger is not None:
                request.logger.debug(
                    f"expanding filelist: {filelist}:{line_number} -> "
                    f"{child_filelist}"
                )
            if trailing_comment is not None:
                flattened_lines.append(trailing_comment)
            annotation = _symlink_target_annotation(child_filelist)
            if annotation is not None:
                flattened_lines.append(annotation)
            flattened_lines.extend(
                _flatten_lines(
                    child_filelist,
                    child_content_base or child_filelist.parent,
                        request,
                        filelist_stack + (child_identity,),
                        next_source_chain,
                        input_filelists,
                    )
            )
            continue
        if len(tokens) == 2 and tokens[0] == "-v":
            expanded_library = _expand_path_value(
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
            if not _has_read_permission(library_file):
                raise FlattenError(
                    "library file is not readable\n"
                    f"{_source_chain_section(source_chain)}"
                    f"  at: {filelist}:{line_number}\n"
                    f"  input: {line}\n"
                    f"  resolved: {library_file}\n"
                    "  suggestion: grant read permission to the library file"
                )
            rendered_library = f"-v {library_file}"
            if trailing_comment is not None:
                rendered_library = f"{rendered_library} {trailing_comment}"
            annotation = _symlink_target_annotation(library_file)
            if annotation is not None:
                flattened_lines.append(annotation)
            flattened_lines.append(rendered_library)
            continue
        if len(tokens) == 2 and tokens[0] == "-y":
            expanded_library_directory = _expand_path_value(
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
            annotation = _symlink_target_annotation(library_directory)
            if annotation is not None:
                flattened_lines.append(annotation)
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
                expanded_include_directory = _expand_path_value(
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
                annotation = _symlink_target_annotation(include_directory)
                if annotation is not None:
                    include_directories.append(annotation)
                include_directories.append(f"+incdir+{include_directory}")
            if trailing_comment is not None:
                flattened_lines.append(trailing_comment)
            flattened_lines.extend(include_directories)
            continue
        if stripped.startswith(("-", "+")):
            flattened_lines.append(line)
            continue
        if len(tokens) != 1:
            raise FlattenError(
                "source path contains whitespace\n"
                f"{_source_chain_section(source_chain)}"
                f"  at: {filelist}:{line_number}\n"
                f"  input: {stripped}\n"
                "  suggestion: use a path without spaces or tabs"
            )
        if (
            "*" in stripped
            or "?" in stripped
            or ("[" in stripped and "]" in stripped)
        ):
            raise FlattenError(
                "glob patterns are not supported in paths\n"
                f"{_source_chain_section(source_chain)}"
                f"  at: {filelist}:{line_number}\n"
                f"  input: {stripped}\n"
                "  suggestion: list each path explicitly"
            )
        expanded_source = _expand_path_value(
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
        if not _has_read_permission(resolved_source):
            raise FlattenError(
                "source file is not readable\n"
                f"{_source_chain_section(source_chain)}"
                f"  at: {filelist}:{line_number}\n"
                f"  input: {line}\n"
                f"  resolved: {resolved_source}\n"
                "  suggestion: grant read permission to the source file"
            )
        if request.logger is not None:
            request.logger.debug(
                f"resolved source: {filelist}:{line_number} -> {resolved_source}"
            )
        annotation = _symlink_target_annotation(resolved_source)
        if annotation is not None:
            flattened_lines.append(annotation)
        rendered_source = str(resolved_source)
        if trailing_comment is not None:
            rendered_source = f"{rendered_source} {trailing_comment}"
        flattened_lines.append(rendered_source)
    if condition_open_lines:
        raise FlattenError(
            "unterminated conditional block\n"
            f"{_source_chain_section(source_chain)}"
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
    top_filelist = _absolute_logical_path(
        request.top_filelist,
        request.working_directory,
    )
    if not top_filelist.exists():
        raise FlattenError(
            "top filelist does not exist\n"
            f"  input: {top_filelist}\n"
            "  suggestion: provide an existing filelist path"
        )
    if not top_filelist.is_file():
        raise FlattenError(
            "top filelist is not a regular file\n"
            f"  input: {top_filelist}\n"
            "  suggestion: provide a regular file"
        )
    if not _has_read_permission(top_filelist):
        raise FlattenError(
            "top filelist is not readable\n"
            f"  input: {top_filelist}\n"
            "  suggestion: grant read permission to the filelist"
        )
    output_filelist = _absolute_logical_path(
        request.output_filelist or Path("flattened.f"),
        request.working_directory,
    )
    if not output_filelist.parent.exists():
        raise FlattenError(
            "output parent directory does not exist\n"
            f"  output: {output_filelist}\n"
            f"  parent: {output_filelist.parent}\n"
            "  suggestion: create the parent directory or choose another output"
        )
    if not output_filelist.parent.is_dir():
        raise FlattenError(
            "output parent is not a directory\n"
            f"  output: {output_filelist}\n"
            f"  parent: {output_filelist.parent}\n"
            "  suggestion: choose an output path inside a directory"
        )
    output_parent_mode = stat.S_IMODE(output_filelist.parent.stat().st_mode)
    if (
        not output_parent_mode & 0o222
        or not output_parent_mode & 0o111
        or not os.access(output_filelist.parent, os.W_OK | os.X_OK)
    ):
        raise FlattenError(
            "output parent directory is not writable\n"
            f"  output: {output_filelist}\n"
            f"  parent: {output_filelist.parent}\n"
            "  suggestion: grant write and search permission to the directory"
        )
    if (
        output_filelist.exists()
        and not output_filelist.is_symlink()
        and not output_filelist.is_file()
    ):
        raise FlattenError(
            "output path is not a regular file\n"
            f"  output: {output_filelist}\n"
            "  suggestion: choose a file path for the flattened filelist"
        )
    top_filelist_identity = top_filelist.resolve()
    input_filelists = {top_filelist_identity: top_filelist}
    flattened_lines = _flatten_lines(
        top_filelist,
        top_filelist.parent,
        request,
        (top_filelist_identity,),
        (),
        input_filelists,
    )
    if request.log_file is not None:
        log_file = _absolute_logical_path(
            request.log_file,
            request.working_directory,
        )
        conflicting_input = (
            input_filelists.get(log_file.resolve()) if log_file.exists() else None
        )
        if conflicting_input is not None:
            raise FlattenError(
                "log path conflicts with input filelist\n"
                f"  log: {log_file}\n"
                f"  input: {conflicting_input}\n"
                "  suggestion: choose a different log path",
                log_publish_safe=False,
            )
    top_annotation = _symlink_target_annotation(top_filelist)
    if top_annotation is not None:
        flattened_lines.insert(0, top_annotation)
    flattened_content = "\n".join(flattened_lines)
    if flattened_lines:
        flattened_content += "\n"
    if output_filelist.exists():
        conflicting_input = input_filelists.get(output_filelist.resolve())
        if conflicting_input is not None:
            raise FlattenError(
                "output conflicts with an input filelist\n"
                f"  output: {output_filelist}\n"
                f"  input: {conflicting_input}\n"
                "  suggestion: choose a different output path"
            )
    preserved_output_mode = None
    if (
        output_filelist.exists()
        and not output_filelist.is_symlink()
        and output_filelist.is_file()
    ):
        preserved_output_mode = (
            stat.S_IMODE(output_filelist.stat().st_mode) & 0o666
        )
    current_umask = os.umask(0)
    os.umask(current_umask)
    output_mode = (
        preserved_output_mode
        if preserved_output_mode is not None
        else 0o666 & ~current_umask
    )
    temporary_fd, temporary_name = tempfile.mkstemp(
        prefix=f".{output_filelist.name}.",
        dir=output_filelist.parent,
    )
    os.close(temporary_fd)
    temporary_output = Path(temporary_name)
    try:
        temporary_output.write_text(flattened_content, encoding="utf-8")
        temporary_output.chmod(output_mode)
        os.replace(temporary_output, output_filelist)
    finally:
        if temporary_output.exists():
            temporary_output.unlink()
    return FlattenResult(output_filelist=output_filelist)


__all__ = [
    "FlattenError",
    "FlattenRequest",
    "FlattenResult",
    "flatten_filelist",
]
