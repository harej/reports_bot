# -*- coding: utf-8 -*-

"""
This module contains the command-line interface wrapper around the task runner.
"""

from argparse import ArgumentParser

# from .config import Config
from .exceptions import TaskLoaderError
from .logging import setup_logging
from .runner import find_task, run_task

__all__ = ["run"]

def run(task_dir=".", config_dir="config", log_dir=None):
    """Main entry point into the Reports bot task runner.

    Runs whatever tasks are specified by the user after parsing command-line
    arguments.

    *task_dir* is the search path for task files. *config_dir* is the (default)
    bot configuration directory. *log_dir* is the (default) log file directory.
    """
    parser = ArgumentParser(
        description="Run tasks through the Reports bot.", add_help=False,
        usage="%(prog)s [-p <project>] [-l <lang>] [-q] <task> [<task> ...]")

    g_task = parser.add_argument_group("task options")
    g_task.add_argument("task_names", nargs="+", metavar="<task>",
                        help="name of task to run")
    g_task.add_argument("-p", "--project", metavar="<project>",
                        default="wikipedia",
                        help="project to run the bot on (default: wikipedia)")
    g_task.add_argument("-l", "--lang", metavar="<lang>", default="en",
                        help="language to run the bot on (default: en)")

    g_logs = parser.add_argument_group("logging")
    g_logs.add_argument("-q", "--quiet", action="store_true",
                        help="don't print routine (non-error) logs to stdout")
    g_logs.add_argument("-t", "--traceless", action="store_true",
                        help="don't write any logs to the filesystem")
    g_logs.add_argument("--log-dir", metavar="<path>", default=log_dir,
                        help="use a custom log directory")

    g_misc = parser.add_argument_group("miscellaneous")
    g_misc.add_argument("-c", "--config", metavar="<path>",
                        help="use a custom config directory")
    g_misc.add_argument("-h", "--help", action="help",
                        help="show this help message and exit")

    args = parser.parse_args()
    setup_logging(log_dir=None if args.traceless else args.log_dir,
                  quiet=args.quiet)
    # config = Config(config_dir)

    try:
        tasks = [find_task(name, task_dir) for name in args.task_names]
    except TaskLoaderError:
        exit(1)

    for task in tasks:
        run_task(task)  # XXX

if __name__ == "__main__":
    run()
