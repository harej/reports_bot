# -*- coding: utf-8 -*-

"""
Updates membership lists for WikiProjects using the WikiProjectCard infrastructure
Copyright (C) 2015 James Hare, 2016 Ben Kurtovic
Licensed under MIT License: http://mitlicense.org
"""

from reportsbot.task import Task

__all__ = ["UpdateMembers"]

class UpdateMembers(Task):
    """Updates WikiProject member lists based on WikiProjectCard usage."""
    MEMBER_TEMPLATE = "WikiProjectCard"

    def _get_all_members(self):
        """Return a dict mapping projects to lists of members (usernames)."""
        self._logger.debug("Fetching member lists")

        query = """SELECT page_title FROM templatelinks
            JOIN page ON page_id = tl_from
            WHERE page_namespace = 2 AND tl_namespace = 10
            AND tl_title = ?"""

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
                project = components[2]

                if not self._bot.get_project("Wikipedia:" + project).exists:
                    continue

                if project in members:
                    members[project].append(username)
                else:
                    members[project] = [username]

        self._logger.info("%s total members in %s projects",
                          sum(len(L) for L in members.values()), len(members))

        return {project: sorted(users) for project, users in members.items()}

    def _update_project(self, project, members):
        """Update the active and inactive member lists for a single project."""
        self._logger.debug("Updating project: %s (%s members)", project,
                           len(members))

        active_title = "Project:" + project + "/Members"
        inactive_title = "Project:" + project + "/Members/Inactive"

        return_to_wikiproject = "{{Clickable button 2|Project:%s|Return to WikiProject|class=mw-ui-neutral}}<span class='wp-formsGadget mw-ui-button mw-ui-progressive' data-mode='create' data-type='Join'>Join WikiProject</span>" % project
        lua_garbage = "{{#invoke:<includeonly>random|list|limit=3</includeonly><noinclude>list|unbulleted</noinclude>|"
        active = "<noinclude>" + return_to_wikiproject + "\n\n<div style='padding-top:1.5em; padding-bottom:2em;'>Our WikiProject members are below. Those who have not edited Wikipedia in over a month are moved to the [[%s|inactive members list]].</div>\n\n</noinclude>" % inactive_title + lua_garbage
        inactive = "<noinclude>" + return_to_wikiproject + "\n\n<div style='padding-top:1.5em; padding-bottom:2em;'>These are our members who have not edited in a while. Once they edit again, they will be moved back to the [[%s|active members list]].</div>\n\n</noinclude>"% active_title + lua_garbage

        for member in members:
            addition = "{{User:" + member + "/WikiProjectCards/" + project + "<includeonly>|mode=compact</includeonly>}}|"
            if self._bot.get_user(member).is_active():
                active += addition
            else:
                inactive += addition

        active = active[:-1] + "}}"  # removing trailing pipe and closing off module
        inactive += "}}"

        page_active = self._bot.site.get_page(active_title)
        page_inactive = self._bot.site.get_page(inactive_title)

        if active != page_active.text:
            self._logger.debug("Saving active members: [[%s]]", active_title)
            page_active.text = active
            page_active.save("Updating member list", minor=False)

        if inactive != page_inactive.text:
            self._logger.debug("Saving inactive members: [[%s]]", inactive_title)
            page_inactive.text = inactive
            page_inactive.save("Updating member list", minor=False)

    def run(self):
        members = self._get_all_members()
        for project in members:
            self._update_project(project, members[project])
