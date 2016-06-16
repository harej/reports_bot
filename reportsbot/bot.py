# -*- coding: utf-8 -*-

from os.path import expanduser

import pymysql
import pywikibot

from .user import User

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
        self._sql_args = {}

    def _get_wikiid(self):
        """Return the site's ID; e.g. "enwiki" from "en" and "wikipedia"."""
        if self._project == "wikipedia":
            return self._lang + "wiki"
        return self._lang + self._project

    def _sql_connect(self, **kwargs):
        """Return a new SQL connection using the given arguments."""
        args = self._sql_args.copy()
        args.update(kwargs)

        if ("read_default_file" not in args and "user" not in args
                and "password" not in args):
            args["read_default_file"] = expanduser("~/.my.cnf")

        if "charset" not in args:
            args["charset"] = "utf8mb4"
        if "autocommit" not in args:
            args["autocommit"] = False

        return pymysql.connect(**args)

    @property
    def site(self):
        """Return a Pywikibot site instance."""
        if not self._site:
            self._site = pywikibot.Site(self._lang, self._project)
        return self._site

    @property
    def wikidb(self):
        """Return a connection to the wiki's database."""
        if not self._wikidb:
            wikiid = self._get_wikiid()
            self._wikidb = self._sql_connect(
                host="{}.labsdb".format(wikiid),
                database="{}_p".format(wikiid))
        return self._wikidb

    @property
    def localdb(self):
        """Return a connection to the local Reports bot/WPX database."""
        if not self._localdb:
            self._localdb = self._sql_connect(**self._config.local_sql)
        return self._localdb

    def get_user(self, name):
        """Return a User object corresponding to the given username."""
        return User(self, name)
