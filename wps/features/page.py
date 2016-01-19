"""
This module contains page importance features
"""
from revscoring.features import Features

from ..datasources import page


def process_views(page_stats):
    return page_stats.views

views = Feature("page.views", process_views, return=int,
                depends_on=[page.stats])


def process_alter_views(page_stats):
    return page_stats.alter_views

alter_views = Features("page.alter_views", ..., depends_on = [page.stats])


def process_inlinks(page_stats):
    return page_stats.inlinks

inlinks = Feature("page.inlinks", ..., depends_on = [page.stats])


def process_alter_inlinks(page_stats):
    return page_stats.alter_inlinks

alter_inlinks = Feature("page.alter_inlinks", ..., depends_on = [page.stats])


def process_inlinks_from_related(page_stats):
    return page_stats.inlinks_from_related

inlinks_from_related = Feature("page.inlinks_from_related", ..., depends_on = [page.stats])
"""
use collections of articles from wikiprojects
"""
