# -*- coding: utf-8 -*-

"""
This module contains the command-line interface wrapper around the task runner.
"""

from argparse import ArgumentParser

from .exceptions import TaskLoaderError
from .logging import setup_logging
from .runner import find_task, run_task

__all__ = ["run"]

def run(task_dir=".", log_dir=None):
    """Main entry point into the Reports bot task runner.

    Runs whatever tasks are specified by the user after parsing command-line
    arguments.

    The given argument is used as the search path for task files.
    """
    parser = ArgumentParser(description="Run tasks through the Reports bot.")
    parser.add_argument("task_names", nargs="+", metavar="task_name",
                        help="name of module in `tasks/' to run")

    args = parser.parse_args()
    setup_logging(log_dir)

    try:
        tasks = [find_task(name, task_dir) for name in args.task_names]
    except TaskLoaderError:
        exit(1)

    for task in tasks:
        run_task(task)

if __name__ == "__main__":
    run()
