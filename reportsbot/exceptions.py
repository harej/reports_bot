# -*- coding: utf-8 -*-

"""
This module contains the Reports bot exception hierarchy.

Exception
+-- ReportsBotError
    +-- ConfigError
    +-- TaskLoaderError
"""

class ReportsBotError(Exception):
    """Base class for all Reports bot-based exceptions."""
    pass

class ConfigError(ReportsBotError):
    """Represents an error while reading or processing bot configuration."""
    pass

class TaskLoaderError(ReportsBotError):
    """Represents an error while loading or setting up a bot task."""
    pass
