# -*- coding: utf-8 -*-

from .logging import get_logger

class Task:
    """Represents a single task to be done by the bot."""

    def __init__(self, bot):
        self._bot = bot
        self._logger = get_logger("task").getChild(type(self).__module__)

    def run(self):
        """Run the task. This must be overridden in subclasses."""
        raise NotImplementedError()
