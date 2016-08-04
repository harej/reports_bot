# -*- coding: utf-8 -*-

from collections import namedtuple

from .util import to_wiki_format

__all__ = ["WikiProject"]

_Page = namedtuple("_Page", ["id", "title", "ns"])

class WikiProject:
    """Represents a single WikiProject on a single site."""

    def __init__(self, bot, name, config=None):
        self._bot = bot
        self._name = to_wiki_format(bot.site, name)

        self._exists = config is not None
        self._config = config or {}

    @property
    def name(self):
        """Return the project's name. This includes the namespace."""
        return self._name

    @property
    def exists(self):
        """Return whether this project has a configuration entry."""
        return self._exists

    @property
    def config(self):
        """Return the on-wiki JSON configuration for this project.

        Default values are automatically resolved.
        """
        return self._config

    def get_members(self, namespaces=None, redirect=None):
        """Return a list of pages within this project.

        Each page is a 3-namedtuple (id, title, ns). Note the title is given in
        "SQL" format (with underscores instead of spaces).

        If *namespaces* is not None, it should either be an integer or an
        iterable of integers, and only pages within those namespaces will be
        returned.

        If *redirect* is not None, it should be a boolean, and only pages that
        are or aren't redirects will be returned.
        """
        query = """SELECT page_id, page_title, page_ns
            FROM {0}_index
            JOIN {0}_page ON index_page = page_id
            JOIN {0}_project ON index_project = project_id
            WHERE index_project = ?"""

        args = [self._name]

        if namespaces is not None:
            if isinstance(namespaces, int):
                query += " AND page_ns = ?"
                args.append(namespaces)
            else:
                chunk = ", ".join("?" * len(namespaces))
                query += " AND page_ns IN ({})".format(chunk)
                args.extend(namespaces)

        if redirect is not None:
            query += " AND page_is_redirect = ?"
            args.append(int(redirect))

        with self._bot.localdb as cursor:
            cursor.execute(query.format(self._bot.wikiid), tuple(args))
            return [_Page(*res) for res in cursor.fetchall()]
