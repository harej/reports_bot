# -*- coding: utf-8 -*-

class Task:
    """Represents a single task to be done by the bot."""

    def __init__(self, bot):
        self.bot = bot

    def run(self):
        """Run the task. This must be overridden in subclasses."""
        raise NotImplementedError()
