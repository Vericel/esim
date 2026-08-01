import argparse
from pathlib import Path
from typing import Optional, Sequence

from ff import FlattenRequest, flatten_filelist


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="ff")
    parser.add_argument("input", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args(argv)

    working_directory = Path.cwd()
    output_filelist = args.output
    if output_filelist is not None and not output_filelist.is_absolute():
        output_filelist = working_directory / output_filelist

    flatten_filelist(
        FlattenRequest(
            top_filelist=args.input,
            working_directory=working_directory,
            output_filelist=output_filelist,
        )
    )
    return 0
