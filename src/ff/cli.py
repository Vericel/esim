import argparse
import logging
import os
import stat
import sys
import tempfile
from collections.abc import Sequence
from contextlib import suppress
from pathlib import Path
from typing import Protocol, cast

from onelog import get_logger

from ff import FlattenError, FlattenRequest, flatten_filelist


def _publish_log(temporary_log: Path, log_file: Path) -> None:
    logging.shutdown()
    os.replace(temporary_log, log_file)


def _paths_share_identity(first: Path, second: Path) -> bool:
    if first == second:
        return True
    return first.exists() and second.exists() and first.resolve() == second.resolve()


class _Logger(Protocol):
    def error(self, msg: object) -> None: ...

    def exception(self, msg: object) -> None: ...


def _report_internal_error(log: _Logger, error: Exception, debug: bool) -> None:
    message = f"ff internal error: {type(error).__name__}: {error}"
    if debug:
        log.exception(message)
    else:
        log.error(message)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ff")
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("-d", "--define", nargs="+", action="append", default=[])
    parser.add_argument("-l", "--log", nargs="?", const=Path("ff.log"), type=Path)
    parser.add_argument("--debug", action="store_true")
    arguments = list(argv) if argv is not None else sys.argv[1:]
    if (
        arguments
        and arguments[0].startswith("-")
        and arguments[0] not in {"-h", "--help"}
    ):
        parser.error("INPUT must be the first argument")
    args = parser.parse_args(arguments)
    input_filelist = cast(Path, args.input)
    output_filelist = cast(Path | None, args.output)
    define_groups = cast(list[list[str]], args.define)
    log_file = cast(Path | None, args.log)
    debug = cast(bool, args.debug)

    working_directory = Path.cwd()
    if output_filelist is not None and not output_filelist.is_absolute():
        output_filelist = working_directory / output_filelist

    temporary_log: Path | None = None
    if log_file is not None:
        if not log_file.is_absolute():
            log_file = working_directory / log_file
        if not log_file.parent.exists():
            print(
                "log parent directory does not exist\n"
                f"  log: {log_file}\n"
                f"  parent: {log_file.parent}\n"
                "  suggestion: create the parent directory or choose another log",
                file=sys.stderr,
            )
            return 1
        if not log_file.parent.is_dir():
            print(
                "log parent is not a directory\n"
                f"  log: {log_file}\n"
                f"  parent: {log_file.parent}\n"
                "  suggestion: choose a log path inside a directory",
                file=sys.stderr,
            )
            return 1
        log_parent_mode = stat.S_IMODE(log_file.parent.stat().st_mode)
        if (
            not log_parent_mode & 0o222
            or not log_parent_mode & 0o111
            or not os.access(log_file.parent, os.W_OK | os.X_OK)
        ):
            print(
                "log parent directory is not writable\n"
                f"  log: {log_file}\n"
                f"  parent: {log_file.parent}\n"
                "  suggestion: grant write and search permission to the directory",
                file=sys.stderr,
            )
            return 1
        if log_file.exists() and not log_file.is_symlink() and not log_file.is_file():
            print(
                "log path is not a regular file\n"
                f"  log: {log_file}\n"
                "  suggestion: choose a file path for the log",
                file=sys.stderr,
            )
            return 1
        effective_output = output_filelist or working_directory / "flattened.f"
        if _paths_share_identity(log_file, effective_output):
            print(
                "log path conflicts with flattened output\n"
                f"  log: {log_file}\n"
                f"  output: {effective_output}\n"
                "  suggestion: choose different log and output paths",
                file=sys.stderr,
            )
            return 1
        top_filelist = input_filelist
        if not top_filelist.is_absolute():
            top_filelist = working_directory / top_filelist
        if _paths_share_identity(log_file, top_filelist):
            print(
                "log path conflicts with input filelist\n"
                f"  log: {log_file}\n"
                f"  input: {top_filelist}\n"
                "  suggestion: choose a different log path",
                file=sys.stderr,
            )
            return 1
        temporary_fd, temporary_name = tempfile.mkstemp(
            prefix=f".{log_file.name}.",
            dir=log_file.parent,
        )
        os.close(temporary_fd)
        temporary_log = Path(temporary_name)
    log = get_logger(
        __name__,
        level=logging.DEBUG if debug else logging.WARNING,
        show_summary=False,
        gen_log=temporary_log is not None,
        log_file=str(temporary_log) if temporary_log is not None else None,
    )

    try:
        log.debug(f"flattening input: {input_filelist}")
        result = flatten_filelist(
            FlattenRequest(
                top_filelist=input_filelist,
                working_directory=working_directory,
                output_filelist=output_filelist,
                predefined_macros=frozenset(
                    macro for macro_group in define_groups for macro in macro_group
                ),
                log_file=log_file,
                logger=log,
            )
        )
    except FlattenError as error:
        with suppress(SystemExit):
            log.fatal(str(error))
        if temporary_log is not None:
            assert log_file is not None
            if error.log_publish_safe:
                _publish_log(temporary_log, log_file)
            else:
                logging.shutdown()
                temporary_log.unlink()
        return 1
    except Exception as error:
        _report_internal_error(log, error, debug)
        if temporary_log is not None:
            assert log_file is not None
            _publish_log(temporary_log, log_file)
        return 3
    log.info(f"flattened output: {result.output_filelist}")
    if temporary_log is not None:
        assert log_file is not None
        try:
            _publish_log(temporary_log, log_file)
        except Exception as error:
            _report_internal_error(log, error, debug)
            if temporary_log.exists():
                temporary_log.unlink()
            return 3
    return 0
