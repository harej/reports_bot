# -*- coding: utf-8 -*-

"""
Updates membership lists for WikiProjects using the WikiProjectCard infrastructure
Copyright (C) 2015 James Hare
Licensed under MIT License: http://mitlicense.org
"""

import pywikibot
import mwparserfromhell

from reportsbot.task import Task

__all__ = ["UpdateMembers"]

class UpdateMembers(Task):
    """
    Updates WikiProject member lists based on WikiProjectCard transclusions.
    """
    MEMBER_TEMPLATE = "WikiProjectCard"

    def _get_all_members(self):
        """Return a dict mapping projects to lists of members (usernames)."""
        query = """SELECT page_title FROM templatelinks
            JOIN page ON page_id = tl_from
            WHERE page_namespace = 2 AND tl_namespace = 10
            AND tl_title = %s"""

        members = {}
        with self._bot.wikidb as cursor:
            cursor.execute(query, (self.MEMBER_TEMPLATE,))
            for row in cursor.fetchall():
                title = row[0].decode('utf-8')
                if title.count("/") < 2:
                    continue

                # 'Users:Harej/WikiProjectCards/WikiProject_Women_in_Technology' ->
                # ['Harej', 'WikiProjectCards', 'WikiProject_Women_in_Technology']
                components = title.split("/", 2)
                if components[1] != "WikiProjectCards":
                    continue

                username = components[0]
                wikiproject = components[2]
                if wikiproject in members:
                    members[wikiproject].append(username)
                else:
                    members[wikiproject] = [username]

        return {project: sorted(users) for project, users in members.items()}

    def run(self):
        members = self._get_all_members()

        for wikiproject in members:
            # Generate active member and inactive member lists:
            return_to_wikiproject = "{{{{Clickable button 2|Wikipedia:{0}|Return to WikiProject|class=mw-ui-neutral}}}}<span class='wp-formsGadget mw-ui-button mw-ui-progressive' data-mode='create' data-type='Join'>Join WikiProject</span>".format(wikiproject)
            lua_garbage = "{{#invoke:<includeonly>random|list|limit=3</includeonly><noinclude>list|unbulleted</noinclude>|"
            active = "<noinclude>" + return_to_wikiproject + "\n\n<div style='padding-top:1.5em; padding-bottom:2em;'>Our WikiProject members are below. Those who have not edited Wikipedia in over a month are moved to the [[Wikipedia:{0}/Members/Inactive|inactive members list]].</div>\n\n</noinclude>".format(wikiproject) + lua_garbage
            inactive = "<noinclude>" + return_to_wikiproject + "\n\n<div style='padding-top:1.5em; padding-bottom:2em;'>These are our members who have not edited in a while. Once they edit again, they will be moved back to the [[Wikipedia:{0}/Members|active members list]].</div>\n\n</noinclude>".format(wikiproject) + lua_garbage

            for member in members[wikiproject]:
                addition = "{{User:" + member + "/WikiProjectCards/" + wikiproject + "<includeonly>|mode=compact</includeonly>}}|"
                if self._bot.get_user(member).is_active():
                    active += addition
                else:
                    inactive += addition

            active = active[:-1] + "}}"  # removing trailing pipe and closing off module
            inactive += "}}"

            # Generate old list to prepare a diff
            page_active = pywikibot.Page(self._bot.site, "Wikipedia:" + wikiproject + "/Members")
            page_inactive = pywikibot.Page(self._bot.site, "Wikipedia:" + wikiproject + "/Members/Inactive")

            oldnames = []
            for text in [page_active.text, page_inactive.text]:
                contents = mwparserfromhell.parse(text)
                contents = contents.filter_templates()
                for t in contents:
                    if t.name[:5] == "User:":  # differentiating between {{Clickable button 2}} et. al. and the WikiProjectCards
                        oldnames.append(t.name.split("/")[0][5:])  # i.e. grab username from template

            newnames = list(set(members[wikiproject]) - set(oldnames))
            newnames.sort()

            # Now, save pages.
            page_active.text = active
            page_active.save("Updating member list", minor=False)
            page_inactive.text = inactive
            page_inactive.save("Updating member list", minor=False)
