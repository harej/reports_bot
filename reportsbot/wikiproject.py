# -*- coding: utf-8 -*-

from .util import to_wiki_format

__all__ = ["WikiProject"]

class WikiProject:
    """Represents a single WikiProject on a single site."""

    def __init__(self, bot, name, config=None):
        self._bot = bot
        self._name = to_wiki_format(name)

        self._exists = config is not None
        self._config = config or {}

    @property
    def name(self):
        """Return the project's name. This includes the namespace."""
        return self._name

    @property
    def exists(self):
        """Return whether this project has a configuration entry."""
        return self._exists

    @property
    def config(self):
        """Return the on-wiki JSON configuration for this project.

        Default values are automatically resolved.
        """
        return self._config
