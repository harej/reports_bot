# -*- coding: utf-8 -*-

from datetime import datetime
import encodings
import json
from os.path import expanduser
import re

import oursql

from .user import User
from .util import to_wiki_format
from .wikidata import Wikidata
from .wikiproject import WikiProject

__all__ = ["Bot"]

class Bot:
    """Represents an instance of the Reports bot on a particular wiki.

    An instance of this class is accessible from all tasks as their '_bot'
    attribute, and is their primary way of interacting with the external world.
    It provides access to databases and structured representations of many
    objects like WikiProjects and users.
    """

    def __init__(self, config, project, lang):
        self._config = config
        self._project = project
        self._lang = lang

        self._site = None
        self._wikidb = None
        self._localdb = None
        self._wikidata = None
        self._project_config = None

    @staticmethod
    def _register_utf8mb4():
        """Install utf8mb4 as a valid alias for utf_8."""
        if "utf8mb4" not in encodings.aliases.aliases:
            encodings.aliases.aliases["utf8mb4"] = "utf_8"
        if hasattr(encodings, "_cache") and "utf8mb4" in encodings._cache:
            del encodings._cache["utf8mb4"]

    def _sql_connect(self, **kwargs):
        """Return a new SQL connection using the given arguments.

        We apply some transformations: a default file is configured if not
        username or password is provided, a default charset is set, and
        autocommit is turned off.

        The default charset really should be utf8mb4, but because of a bug in
        oursql's handling of charsets (conflating Python codecs with MySQL
        charsets, which are sometimes different), we cannot. Instead, if
        utf8mb4 is chosen, we'll install it as an alias first.
        """
        if ("read_default_file" not in kwargs and "user" not in kwargs
                and "password" not in kwargs):
            kwargs["read_default_file"] = expanduser("~/.my.cnf")
        if "charset" not in kwargs:
            kwargs["charset"] = "utf8mb4"
        if "autoping" not in kwargs:
            kwargs["autoping"] = True
        if "autoreconnect" not in kwargs:
            kwargs["autoreconnect"] = True

        if kwargs["charset"] == "utf8mb4":
            self._register_utf8mb4()

        return oursql.connect(**kwargs)

    def _load_project_config(self):
        """Load the project config JSON blob from the database.

        After calling this function, the config is available from and cached in
        self._project_config.
        """
        if self._project_config is not None:
            return

        query = "SELECT config_json FROM project_config WHERE config_site = ?"
        with self.localdb as cursor:
            cursor.execute(query, (self.wikiid,))
            results = cursor.fetchall()
            if not results:
                self._project_config = {"defaults": {}, "projects": {}}
                return
            raw = json.loads(results[0][0])

        config = {"defaults": raw["defaults"], "projects": {}}
        for project in raw["projects"]:
            config["projects"][project["name"]] = project
        self._project_config = config

    def _get_project_config(self, name):
        """Return the on-wiki JSON configuration for the given project.

        Default values are automatically resolved. If the project doesn't
        exist, None is returned.
        """
        self._load_project_config()

        name = to_wiki_format(self.site, name)
        if name not in self._project_config["projects"]:
            return None

        config = self._project_config["defaults"].copy()
        config.update(self._project_config["projects"][name])
        return config

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
        """Return a connection to the wiki replica SQL database."""
        if not self._wikidb:
            kwargs = self._config.get_wiki_sql(self.wikiid)
            self._wikidb = self._sql_connect(**kwargs)
        return self._wikidb

    @property
    def localdb(self):
        """Return a connection to the local Reports bot/WPX SQL database."""
        if not self._localdb:
            self._localdb = self._sql_connect(**self._config.get_local_sql())
        return self._localdb

    @property
    def wikidata(self):
        """Return an interface to Wikidata."""
        if not self._wikidata:
            sql_kwargs = self._config.get_wiki_sql("wikidatawiki")
            sql_conn = self._sql_connect(**sql_kwargs)
            self._wikidata = Wikidata(sql_conn)
        return self._wikidata

    def get_page(self, title):
        """Return a Pywikibot Page instance for the given page."""
        import pywikibot
        return pywikibot.Page(self.site, title)

    def get_project(self, name):
        """Return a WikiProject object corresponding to the given name.

        The name is the page title of the project's base page, including the
        namespace.
        """
        return WikiProject(self, name, self._get_project_config(name))

    def get_user(self, name):
        """Return a User object corresponding to the given username."""
        return User(self, name)

    def get_configured_projects(self):
        """Return a list of all WikiProjects that are configured."""
        self._load_project_config()
        projects = self._project_config["projects"]
        return [self.get_project(name) for name in projects]

    def get_last_updated(self, key):
        """Get the last update timestamp for the given key."""
        query = """SELECT lu_timestamp
            FROM last_update
            WHERE lu_site = ? AND lu_key = ?"""

        with self.localdb as cursor:
            cursor.execute(query, (self.wikiid, key))
            results = cursor.fetchall()

        if results:
            return results[0][0]
        return datetime.min

    def set_last_updated(self, key, timestamp=None):
        """Set the last update timestamp for the given key."""
        query = """INSERT INTO last_update (lu_site, lu_key, lu_timestamp)
            VALUES(?, ?, ?)
            ON DUPLICATE KEY UPDATE lu_timestamp = ?"""

        if not timestamp:
            timestamp = datetime.utcnow()

        with self.localdb as cursor:
            cursor.execute(query, (self.wikiid, key, timestamp, timestamp))
