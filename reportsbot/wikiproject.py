# -*- coding: utf-8 -*-

import json

from .exceptions import NoProjectError
from .util import to_wiki_format

__all__ = ["WikiProject"]

class WikiProject:
    """Represents a single WikiProject on a single site."""

    def __init__(self, bot, name):
        self._bot = bot
        self._name = to_wiki_format(name)

    @property
    def name(self):
        """Return the project's name. This includes the namespace."""
        return self._name

    def get_config(self):
        """Return the on-wiki JSON configuration for this project.

        Default values are automatically resolved.

        Raises NoProjectError if the project is not found in the config.
        """
        query = "SELECT config_json FROM project_config WHERE config_site = ?"

        with self._bot.localdb as cursor:
            cursor.execute(query, (self._bot.wikiid,))
            if cursor.rowcount == 0:
                raise NoProjectError(self._name)
            raw = cursor.fetchall()[0][0]

        data = json.loads(raw)
        for project in data["projects"]:
            if project["name"] == self._name:
                config = data["defaults"]
                config.update(project)
                return config

        raise NoProjectError(self._name)
