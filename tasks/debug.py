# -*- coding: utf-8 -*-

import pdb

from reportsbot.task import Task

__all__ = ["Debug"]

class Debug(Task):
    """Example task for demonstration and debugging purposes."""

    def run(self):
        """Launch a debugging session."""
        pdb.set_trace()
