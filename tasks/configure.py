# -*- coding: utf-8 -*-

from os import makedirs, path

import yaml

from reportsbot.exceptions import ConfigError
from reportsbot.task import Task

__all__ = ["Configure"]

class Configure(Task):
    """Assisted creation of Reports bot's configuration."""

    def __init__(self, bot):
        super().__init__(bot)

    def _create_config_dir(self):
        """Create the config dir if missing."""
        config_dir = self._bot.config.dir
        if not path.isdir(config_dir):
            if path.exists(config_dir):
                err = "config_dir ({}) exists but is not a directory"
                raise ConfigError(err.format(config_dir))

            self._logger.info("Creating config directory: %s", config_dir)
            makedirs(config_dir, stat.S_IWUSR|stat.S_IRUSR|stat.S_IXUSR)

    def _build_bot_config(self):
        """Create the config.yml file if it doesn't exist."""
        filename = path.join(self._bot.config.dir, "config.yml")
        if path.exists(filename):
            self._logger.warn("Skipping config.yml; exists.")
            return

        # TODO

    def _build_pywiki_config(self):
        """Create the user-config.py file if it doesn't exist."""
        filename = path.join(self._bot.config.dir, "user-config.py")
        if path.exists(filename):
            self._logger.warn("Skipping user-config.py; exists.")
            return

        # TODO

    def run(self):
        self._create_config_dir()
        self._build_bot_config()
        self._build_pywiki_config()
