"""
This module contains assorted utility functions.
"""

__all__ = [
    "to_sql_format",
    "to_wiki_format",
    "split_full_title",
    "join_full_title",
]


def to_sql_format(title):
    """Convert a page title or username to 'canonical' SQL format.

    SQL format uses underscores instead of spaces, and capitalizes the first
    letter.
    """
    title = title.replace(" ", "_")
    if not title:
        return ""
    return title[0].upper() + title[1:]


def to_wiki_format(site, title, ignore_ns=False):
    """Convert a page title or username to 'canonical' wiki format.

    Wiki format uses spaces instead of underscores, and capitalizes the first
    letter. It also uses custom (not canonical) namespace names. The first
    parameter should be a Pywikibot Site object, and is used to look up
    namespace names.
    """

    def _format(title):
        title = title.replace("_", " ")
        return (title[0].upper() + title[1:]) if title else ""

    if ":" in title and not ignore_ns:
        ns_name, base_name = title.split(":", 1)
        if ns_name in site.namespaces:
            ns_name = site.namespaces[ns_name].custom_name
            return ns_name + ":" + _format(base_name)
    return _format(title)


def split_full_title(site, title):
    """Split a full pagename into a 2-tuple of (namespace ID, SQL-ready title).

    The first parameter should be a Pywikibot Site object, and is used to look
    up namespace names.
    """
    if ":" in title:
        ns_name, base_name = title.split(":", 1)
        if ns_name in site.namespaces:
            return (site.namespaces[ns_name].id, to_sql_format(base_name))
    return (0, to_sql_format(title))


def join_full_title(site, ns, title):
    """Join a namespace ID and page title into a wiki-formatted full pagename.

    The first parameter should be a Pywikibot Site object, and is used to look
    up namespace IDs.
    """
    if ns == 0:
        return to_wiki_format(site, title, ignore_ns=True)
    ns_name = site.namespaces[ns].custom_name
    return ns_name + ":" + to_wiki_format(site, title, ignore_ns=True)
