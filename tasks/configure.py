# -*- coding: utf-8 -*-

from collections import OrderedDict
from getpass import getpass
from os import chmod, makedirs, path
import stat

import yaml

from reportsbot.exceptions import ConfigError
from reportsbot.task import Task

__all__ = ["Configure"]

class Configure(Task):
    """Assisted creation of Reports bot's configuration."""
    PROMPT = "\x1b[32m> \x1b[0m"

    def __init__(self, bot):
        super().__init__(bot)
        self._defaults = OrderedDict()
        self._username = None

    def _ask(self, text, default=None, require=True):
        """Ask a question of the user and return the response."""
        text = self.PROMPT + text
        if default:
            text += " \x1b[33m[{0}]\x1b[0m".format(default)

        while True:
            answer = input(text + " ") or default
            if answer or not require:
                return answer

    def _ask_bool(self, text, default=True):
        """Ask the user a yes or no question and return the response."""
        text = self.PROMPT + text
        if default:
            text += " \x1b[33m[Y/n]\x1b[0m"
        else:
            text += " \x1b[33m[y/N]\x1b[0m"

        while True:
            answer = input(text + " ").lower()
            if not answer:
                return default
            if answer.startswith("y"):
                return True
            if answer.startswith("n"):
                return False

    def _ask_pass(self, text):
        return getpass(self.PROMPT + text + " ")

    def _write_file_with_mode(self, filename, mode, callback):
        """Write data to the given file with the given mode."""
        with open(filename, "x") as fp:
            pass
        chmod(filename, mode)
        with open(filename, "w") as fp:
            callback(fp)

    def _dump_yaml(self, data, stream=None, **kwargs):
        """Dump some YAML data into the stream, while preserving dict order.

        Based on: http://stackoverflow.com/a/21912744/2712951
        """
        class OrderedDumper(yaml.Dumper):
            pass

        def _dict_representer(dumper, data):
            return dumper.represent_mapping(
                yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
                data.items())

        OrderedDumper.add_representer(OrderedDict, _dict_representer)
        return yaml.dump(data, stream, OrderedDumper, **kwargs)

    def _create_config_dir(self):
        """Create the config dir if missing."""
        config_dir = self._bot.config.dir
        if not path.isdir(config_dir):
            if path.exists(config_dir):
                err = "config_dir ({}) exists but is not a directory"
                raise ConfigError(err.format(config_dir))

            self._logger.info("Creating config directory: %s", config_dir)
            makedirs(config_dir, stat.S_IWUSR|stat.S_IRUSR|stat.S_IXUSR)

    def _get_username(self):
        """Return the bot's username; ask for it if necessary."""
        if not self._username:
            self._username = self._ask("Bot username:")
        return self._username

    def _get_defaults(self):
        """Return default site info; ask for it if necessary."""
        if not self._defaults:
            project = self._ask("Default site project:", "wikipedia").lower()
            lang = self._ask("Default site language code:", "en").lower()
            self._defaults["project"] = project
            self._defaults["lang"] = lang
        return self._defaults

    def _build_sql_config(self):
        """Build and return a dict of SQL config."""
        sql = OrderedDict()

        if self._ask_bool("Assume Wikimedia Labs standard database setup?"):
            defaultsfile = self._ask("Defaults file path:", "~/replica.my.cnf")
            localdb = self._ask("Local bot database name:")
            sql["all"] = {"read_default_file": defaultsfile}
            sql["wiki"] = OrderedDict((
                ("host", "{site}.labsdb"), ("db", "{site}_p")))
            sql["local"] = OrderedDict((
                ("host", "tools.labsdb"), ("db", localdb)))

        else:
            wikihost = self._ask("Wiki database host (use '{site}' as a placeholder for the site ID, e.g. '{site}.labsdb'):")
            wikidb = self._ask("Wiki database name (e.g. '{site}_p'):")
            localhost = self._ask("Local bot database host:")
            localdb = self._ask("Local bot database name:")
            sql["wiki"] = OrderedDict((("host", wikihost), ("db", wikidb)))
            sql["local"] = OrderedDict((("host", localhost), ("db", localdb)))

            if self._ask_bool("Use a defaults file for SQL authentication?"):
                defaultsfile = self._ask("Defaults file path:", "~/.my.cnf")
                sql["all"] = {"read_default_file": defaultsfile}
            else:
                sql["wiki"]["user"] = self._ask(
                    "Wiki database username:")
                sql["wiki"]["password"] = self._ask_pass(
                    "Wiki database password:")
                sql["local"]["user"] = self._ask(
                    "Local bot database username:")
                sql["local"]["password"] = self._ask_pass(
                    "Local bot database password:")

        return sql

    def _make_bot_config(self):
        """Create the config.yml file if it doesn't exist."""
        filename = path.join(self._bot.config.dir, "config.yml")
        if path.exists(filename):
            self._logger.warn("Skipping config.yml; exists.")
            return

        config = OrderedDict()
        config["username"] = self._get_username()
        config["defaults"] = self._get_defaults()
        config["sql"] = self._build_sql_config()

        self._write_file_with_mode(
            filename, stat.S_IWUSR|stat.S_IRUSR,
            lambda fp: self._dump_yaml(config, stream=fp))

    def _make_password_file(self, username, password):
        """Create a .password file for Pywikibot."""
        filename = path.join(self._bot.config.dir, ".password")
        data = "({}, {})".format(repr(username), repr(password))

        self._write_file_with_mode(
            filename, stat.S_IWUSR|stat.S_IRUSR,
            lambda fp: fp.write(data))
        return filename

    def _make_pywiki_config(self):
        """Create the user-config.py file if it doesn't exist."""
        filename = path.join(self._bot.config.dir, "user-config.py")
        if path.exists(filename):
            self._logger.warn("Skipping user-config.py; exists.")
            return

        config = []
        defaults = self._get_defaults()
        config.append("family = {}".format(repr(defaults["project"])))
        config.append("mylang = {}".format(repr(defaults["lang"])))

        if self._ask_bool("Use OAuth for authentication?"):
            consumer_key = self._ask("OAuth consumer token:")
            consumer_secret = self._ask("OAuth consumer secret:")
            access_key = self._ask("OAuth access token:")
            access_secret = self._ask("OAuth access secret:")
            config.append("authenticate['*'] = ({}, {}, {}, {})".format(
                repr(consumer_key), repr(consumer_secret), repr(access_key),
                repr(access_secret)))
        else:
            username = self._get_username()
            password = self._ask_pass("Bot password:")
            pwfile = self._make_password_file(username, password)
            config.append("password_file = {}".format(repr(pwfile)))

        config.append("log = []")
        config.append("noisysleep = 120")

        self._write_file_with_mode(
            filename, stat.S_IWUSR|stat.S_IRUSR,
            lambda fp: fp.write("\n".join(config) + "\n"))

    def run(self):
        self._create_config_dir()
        self._make_bot_config()
        self._make_pywiki_config()
