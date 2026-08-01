import argparse
from pathlib import Path
from typing import Optional, Sequence

from ff import FlattenRequest, flatten_filelist


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="ff")
    parser.add_argument("input", type=Path)
    args = parser.parse_args(argv)

    flatten_filelist(
        FlattenRequest(
            top_filelist=args.input,
            working_directory=Path.cwd(),
        )
    )
    return 0
