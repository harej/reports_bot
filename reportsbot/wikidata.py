# -*- coding: utf-8 -*-

from urllib.parse import urlencode

import requests

__all__ = ["Wikidata"]

class Wikidata:
    """Provides a structured interface for querying Wikidata."""

    def __init__(self, db):
        self._db = db

    @property
    def db(self):
        """Return a connection to Wikidata's SQL database."""
        return self._db

    def query(self, query):
        """Make a WDQ query and return a list of items IDs.

        Syntax is described at: http://wdq.wmflabs.org/api_documentation.html
        """
        params = {"q": query}
        url = "https://wdq.wmflabs.org/api?" + urlencode(params)
        req = requests.get(url)
        return req.json()["items"]

    def get_linked_pages(self, wikiid, items):
        """Return pages linked to by the given items on the given wiki.

        *items* should be a list of item IDs, as integers. The returned pages
        are full page titles in "wiki" format, with spaces instead of
        underscores.
        """
        query = """SELECT ips_site_page
            FROM wb_items_per_site
            WHERE ips_site_id = ? AND ips_item_id IN ({})"""

        chunksize = 10000
        pages = []

        with self._db as cursor:
            for start in range(0, len(items), chunksize):
                chunk = items[start:start+chunksize]
                params = ", ".join("?" * len(chunk))
                args = [wikiid] + chunk

                cursor.execute(query.format(params), args)
                results = [title.decode("utf8")
                           for (title,) in cursor.fetchall()]
                pages.extend(results)

        return pages
