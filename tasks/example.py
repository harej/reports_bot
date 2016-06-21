# -*- coding: utf-8 -*-

from reportsbot.task import Task

__all__ = ["Example"]

class Example(Task):
    """Example task for demonstration purposes."""

    def run(self):
        """This is the main entry point into the task.

        In this case, it simply launches a debugging session.
        """
        import pdb
        pdb.set_trace()
