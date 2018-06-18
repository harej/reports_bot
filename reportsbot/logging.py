# -*- coding: utf-8 -*-

"""
This module contains utility code for Python's standard logging library.
"""

from logging import getLogger, Formatter, StreamHandler, FileHandler
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import os
from stat import ST_DEV, ST_INO

from .exceptions import ConfigError

__all__ = ["setup_logging", "get_logger"]

_ROOT_NAME = "reportsbot"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_root = getLogger(_ROOT_NAME)
_log_dir = None
_setup_done = False
_file_logging_enabled = False


class _WatchedRotatingFileHandler(RotatingFileHandler):
    """Modifies a RotatingFileHandler to emulate a WatchedFileHandler.

    The goal here is to ensure that if another process rotates a log file while
    we are using it, we'll reopen the new log file instead of continuing to
    write to its old location (and possibly rotating things multiple times).

    I'd prefer to just subclass RotatingFileHandler and WatchedFileHandler
    together, but due to the way they structure their method calls, it's not
    possible. Instead, code from WatchedFileHandler is adapted here.
    """

    def __init__(self, filename, maxBytes=0, backupCount=0):
        super().__init__(filename, maxBytes=maxBytes, backupCount=backupCount)
        self.dev, self.ino = -1, -1
        self._statstream()

    def _statstream(self):
        if self.stream:
            sres = os.fstat(self.stream.fileno())
            self.dev, self.ino = sres[ST_DEV], sres[ST_INO]

    def emit(self, record):
        try:
            sres = os.stat(self.baseFilename)
        except FileNotFoundError:
            sres = None

        if not sres or sres[ST_DEV] != self.dev or sres[ST_INO] != self.ino:
            if self.stream is not None:
                self.stream.flush()
                self.stream.close()
                self.stream = None
                self.stream = self._open()
                self._statstream()

        super().emit(record)


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
        fmt = "%(asctime)s %(levelcolor)s %(name)s: %(message)s"
        super().__init__(fmt=fmt, datefmt=_DATE_FORMAT)

    def format(self, record):
        default = "[{}]".format(record.levelname)
        record.levelcolor = self._LEVELS.get(record.levelname, default)
        return super().format(record)


def _ensure_dirs(dirpath):
    """Ensure that the given path exists as a directory."""
    if not os.path.isdir(dirpath):
        if os.path.exists(dirpath):
            err = "log path ({}) exists but is not a directory"
            raise ConfigError(err.format(dirpath))
        os.makedirs(dirpath, 0o777)

def _setup_file_logging(log_dir):
    """Set up logging to the filesystem."""
    global _file_logging_enabled, _log_dir
    _file_logging_enabled = True

    _log_dir = log_dir
    _ensure_dirs(log_dir)

    formatter = Formatter(
        fmt="[%(asctime)s %(levelname)-7s] %(name)s: %(message)s",
        datefmt=_DATE_FORMAT)

    infohandler = _WatchedRotatingFileHandler(
        os.path.join(log_dir, "all.log"), maxBytes=32 * 1024**2, backupCount=4)
    infohandler.setLevel("INFO")

    errorhandler = _WatchedRotatingFileHandler(
        os.path.join(log_dir, "all.err"), maxBytes=32 * 1024**2, backupCount=4)
    errorhandler.setLevel("WARNING")

    for handler in [infohandler, errorhandler]:
        handler.setFormatter(formatter)
        _root.addHandler(handler)

def _disable_pywikibot_logging():
    """Tells Pywikibot to not log messages below WARNING level to stderr."""
    # We need to wake up Pywikibot's logging interface so that its logger level
    # won't get overridden by a later logging call:
    import pywikibot
    pywikibot.debug("Disabling routine logging", "logging")
    getLogger("pywiki").setLevel("WARNING")

def _setup_task_logger(logger):
    """Configure a task logger to generate site- and task-specific logs."""
    if logger.handlers:  # Already processed
        return

    parts = logger.name.split(".")
    if len(parts) < 4:  # Malformed
        return
    site = parts[2]
    task = parts[3]

    _ensure_dirs(os.path.join(_log_dir, site))

    formatter = Formatter(
        fmt="[%(asctime)s %(levelname)-7s] %(message)s",
        datefmt=_DATE_FORMAT)

    infohandler = TimedRotatingFileHandler(
        os.path.join(_log_dir, site, task + ".log"), "midnight", 1, 30)
    infohandler.setLevel("INFO")

    debughandler = FileHandler(
        os.path.join(_log_dir, site, task + ".log.verbose"), "w")
    debughandler.setLevel("DEBUG")

    errorhandler = RotatingFileHandler(
        os.path.join(_log_dir, site, task + ".err"), maxBytes=1024**2,
        backupCount=4)
    errorhandler.setLevel("WARNING")

    for handler in [infohandler, debughandler, errorhandler]:
        handler.setFormatter(formatter)
        logger.addHandler(handler)

def setup_logging(log_dir=None, quiet=False):
    """Set up the logging infrastructure.

    If *log_dir* is given, logs will be written to that directory. If *quiet*
    is True, logs below ERROR level will not be written to standard error.
    """
    global _setup_done

    if _setup_done:
        return
    _setup_done = True

    _root.handlers = []  # Remove any handlers already attached
    _root.setLevel("DEBUG")

    stream = StreamHandler()
    stream.setLevel("ERROR" if quiet else "DEBUG")
    stream.setFormatter(_ColorFormatter())
    _root.addHandler(stream)

    if log_dir:
        _setup_file_logging(log_dir)

    if quiet:
        _disable_pywikibot_logging()

def get_logger(name):
    """Return a logger for the given service.

    If the logger is a task logger (e.g. "task.enwiki.update_foo"), then we
    will ensure that the returned logger is configured to generate
    site-specific detailed logs.
    """
    logger = _root.getChild(name)
    if name.startswith("task.") and _file_logging_enabled:
        _setup_task_logger(logger)
    return logger
