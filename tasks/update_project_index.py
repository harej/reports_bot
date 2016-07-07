# -*- coding: utf-8 -*-

"""
Project Index -- prepares an index of WikiProjects and their in-scope pages for use by scripts
Copyright (C) 2015 James Hare
Licensed under MIT License: http://mitlicense.org
"""

from collections import namedtuple
import re

from BTrees.IIBTree import IIBTree
from oursql import ProgrammingError

from reportsbot.task import Task
from reportsbot.util import to_wiki_format

__all__ = ["UpdateProjectIndex"]

Project = namedtuple("Project", ["id", "title", "categories"])
Page = namedtuple("Page", ["id", "talkid", "ns", "title", "isredir"])

class UpdateProjectIndex(Task):
    """Updates the index of articles associated with each WikiProject."""

    def __init__(self, bot):
        super().__init__(bot)
        self._page_table = bot.wikiid + "_page"
        self._project_table = bot.wikiid + "_project"
        self._index_table = bot.wikiid + "_index"

    def _create_tables(self, cursor):
        """Create this wiki's various tables, using base_* as references."""
        self._logger.info("Creating index tables for %s", self._bot.wikiid)

        query1 = "DROP TABLE IF EXISTS {}"
        query2 = "CREATE TABLE {} LIKE {}"

        cursor.execute(query1.format(self._index_table))
        cursor.execute(query1.format(self._project_table))
        cursor.execute(query1.format(self._page_table))

        cursor.execute(query2.format(self._page_table, "base_page"))
        cursor.execute(query2.format(self._project_table, "base_project"))
        cursor.execute(query2.format(self._index_table, "base_index"))

    def _ensure_tables(self):
        """Ensure that all necessary tables exist for this wiki."""
        query = "SELECT 1 FROM {} LIMIT 1"
        with self._bot.localdb as cursor:
            try:
                cursor.execute(query.format(self._page_table))
                cursor.execute(query.format(self._project_table))
                cursor.execute(query.format(self._index_table))
            except ProgrammingError:
                self._create_tables(cursor)

    def _get_project_categories(self):
        """Return a list of Wikiproject classification categories."""
        query = r"""SELECT page_title
            FROM page
            WHERE page_namespace = 14 AND (
                page_title LIKE "%-Class\_%\_articles" OR
                page_title LIKE "Unassessed\_%\_articles" OR
                page_title LIKE "WikiProject\_%\_articles"
            )"""

        with self._bot.wikidb as cursor:
            cursor.execute(query)
            return [cat.decode("utf8") for (cat,) in cursor.fetchall()]

    def _find_project(self, cursor, name):
        """Return the ID and title of the given WikiProject's root page."""
        query1 = """SELECT page_id, page_namespace, page_title,
                rd_namespace, rd_title
            FROM page LEFT JOIN redirect ON rd_from = page_id
            WHERE page_title = ? AND page_namespace = 4"""
        query2 = """SELECT page_id
            FROM page
            WHERE page_namespace = ? AND page_title = ?"""

        candidates = ("WikiProject_%s" % name, "WikiProject_%ss" % name, name)
        for candidate in candidates:
            cursor.execute(query1, (candidate,))
            results = cursor.fetchall()
            if results:
                break
        else:
            raise ValueError(name)

        pid, ns, title, rns, rtitle = results[0]
        if rns and rtitle:
            cursor.execute(query2, (rns, rtitle))
            result = cursor.fetchall()
            if not result:  # Broken redirect?
                raise ValueError(name)
            pid = result[0][0]
            ns, title = rns, rtitle

        ns_name = self._bot.site.namespaces[ns].custom_name
        fulltitle = to_wiki_format(ns_name + ":" + title.decode("utf8"))
        return pid, fulltitle

    def _get_projects(self):
        """Return a list of valid WikiProjects.

        Each project is a 3-tuple: (project_id, project_title, categories).
        """
        self._logger.info("Building project list")
        categories = self._get_project_categories()
        catmap = {}

        # Extract and map project names to their categories:
        regex = r"""^
            (?:.*?-Class_|Unassessed_)?
            (?:.*?-importance_)?
            (?:WikiProject_)?
            (.*?)                               # Actual project name fragment
            (?:-related|_task_force)?
            _articles$"""
        for cat in categories:
            name = re.search(regex, cat, flags=re.VERBOSE).group(1)
            if not name:  # Shouldn't happen, but would break us if it did
                continue
            name = name[0].upper() + name[1:]  # Normalize
            if name in catmap:
                catmap[name].append(cat)
            else:
                catmap[name] = [cat]

        # Build the Project objects:
        projects = {}
        with self._bot.wikidb as cursor:
            for name, cats in catmap.items():
                try:
                    pid, title = self._find_project(cursor, name)
                except ValueError:
                    msg = "Rejecting project: %s (%s categories, first: %s)"
                    self._logger.debug(msg, name, len(cats), cats[0])
                    continue

                if pid in projects:
                    projects[pid].categories.extend(cats)
                else:
                    projects[pid] = Project(pid, title, cats)

        msg = "%s projects with %s total categories"
        total_cats = sum(len(proj.categories) for proj in projects.values())
        self._logger.info(msg, len(projects), total_cats)
        return list(projects.values())

    def _sync_projects(self, cursor, projects):
        """Synchronize the given projects with the database."""
        self._logger.info("Synchronizing projects")

        query1 = "SELECT project_id, project_title FROM {}"
        query2 = """DELETE {0}, {1}
            FROM {0} LEFT JOIN {1} ON project_id = index_project
            WHERE project_id = ?"""
        query3 = "INSERT INTO {} (project_id, project_title) VALUES (?, ?)"
        query4 = "UPDATE {} SET project_title = ? WHERE project_id = ?"

        query1 = query1.format(self._project_table)
        query2 = query2.format(self._project_table, self._index_table)
        query3 = query3.format(self._project_table)
        query4 = query4.format(self._project_table)

        cursor.execute(query1)
        old = dict(cursor.fetchall())
        new = {proj.id: proj.title for proj in projects}

        to_remove = old.keys() - new.keys()
        to_add = new.keys() - old.keys()
        to_update = [pid for pid in new.keys() & old.keys()
                     if new[pid] != old[pid]]

        msg = "Remove/add/update: %s/%s/%s"
        self._logger.info(msg, len(to_remove), len(to_add), len(to_update))

        cursor.executemany(query2, [(pid,) for pid in to_remove])
        cursor.executemany(query3, [(pid, new[pid]) for pid in to_add])
        cursor.executemany(query4, [(new[pid], pid) for pid in to_update])

    def _get_talkmap(self, cursor):
        """Return a dict mapping talk page IDs to subject page IDs.

        Actually, this is misleading. The map also stores whether the subject
        page is a redirect, and for maximum space efficiency, we do this by
        shifting the subject page ID right by one bit and storing the boolean
        in the least significant bit.
        """
        self._logger.info("Building talkmap")

        query = """SELECT talk.page_id, subj.page_id, subj.page_is_redirect
        FROM page AS talk
        INNER JOIN page AS subj ON talk.page_title = subj.page_title
            AND talk.page_namespace = subj.page_namespace + 1
        WHERE talk.page_namespace % 2 = 1"""

        talkmap = IIBTree()
        cursor.execute(query)
        self._logger.debug("Fetching result chunks")
        while True:
            resultset = cursor.fetchmany(100000)
            if not resultset:
                break

            self._logger.debug(
                "Fetched chunk (%s+%s)", len(talkmap), len(resultset))
            for talkid, subjectid, isredir in resultset:
                talkmap[talkid] = (subjectid << 1) | isredir

        return talkmap

    def _get_pages_in_project(self, cursor, talkmap, project):
        """Return a list of Page objects within the given project.

        Each page is a 5-tuple of (subject_page_id, talk_page_id,
        subject_page_ns, title, subject_is_redirect).
        """
        query = """SELECT DISTINCT page_id, page_namespace - 1, page_title
            FROM page
            JOIN categorylinks ON cl_from = page_id
            WHERE cl_type = "page" AND page_namespace % 2 = 1
            AND cl_to IN ({})"""

        query = query.format(", ".join("?" * len(project.categories)))
        cursor.execute(query, project.categories)
        pages = [Page(talkmap[talkid] >> 1, talkid, ns, title.decode("utf8"),
                      bool(talkmap[talkid] & 1))
                 for (talkid, ns, title) in cursor.fetchall()
                 if talkid in talkmap]

        self._logger.debug("    %s pages", len(pages))
        return pages

    def _save_modified_pages(self, cursor, to_remove, to_add, to_update):
        """Update modified pages in the database."""
        msg = "    remove/add/update: %s/%s/%s"
        self._logger.debug(msg, len(to_remove), len(to_add), len(to_update))

        query1 = """DELETE {0}, {1}
            FROM {0} LEFT JOIN {1} ON page_id = index_page
            WHERE page_talk_id = ?"""
        query2 = """INSERT INTO {}
            (page_id, page_talk_id, page_title, page_ns, page_is_redirect)
            VALUES (?, ?, ?, ?, ?)"""
        query3 = """UPDATE {}
            SET page_talk_id = ?, page_title = ?, page_ns = ?,
                page_is_redirect = ?
            WHERE page_id = ?"""

        query1 = query1.format(self._page_table, self._index_table)
        query2 = query2.format(self._page_table)
        query3 = query3.format(self._page_table)

        # TODO: optimization candidates:
        cursor.executemany(query1, to_remove)
        cursor.executemany(query2, to_add)
        cursor.executemany(query3, to_update)

    def _sync_pageset(self, cursor, pages):
        """Synchronize every page in the given list with the database."""
        query = """SELECT page_id, page_talk_id, page_title, page_ns,
                page_is_redirect
            FROM {}
            WHERE page_id IN (%s)""".format(self._page_table)

        pageids = [page.id for page in pages]
        cursor.execute(query % ", ".join("?" * len(pages)), pageids)
        current = {row[0]: row[1:] for row in cursor.fetchall()}

        to_remove = []
        to_add = []
        to_update = []

        for page in pages:
            new = (page.talkid, page.title, page.ns, page.isredir)
            if page.id in current:
                cur = current[page.id]
                if new != cur:
                    if page.talkid != cur[0]:
                        # The talk page of this subject page has changed IDs,
                        # indicating that stuff has been moved around; we need
                        # to ensure that the talk page's previous entry in the
                        # database is removed (if any) before we update it
                        # since talk IDs are uniquely indexed:
                        to_remove.append((page.talkid,))
                    to_update.append(new + (page.id,))
            else:
                to_add.append((page.id,) + new)

        self._save_modified_pages(cursor, to_remove, to_add, to_update)

    def _sync_pages(self, cursor, processed, pages):
        """Synchronize the given list of pages with the database.

        Pages whose IDs are in in the processed set are skipped. The other
        pages are added to the set after processing.
        """
        unprocessed = [page for page in pages if page.id not in processed]
        self._logger.debug("    %s unprocessed to check", len(unprocessed))
        chunksize = 10000

        for start in range(0, len(unprocessed), chunksize):
            chunk = unprocessed[start:start+chunksize]
            num = int(start / chunksize) + 1
            self._logger.debug("    sync chunk #%s: %s pages", num, len(chunk))
            self._sync_pageset(cursor, chunk)

        processed |= {page.id for page in unprocessed}

    def _get_current_index(self, cursor, project):
        """Return a list of page IDs currently indexed in the given project."""
        query = "SELECT index_page FROM {} WHERE index_project = ?"
        cursor.execute(query.format(self._index_table), (project.id,))
        return [pageid for (pageid,) in cursor.fetchall()]

    def _sync_index(self, cursor, project, newpages, oldids):
        """Synchronize the index table for the given project."""
        newids = [page.id for page in newpages]

        msg = "    sync index: %s -> %s (change: %s)"
        change = len(set(oldids) ^ set(newids))
        self._logger.debug(msg, len(oldids), len(newids), change)

        query1 = "DELETE FROM {} WHERE index_page = ? AND index_project = ?"
        query2 = "INSERT INTO {} (index_page, index_project) VALUES (?, ?)"

        query1 = query1.format(self._index_table)
        query2 = query2.format(self._index_table)

        to_remove = set(oldids) - set(newids)
        to_add = set(newids) - set(oldids)

        # TODO: optimization candidates:
        cursor.executemany(query1, [(pid, project.id) for pid in to_remove])
        cursor.executemany(query2, [(pid, project.id) for pid in to_add])

    def _clear_old_pages(self, cursor, valid):
        """Remove all pages from the database that aren't in the given set."""
        query1 = "SELECT page_id FROM {}"
        query2 = "DELETE FROM {} WHERE page_id = ?"

        query1 = query1.format(self._page_table)
        query2 = query2.format(self._page_table)

        cursor.execute(query1)
        current = {pageid for (pageid,) in cursor.fetchall()}
        to_remove = current - valid

        # TODO: optimization candidate:
        cursor.executemany(query2, [(pageid,) for pageid in to_remove])

    def _sync_pages_and_index(self, cursor, projects):
        """Synchronize the database's page and index tables."""
        with self._bot.wikidb as wcursor:
            talkmap = self._get_talkmap(wcursor)
            processed = set()

            self._logger.info("Synchronizing pages and index")
            for project in projects:
                self._logger.debug("Processing: %s", project.title)
                pages = self._get_pages_in_project(wcursor, talkmap, project)
                self._sync_pages(cursor, processed, pages)
                current = self._get_current_index(cursor, project)
                self._sync_index(cursor, project, pages, current)

            self._clear_old_pages(cursor, processed)

    def run(self):
        self._ensure_tables()
        projects = self._get_projects()

        with self._bot.localdb as cursor:
            self._sync_projects(cursor, projects)
            self._sync_pages_and_index(cursor, projects)
