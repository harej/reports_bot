# -*- coding: utf-8 -*-

from .util import to_sql_format, to_wiki_format

__all__ = ["User"]

class User:
    """Represents a user on a particular site.

    Users can be part of multiple WikiProjects.
    """

    def __init__(self, bot, name):
        self._bot = bot
        self._name = to_wiki_format(name)

    @property
    def name(self):
        """Return the user's name."""
        return self._name

    def is_active(self):
        """Return whether or not the user meets a basic threshold of activity.

        Threshold is at least one edit in the past 30 days.
        """
        query = """SELECT COUNT(*)
            FROM recentchanges_userindex
            WHERE rc_user_text = %s AND
            TIMESTAMP(rc_timestamp) > DATE_SUB(NOW(), INTERVAL 30 DAY)"""

        with self._bot.wikidb as cursor:
            cursor.execute(query, (to_sql_format(self._name),))
            count = cursor.fetchall()[0][0]

        return count > 0
