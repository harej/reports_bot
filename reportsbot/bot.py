# -*- coding: utf-8 -*-

from os.path import expanduser
import re

import oursql

from .user import User
from .wikiproject import WikiProject

__all__ = ["Bot"]

class Bot:
    """Represents an instance of the Reports bot on a particular wiki."""

    def __init__(self, config, project, lang):
        self._config = config
        self._project = project
        self._lang = lang

        self._site = None
        self._wikidb = None
        self._localdb = None

    def _sql_connect(self, **kwargs):
        """Return a new SQL connection using the given arguments.

        We apply some transformations: a default file is configured if not
        username or password is provided, a default charset is set, and
        autocommit is turned off.
        """
        if ("read_default_file" not in kwargs and "user" not in kwargs
                and "password" not in kwargs):
            kwargs["read_default_file"] = expanduser("~/.my.cnf")
        if "charset" not in kwargs:
            kwargs["charset"] = "utf8"
        if "autoping" not in kwargs:
            kwargs["autoping"] = True
        if "autoreconnect" not in kwargs:
            kwargs["autoreconnect"] = True

        return oursql.connect(**kwargs)

    @property
    def config(self):
        """Return the bot's Config object."""
        return self._config

    @property
    def wikiid(self):
        """Return the site's ID; e.g. "enwiki" from "en" and "wikipedia"."""
        # TODO: This is somewhat hacky; should really be using the API here...
        if self._project == "wikipedia":
            res = self._lang + "wiki"
        else:
            res = self._lang + self._project
        return re.sub(r"[^a-zA-Z0-9_-]", "", res).replace("-", "_")

    @property
    def site(self):
        """Return a Pywikibot Site instance."""
        import pywikibot
        if not self._site:
            self._site = pywikibot.Site(self._lang, self._project,
                                        self._config.username)
        return self._site

    @property
    def wikidb(self):
        """Return a connection to the wiki replica database."""
        if not self._wikidb:
            kwargs = self._config.get_wiki_sql(self.wikiid)
            self._wikidb = self._sql_connect(**kwargs)
        return self._wikidb

    @property
    def localdb(self):
        """Return a connection to the local Reports bot/WPX database."""
        if not self._localdb:
            self._localdb = self._sql_connect(**self._config.get_local_sql())
        return self._localdb

    def get_page(self, title):
        """Return a Pywikibot Page instance for the given page."""
        import pywikibot
        return pywikibot.Page(self.site, title)

    def get_project(self, name):
        """Return a WikiProject object corresponding to the given name.

        The name is the page title of the project's base page, including the
        namespace.
        """
        return WikiProject(self, name)

    def get_user(self, name):
        """Return a User object corresponding to the given username."""
        return User(self, name)
