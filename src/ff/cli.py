import argparse
from pathlib import Path
import sys
from typing import Optional, Sequence

from ff import FlattenError, FlattenRequest, flatten_filelist


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="ff")
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("-d", "--define", nargs="+", action="append", default=[])
    args = parser.parse_args(argv)

    working_directory = Path.cwd()
    output_filelist = args.output
    if output_filelist is not None and not output_filelist.is_absolute():
        output_filelist = working_directory / output_filelist

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
        return 1
    return 0
