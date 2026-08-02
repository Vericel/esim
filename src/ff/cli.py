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


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="ff")
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("-d", "--define", nargs="+", action="append", default=[])
    parser.add_argument("-l", "--log", nargs="?", const=Path("ff.log"), type=Path)
    args = parser.parse_args(argv)

    working_directory = Path.cwd()
    output_filelist = args.output
    if output_filelist is not None and not output_filelist.is_absolute():
        output_filelist = working_directory / output_filelist

    log_file = args.log
    temporary_log = None
    if log_file is not None:
        if not log_file.is_absolute():
            log_file = working_directory / log_file
        temporary_fd, temporary_name = tempfile.mkstemp(
            prefix=f".{log_file.name}.",
            dir=log_file.parent,
        )
        os.close(temporary_fd)
        temporary_log = Path(temporary_name)
        get_logger(
            __name__,
            level=logging.WARNING,
            show_summary=False,
            gen_log=True,
            log_file=str(temporary_log),
        )

    try:
        flatten_filelist(
            FlattenRequest(
                top_filelist=args.input,
                working_directory=working_directory,
                output_filelist=output_filelist,
                predefined_macros=frozenset(
                    macro
                    for macro_group in args.define
                    for macro in macro_group
                ),
            )
        )
    except FlattenError as error:
        print(error, file=sys.stderr)
        if temporary_log is not None:
            logging.getLogger(__name__).error(str(error))
            _publish_log(temporary_log, log_file)
        return 1
    if temporary_log is not None:
        _publish_log(temporary_log, log_file)
    return 0
