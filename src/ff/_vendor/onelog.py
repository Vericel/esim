"""Vendored from https://github.com/BottiCelle/onelog at dd41f9a.

The upstream repository does not currently contain Python packaging metadata,
so ff ships this module together with its declared Rich dependency.
"""

import atexit
import logging
import sys

from rich.logging import RichHandler
from rich.traceback import install


install(show_locals=True)

_DEFAULT_CONFIG = {
    "level": logging.INFO,
    "show_loc": False,
    "show_time": True,
    "show_summary": True,
    "gen_log": True,
    "log_file": "app.log",
    "log_format": (
        "%(asctime)s | %(levelname)-8s | %(pathname)s:%(lineno)d | %(message)s"
    ),
    "date_format": "[%H:%M:%S]",
}

FATAL = logging.FATAL
_global_config = None
_configured = False
_log_counter = {
    "DEBUG": 0,
    "INFO": 0,
    "WARNING": 0,
    "ERROR": 0,
    "FATAL": 0,
}


class FatalError(Exception):
    """FATAL log exception retained for compatibility with upstream."""


class _CountingFilter(logging.Filter):
    def filter(self, record):
        level_name = record.levelname
        if level_name in _log_counter:
            _log_counter[level_name] += 1
        return True


def log_summary():
    from rich.console import Console
    from rich.rule import Rule

    console = Console()
    console.print()
    console.print(Rule("[bold]📊 Log Summary[/bold]", style="cyan"))
    console.print(f"  DEBUG:   {_log_counter['DEBUG']}")
    console.print(f"  INFO:    {_log_counter['INFO']}")
    console.print(f"  WARNING: {_log_counter['WARNING']}", style="yellow")
    console.print(f"  ERROR:   {_log_counter['ERROR']}", style="bold red")
    if _log_counter["FATAL"] > 0:
        console.print(f"  FATAL:   {_log_counter['FATAL']}", style="bold magenta")
    console.print()
    if _global_config and _global_config.get("log_file"):
        import os

        log_path = os.path.abspath(_global_config["log_file"])
        console.print(f"  Log File: {log_path}")
    console.print(Rule(style="cyan"))
    console.print()


def get_logger(
    name=None,
    level=None,
    show_loc=None,
    show_time=None,
    show_summary=None,
    gen_log=None,
    log_file=None,
):
    global _global_config, _configured

    if not _configured:
        _global_config = dict(_DEFAULT_CONFIG)
        if level is not None:
            _global_config["level"] = level
        if show_loc is not None:
            _global_config["show_loc"] = show_loc
        if show_time is not None:
            _global_config["show_time"] = show_time
        if show_summary is not None:
            _global_config["show_summary"] = show_summary
        if gen_log is not None:
            _global_config["gen_log"] = gen_log
        if log_file is not None:
            _global_config["log_file"] = log_file
        if _global_config["gen_log"] is False:
            _global_config["log_file"] = None
        _apply_config()
        _configured = True

    return logging.getLogger(name)


def _apply_config():
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(_global_config["level"])

    from rich.console import Console
    from rich.theme import Theme

    custom_theme = Theme(
        {
            "logging.level.warning": "yellow",
            "logging.level.error": "bold red",
            "logging.level.fatal": "bold magenta",
        }
    )
    console = Console(theme=custom_theme)
    rich_handler = RichHandler(
        console=console,
        rich_tracebacks=True,
        show_path=_global_config["show_loc"],
        show_level=True,
        show_time=_global_config["show_time"],
        log_time_format=_global_config["date_format"],
        markup=False,
    )
    rich_handler.setLevel(_global_config["level"])
    rich_handler.addFilter(_CountingFilter())
    handlers = [rich_handler]

    if _global_config["log_file"]:
        file_handler = logging.FileHandler(
            _global_config["log_file"], encoding="utf-8"
        )
        file_handler.setFormatter(
            logging.Formatter(
                _global_config["log_format"],
                datefmt=_global_config["date_format"],
            )
        )
        file_handler.setLevel(_global_config["level"])
        handlers.append(file_handler)

    logging.basicConfig(
        level=_global_config["level"],
        format="%(message)s",
        handlers=handlers,
        force=True,
    )
    _patch_logger_fatal()
    if _global_config["show_summary"]:
        atexit.register(log_summary)


def _patch_logger_fatal():
    def fatal(self, msg, *args, **kwargs):
        kwargs.setdefault("stacklevel", 2)
        self.log(FATAL, msg, *args, **kwargs)
        sys.exit(1)

    logging.Logger.fatal = fatal
    logging.addLevelName(FATAL, "FATAL")
