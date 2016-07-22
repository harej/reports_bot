# -*- coding: utf-8 -*-

"""
Loads wikiproject.json, validates it, stores it
Copyright (C) 2015 James Hare, 2016 Ben Kurtovic
Licensed under MIT License: http://mitlicense.org
"""

from datetime import datetime
import json

from reportsbot.task import Task

__all__ = ["LoadProjectConfig"]

class LoadProjectConfig(Task):
    """Loads project config from on-wiki and stores it in our database."""
    CONFIG_TITLE = "Project:WikiProject X/wikiproject.json"
    ERROR_TITLE = "Project talk:WikiProject X/wikiproject.json/Errors"

    def _report_error(self, message):
        """Report an error to the error page."""
        self._logger.error(message)
        page = self._bot.get_page(self.ERROR_TITLE)
        wikitime = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        page.text = "{}: {}".format(wikitime, message)
        page.save("Error while loading configuration", minor=False)

    def _verify(self, data):
        """Verify that the given config data matches the schema.

        This applies some normalization to the data, like to project names.
        """
        sections = {
            "schema": dict,
            "defaults": dict,
            "projects": list
        }

        for key, type_ in sections.items():
            if key not in data:
                self._report_error("Missing section: {}".format(key))
                return False
            if not isinstance(data[key], type_):
                err = "Wrong data type for section {}, should be {}"
                self._report_error(err.format(key, type_))
                return False

        for setting in data["defaults"]:
            if setting not in data["schema"]:
                err = "Invalid setting {0} in default configuration"
                self._report_error(err.format(setting))
                return False

        for i, project in enumerate(data["projects"]):
            if not isinstance(project, dict):
                err = "Wrong data type for project at index {}"
                self._report_error(err.format(i))
                return False
            if "name" not in project:
                err = "Missing name for project at index {}"
                self._report_error(err.format(i))
                return False
            for setting in project:
                if setting not in data["schema"]:
                    err = "Invalid setting {} for project {}"
                    self._report_error(err.format(setting, project["name"]))
                    return False

        return True

    def _save_to_database(self, data):
        """Save the given config data to the database."""
        self._logger.info("Saving new config to database")

        query1 = "DELETE FROM project_config WHERE config_site = ?"
        query2 = """INSERT INTO project_config (config_site, config_json)
                    VALUES (?, ?)"""

        dump = json.dumps(data)
        with self._bot.localdb as cursor:
            cursor.execute("BEGIN")
            cursor.execute(query1, (self._bot.wikiid,))
            cursor.execute(query2, (self._bot.wikiid, dump))

    def run(self):
        page = self._bot.get_page(self.CONFIG_TITLE)

        try:
            data = json.loads(page.text)
        except ValueError as ack:  # If JSON is invalid
            self._report_error(str(ack))
            return

        if not self._verify(data):
            return

        self._save_to_database(data)
