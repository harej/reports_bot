# -*- coding: utf-8 -*-

"""
This module contains assorted utility functions.
"""

import os
import pwd

from .exceptions import ConfigError

__all__ = ["to_sql_format", "to_wiki_format", "ensure_ownership"]

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

    try:
        # TODO: should really set group ID here with os.setregid()
        os.setreuid(owner, owner)
    except OSError as exc:
        err = "Can't become bot user ({}), are you root?\n{}"
        owner_name = pwd.getpwuid(owner).pw_name
        raise ConfigError(err.format(owner_name, exc)) from None
