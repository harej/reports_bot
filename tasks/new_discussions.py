# -*- coding: utf-8 -*-

"""
New Discussions -- Provides a list of new discussions within a WikiProject's scope
Copyright (C) 2015 James Hare, 2016 Ben Kurtovic
Licensed under MIT License: http://mitlicense.org
"""

from collections import namedtuple
from datetime import datetime
import re

from reportsbot.task import Task
from reportsbot.util import join_full_title

import mwparserfromhell
from pywikibot.data.api import Request

__all__ = ["NewDiscussions"]

_Section = namedtuple("_Section", ["name", "timestamp"])
_Discussion = namedtuple("_Discussion", ["title", "name", "timestamp"])

class NewDiscussions(Task):
    """Updates a list of new discussions within a WikiProject's scope."""
    DISCUSSION_TEMPLATE = "WPX new discussion"
    DISCUSSIONS_PER_PAGE = 15
    DISCUSSIONS_BEFORE_FOLD = 4

    @staticmethod
    def _parse_timestamp(text):
        """Return a datetime for the given timestamp string, or ValueError."""
        return datetime.strptime(str(text), "%H:%M, %d %B %Y (UTC)")

    def _extract_sections(self, text):
        """Return a list of section tuples for the given page."""
        code = mwparserfromhell.parse(text)
        sections = set()

        for section in code.get_sections(levels=[2]):
            clean = section.strip_code()
            match = re.search(r"\d\d:\d\d,\s\d\d?\s\w+\s\d{4}\s\(UTC\)", clean)
            if not match:
                continue
            try:
                timestamp = self._parse_timestamp(match.group(0))
            except ValueError:
                continue

            name = str(section.get(0).title.strip_code()).strip()
            sections.add(_Section(name, timestamp))

        return sections

    def _load_pages(self, revids):
        """Load a chunk of pages from the API by revision."""
        req = Request(self._bot.site, parameters={
            "action": "query", "prop": "revisions", "rvprop": "content",
            "revids": "|".join(str(revid) for revid in revids)
        })

        data = req.submit()
        return [(page["title"], page["revisions"][0]["*"])
                for page in data["query"]["pages"].values()
                if "*" in page["revisions"][0]]

    def _get_updated_discussions(self, start, end):
        """Return a dict mapping talk page titles to lists of section tuples.

        The only pages included in the dict are those that have been updated
        in the given time range.
        """
        query = """SELECT MAX(rc_this_oldid)
            FROM recentchanges
            WHERE rc_timestamp >= ? AND rc_timestamp < ?
            AND rc_namespace % 2 = 1 AND rc_namespace != 3
            AND (rc_type = 0 OR rc_type = 1) AND rc_bot = 0
            GROUP BY rc_namespace, rc_title"""
        # TODO: generate events for pages that have been moved/deleted

        startts = start.strftime("%Y%m%d%H%M%S")
        endts = end.strftime("%Y%m%d%H%M%S")
        self._logger.info("Fetching discussions updated between %s and %s",
                          startts, endts)

        with self._bot.wikidb as cursor:
            cursor.execute(query, (startts, endts))
            revids = [revid for (revid,) in cursor.fetchall()]

        self._logger.debug("Fetching sections for %s pages", len(revids))

        sections = {}
        chunksize = 50
        for start in range(0, len(revids), chunksize):
            chunk = revids[start:start+chunksize]
            pages = self._load_pages(chunk)
            sections.update({title: self._extract_sections(text)
                             for title, text in pages})

        return sections

    def _get_current_discussions(self, title):
        """Return a dict mapping talk page titles to lists of section tuples.

        Given a WikiProject new discussions page, return all discussions
        currently listed.
        """
        text = self._bot.get_page(title).text
        code = mwparserfromhell.parse(text)
        discussions = {}

        for tmpl in code.filter_templates():
            if tmpl.name != self.DISCUSSION_TEMPLATE:
                continue
            if not (tmpl.has("title") and tmpl.has("section") and
                    tmpl.has("timestamp")):
                continue

            try:
                timestamp = self._parse_timestamp(tmpl.get("timestamp").value)
            except ValueError:
                continue
            title = str(tmpl.get("title").value)
            section = _Section(tmpl.get("section").value, timestamp)
            if title in discussions:
                discussions[title].add(section)
            else:
                discussions[title] = {section}

        return discussions

    def _process_discussions(self, pages, current, updated):
        """Return a sorted list of the most recent discussion tuples."""
        sections = {}

        for page in pages:
            title = join_full_title(self._bot.site, page.ns + 1, page.title)
            if title in updated:
                sections[title] = updated[title]
            elif title in current:
                sections[title] = current[title]

        discussions = [_Discussion(title, section.name, section.timestamp)
                       for title in sections for section in sections[title]]
        discussions.sort(key=lambda disc: disc.timestamp, reverse=True)
        return discussions[:self.DISCUSSIONS_PER_PAGE]

    def _save_discussions(self, project, title, discussions):
        """Save the given list of discussions to the given page title."""
        text = """<noinclude><div style="padding-bottom:1em;">{{Clickable button 2|%(projname)s|Return to WikiProject|class=mw-ui-neutral}}</div></noinclude>
{{WPX action box|color={{{2|#086}}}|title=Have a question?|content=
{{Clickable button 2|url={{fullurl:%(projtalk)s|action=edit&section=new}}|Ask the WikiProject|class=mw-ui-progressive mw-ui-block}}

{{Clickable button 2|%(projtalk)s|View Other Discussions|class=mw-ui-block}}
}}
{{WPX list start|intro={{WPX last updated|%(title)s}}}}
%(discussions)s
{{WPX list end|more=%(title)s}}
        """
        template = "{{WPX new discussion|color={{{1|#37f}}}|title=%(title)s|section=%(name)s|timestamp=%(timestamp)s}}"

        discitems = [
            template % {
                "title": disc.title,
                "name": disc.name,
                "timestamp": disc.timestamp.strftime("%H:%M, %d %B %Y (UTC)")
            }
            for disc in discussions]

        fold = self.DISCUSSIONS_BEFORE_FOLD
        if len(discitems) > fold:
            before = "\n".join(discitems[:fold])
            after = "\n".join(discitems[fold:])
            disclist = before + "<noinclude>\n" + after + "</noinclude>"
        else:
            disclist = "\n".join(discitems)

        projtalk = self._bot.get_page(project.name).toggleTalkPage().title()

        page = self._bot.get_page(title)
        page.text = text % {
            "title": title,
            "projname": project.name,
            "projtalk": projtalk,
            "discussions": disclist
        }
        page.save("Updating new discussions", minor=False)

    def _process(self, project, updated):
        """Process new discussions for the given project."""
        self._logger.info("Updating new discussions for %s", project.name)
        title = project.name + "/Discussions"

        pages = project.get_members()
        current = self._get_current_discussions(title)
        discussions = self._process_discussions(pages, current, updated)
        self._save_discussions(project, title, discussions)

    def run(self):
        start = self._bot.get_last_updated("new_discussions")
        end = datetime.utcnow()
        updated = self._get_updated_discussions(start, end)

        for project in self._bot.get_configured_projects():
            if project.config.get("new_discussions"):
                self._process(project, updated)

        self._bot.set_last_updated("new_discussions", end)
