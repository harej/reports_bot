# -*- coding: utf-8 -*-

import errno
from os import path

import yaml

from .exceptions import ConfigError

__all__ = ["Config"]

class Config:
    """Stores general-purpose bot configuration."""

    def __init__(self, base_dir):
        self._base_dir = base_dir
        self._data = {}
        self._load()

    def _load(self):
        """Load or reload the bot's main configuration file (config.yml)."""
        filename = path.join(self._base_dir, "config.yml")
        try:
            with open(filename) as fp:
                self._data = yaml.load(fp)
        except (OSError, yaml.error.YAMLError) as exc:
            if exc.errno == errno.ENOENT:  # Ignore missing file; use defaults
                return
            err = "Couldn't read config file ({}):\n{}"
            raise ConfigError(err.format(filename, exc)) from None

    def _get_sql_info(self, which):
        """Get some SQL connection info."""
        sql = self._data.get("sql", {})
        info = sql.get("all", {}).copy()
        info.update(sql.get(which, {}))
        return info

    @property
    def dir(self):
        """Return the bot's config directory."""
        return self._base_dir

    @property
    def username(self):
        """Return the bot's username."""
        return self._data.get("username")

    @property
    def default_project(self):
        """Return the default site project, like 'wikipedia'."""
        return self._data.get("defaults", {}).get("project", "wikipedia")

    @property
    def default_lang(self):
        """Return the default site language, like 'en'."""
        return self._data.get("defaults", {}).get("lang", "en")

    def get_wiki_sql(self, site):
        """Return SQL connection info for the wiki DB for the given site."""
        info = self._get_sql_info("wiki")
        for key, val in info.items():  # Convert db="{site}_p" to "enwiki_p"
            if isinstance(val, str):
                info[key] = val.format(site=site)
        return info

    def get_local_sql(self):
        """Return SQL connection info for the local Reports bot/WPX DB."""
        return self._get_sql_info("local")
