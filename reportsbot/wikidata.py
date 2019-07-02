# -*- coding: utf-8 -*-

import requests

__all__ = ["Wikidata"]

class Wikidata:
    """Provides a structured interface for querying Wikidata."""

    def __init__(self, site, db):
        self._site = site
        self._db = db
        self._user_agent = None

    def _get_user_agent(self):
        """
        Return a user agent string suitable for accessing Wikidata.
        """
        if self._user_agent is None:
            from pywikibot.comms import http
            self._user_agent = http.user_agent(self._site)
        return self._user_agent

    @property
    def db(self):
        """Return a connection to Wikidata's SQL database."""
        return self._db

    @staticmethod
    def _parse_sparql_result_binding(bind):
        """Parse a result binding from a SPARQL query. Return an item ID.

        Raise ValueError if we can't parse it.
        """
        if bind["type"] != "uri":
            raise ValueError("Unknown binding type: %s" % bind["type"])

        val = bind["value"]
        if "/entity/" not in val:
            raise ValueError("Invalid value for URI binding: %s" % val)

        itemid = val.split("/entity/", 1)[1]
        if not itemid.startswith("Q"):
            return None

        try:
            return int(itemid[1:])
        except ValueError:
            raise ValueError("Invalid item ID for URI binding: %s" % val)

    def query(self, query):
        """Make a SPARQL query and return a list of item IDs.

        Syntax is described at:
        https://www.wikidata.org/wiki/Wikidata:SPARQL_query_service/queries

        Raise ValueError if some aspect of the query resulted in invalid data.
        Return an empty list if there were no results.
        """
        params = {"query": query, "format": "json"}
        url = "https://query.wikidata.org/bigdata/namespace/wdq/sparql?"
        req = requests.get(url, params=params, headers={"User-Agent": self._get_user_agent()})
        req.raise_for_status()

        try:
            data = req.json()
        except ValueError as exc:
            raise ValueError(
                "Couldn't decode JSON from URL: %s: %s" % (url, exc))

        try:
            var = data["head"]["vars"][0]
            bindings = data["results"]["bindings"]
            items = [self._parse_sparql_result_binding(bind[var])
                     for bind in bindings]
            return [item for item in items if item is not None]
        except (KeyError, IndexError):
            return []

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
