# -*- coding: utf-8 -*-

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
                self._data = yaml.load(fp.read())
        except (OSError, yaml.error.YAMLError) as exc:
            err = "Couldn't read config file ({}):\n{}"
            raise ConfigError(err.format(filename, exc)) from None

    @property
    def default_project(self):
        """Return the default site project, like 'wikipedia'."""
        return self._data.get("defaults", {}).get("project", "wikipedia")

    @property
    def default_lang(self):
        """Return the default site language, like 'en'."""
        return self._data.get("defaults", {}).get("lang", "en")

    @property
    def local_sql(self):
        """Return SQL connection info for the Reports bot/WPX database."""
        return self._data.get("local_sql", {})
