import argparse
import logging
import os
from pathlib import Path
import sys
import tempfile
from typing import Optional, Sequence

from ff import FlattenError, FlattenRequest, flatten_filelist
from ff._vendor.onelog import get_logger


def _publish_log(temporary_log: Path, log_file: Path) -> None:
    logging.shutdown()
    os.replace(temporary_log, log_file)


def _paths_share_identity(first: Path, second: Path) -> bool:
    if first == second:
        return True
    return first.exists() and second.exists() and first.resolve() == second.resolve()


def main(argv: Optional[Sequence[str]] = None) -> int:
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

    working_directory = Path.cwd()
    output_filelist = args.output
    if output_filelist is not None and not output_filelist.is_absolute():
        output_filelist = working_directory / output_filelist

    log_file = args.log
    temporary_log = None
    if log_file is not None:
        if not log_file.is_absolute():
            log_file = working_directory / log_file
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
        top_filelist = args.input
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
    log = None
    if args.debug or temporary_log is not None:
        log = get_logger(
            __name__,
            level=logging.DEBUG if args.debug else logging.WARNING,
            show_summary=False,
            gen_log=temporary_log is not None,
            log_file=str(temporary_log) if temporary_log is not None else None,
        )

    try:
        if log is not None:
            log.debug(f"flattening input: {args.input}")
        result = flatten_filelist(
            FlattenRequest(
                top_filelist=args.input,
                working_directory=working_directory,
                output_filelist=output_filelist,
                predefined_macros=frozenset(
                    macro
                    for macro_group in args.define
                    for macro in macro_group
                ),
                log_file=log_file,
            )
        )
    except FlattenError as error:
        if log is None:
            print(error, file=sys.stderr)
        else:
            try:
                log.fatal(str(error))
            except SystemExit:
                pass
        if temporary_log is not None:
            if error.log_publish_safe:
                _publish_log(temporary_log, log_file)
            else:
                logging.shutdown()
                temporary_log.unlink()
        return 1
    if log is not None:
        log.info(f"flattened output: {result.output_filelist}")
    if temporary_log is not None:
        _publish_log(temporary_log, log_file)
    return 0
