# -*- coding: utf-8 -*-

"""
This module contains assorted utility functions.
"""

import os
import pwd

from .exceptions import ConfigError

__all__ = ["to_sql_format", "to_wiki_format", "split_full_title",
           "join_full_title", "ensure_ownership"]

def to_sql_format(title):
    """Convert a page title or username to 'canonical' SQL format.

    SQL format uses underscores instead of spaces, and capitalizes the first
    letter.
    """
    title = title.strip().replace(" ", "_")
    if not title:
        return ""
    return title[0].upper() + title[1:]

def to_wiki_format(title):
    """Convert a page title or username to 'canonical' wiki format.

    Wiki format uses spaces instead of underscores, and capitalizes the first
    letter.
    """
    title = title.strip().replace("_", " ")
    if not title:
        return ""
    return title[0].upper() + title[1:]

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
        return to_wiki_format(title)
    ns_name = site.namespaces[ns].custom_name
    return ns_name + ":" + to_wiki_format(title)

def ensure_ownership(path):
    """Ensure that we are the owner of the given path.

    If not, try to set our user ID to match. If this fails (not root), OSError
    is raised. Nothing is done if the path doesn't exist.
    """
    try:
        owner = os.stat(path).st_uid
    except OSError:
        return

    if owner == os.geteuid():
        return

    user = pwd.getpwuid(owner)
    try:
        os.setregid(user.pw_gid, user.pw_gid)
        os.setreuid(owner, owner)
    except OSError as exc:
        err = "Can't become bot user ({}), are you root?\n{}"
        raise ConfigError(err.format(user.pw_name, exc)) from None
