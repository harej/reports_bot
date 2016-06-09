# -*- coding: utf-8 -*-

from reportsbot.task import Task

__all__ = ["ExampleTask"]

class ExampleTask(Task):
    """Example task that does nothing."""

    def run(self):
        """Just write a simple log message."""
        self._logger.info("Hello, world!")
