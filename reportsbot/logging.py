# -*- coding: utf-8 -*-

"""
This module contains utility code for Python's standard logging library.
"""

from logging import getLogger, Formatter, StreamHandler
from logging.handlers import TimedRotatingFileHandler
from os import makedirs, path
import stat

from .exceptions import ConfigError

__all__ = ["setup_logging", "get_logger"]

_ROOT_NAME = "reportsbot"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_root = getLogger(_ROOT_NAME)
_setup_done = False


class _ColorFormatter(Formatter):
    """A logging formatter that adds a bit of color to stream messages."""
    _LEVELS = {
        "DEBUG"   : "\x1b[34m[DEBUG]\x1b[0m",
        "INFO"    : "\x1b[32m[INFO] \x1b[0m",
        "WARNING" : "\x1b[33m[WARN] \x1b[0m",
        "ERROR"   : "\x1b[31m[ERROR]\x1b[0m",
        "CRITICAL": "\x1b[1m\x1b[31m[CRIT] \x1b[0m"
    }

    def __init__(self):
        format = "%(asctime)s %(levelcolor)s %(name)s: %(message)s"
        super().__init__(fmt=format, datefmt=_DATE_FORMAT)

    def format(self, record):
        default = "[{}]".format(record.levelname)
        record.levelcolor = self._LEVELS.get(record.levelname, default)
        return super().format(record)


def _setup_file_logging(log_dir):
    """Set up logging to the filesystem."""
    if not path.isdir(log_dir):
        if path.exists(log_dir):
            err = "log_dir ({}) exists but is not a directory"
            raise ConfigError(err.format(log_dir))
        makedirs(log_dir, stat.S_IWUSR|stat.S_IRUSR|stat.S_IXUSR)

    formatter = Formatter(
        fmt="[%(asctime)s %(levelname)-5s] %(name)s: %(message)s",
        datefmt=_DATE_FORMAT)

    logpath = path.join(log_dir, "bot.log")
    handler = TimedRotatingFileHandler(logpath, "midnight", 1, 7)
    handler.setLevel("INFO")
    handler.setFormatter(formatter)
    _root.addHandler(handler)

def setup_logging(log_dir=None):
    """Set up the logging infrastructure.

    If an argument is given, logs will be written to that directory.
    """
    global _setup_done

    if _setup_done:
        return
    _setup_done = True

    _root.handlers = []  # Remove any handlers already attached
    _root.setLevel("DEBUG")

    stream = StreamHandler()
    stream.setLevel("DEBUG")
    stream.setFormatter(_ColorFormatter())
    _root.addHandler(stream)

    if log_dir:
        _setup_file_logging(log_dir)

def get_logger(name):
    """Return a logger for the given service."""
    return _root.getChild(name)
