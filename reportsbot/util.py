# -*- coding: utf-8 -*-

"""
This module contains assorted utility functions.
"""

__all__ = ["to_sql_format", "to_wiki_format"]

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
