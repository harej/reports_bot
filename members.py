# -*- coding: utf-8 -*-
"""
Updates membership lists for WikiProjects using the WikiProjectCard infrastructure
Copyright (C) 2015 James Hare
Licensed under MIT License: http://mitlicense.org
"""


import pywikibot
import mwparserfromhell
from project_index import WikiProjectTools
from notifications import WikiProjectNotifications


class WikiProjectMembers:
    def __init__(self):
        self.wptools = WikiProjectTools()


    def active_user(self, username):
        '''
        Determines if a username meets a basic threshold of activity
        Takes string *username*, returns boolean
        Threshold is one edit in the recent changes tables (i.e. in the past 30 days)
        '''

        q = 'select count(*) from recentchanges_userindex where rc_user_text = "{0}"'.format(username)
        if self.wptools.query('wiki', q, None)[0][0] > 0:
            return True
        else:
            return False


    def queue_notification(self, project, username):
        '''
        Queue new member notification
        '''

        wpn = WikiProjectNotifications()
        content = "* [[User:" + username + "|" + username + "]]"
        wpn.post(project, "newmember", content)


    def run(self):
        bot = pywikibot.Site('en', 'wikipedia')

        q = ('select page_title from templatelinks '
             'join page on page_id = tl_from and page_namespace = tl_from_namespace '
             'where page_namespace = 2 and tl_namespace = 10 '
             'and tl_title = "WikiProjectCard";')

        # Generate list of WikiProjects and members through the WikiProjectCard system
        members = {}
        for row in self.wptools.query('wiki', q, None):
            title = row[0].decode('utf-8')
            components = title.split('/')  # e.g. ['Harej', 'WikiProjectCards', 'WikiProject_Women_in_Technology']
            title = "User: " + title
            username = components[0]
            wikiproject = '/'.join(components[2:])  # In case the WikiProject name somehow has a slash in it

            if wikiproject in members:
                members[wikiproject].append(username)
            else:
                members[wikiproject] = [username]

        members = {wikiproject:sorted(memberlist) for wikiproject, memberlist in members.items()}

        for wikiproject in members:
            # Generate active member and inactive member lists
            return_to_wikiproject = "{{{{Clickable button 2|Wikipedia:{0}|Return to WikiProject|class=mw-ui-neutral}}}}<span class='wp-formsGadget mw-ui-button mw-ui-progressive' data-mode='create' data-type='Join'>Join WikiProject</span>".format(wikiproject)
            lua_garbage = "{{#invoke:<includeonly>random|list|limit=2</includeonly><noinclude>list|unbulleted</noinclude>|"
            active = "<noinclude>" + return_to_wikiproject + "\n\n<div style='padding-top:1.5em; padding-bottom:2em;'>Our WikiProject members are below. Those who have not edited Wikipedia in over a month are moved to the [[Wikipedia:{0}/Members/Inactive|inactive members list]].</div>\n\n</noinclude>".format(wikiproject) + lua_garbage
            inactive = "<noinclude>" + return_to_wikiproject + "\n\n<div style='padding-top:1.5em; padding-bottom:2em;'>These are our members who have not edited in a while. Once they edit again, they will be moved back to the [[Wikipedia:{0}/Members|active members list]].</div>\n\n</noinclude>".format(wikiproject) + lua_garbage

            for member in members[wikiproject]:
                addition = "{{User:" + member + "/WikiProjectCards/" + wikiproject + "}}|"
                if self.active_user(member):
                    active += addition
                else:
                    inactive += addition

            active = active[:-1] + "}}"  # removing trailing pipe and closing off module
            inactive += "}}"

            # Generate old list to prepare a diff
            page_active = pywikibot.Page(bot, "Wikipedia:" + wikiproject + "/Members")
            page_inactive = pywikibot.Page(bot, "Wikipedia:" + wikiproject + "/Members/Inactive")

            oldnames = []
            for text in [page_active.text, page_inactive.text]:
                contents = mwparserfromhell.parse(text)
                contents = contents.filter_templates()
                for t in contents:
                    if t.name[:5] == "User:":  # differentiating between {{Clickable button 2}} et. al. and the WikiProjectCards
                        oldnames.append(t.name.split("/")[0][5:])  # i.e. grab username from template

            newnames = list(set(members) - set(oldnames))
            newnames.sort()
            print(newnames)

            # Anyone in the *newnames* set is a new user. Queue the notification!
            for member in newnames:
                self.queue_notification(wikiproject, member)

            # Now, save pages.
            page_active.text = active
            page_active.save("Updating member list", minor=False, async=True)
            page_inactive.text = inactive
            page_inactive.save("Updating member list", minor=False, async=True)


if __name__ == "__main__":
    go = WikiProjectMembers()
    go.run()