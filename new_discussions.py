# -*- coding: utf-8 -*-
"""
New Discussions -- Provides a list of new discussions within a WikiProject's scope
Copyright (C) 2015 James Hare
Licensed under MIT License: http://mitlicense.org
"""


import os
import configparser
import json
import time
import datetime
import pywikibot
import mwparserfromhell
from mw import api
from mw.lib import reverts
from notifications import WikiProjectNotifications
from project_index import WikiProjectTools


def main():
    # This is used for Aaron Halfaker's API wrapper...
    loginfile = configparser.ConfigParser()
    loginfile.read([os.path.expanduser('~/.wiki.ini')])
    username = loginfile.get('wiki', 'username')
    password = loginfile.get('wiki', 'password')

    # ...And this is for Pywikibot
    bot = pywikibot.Site('en', 'wikipedia')

    wptools = WikiProjectTools()

    now = datetime.datetime.utcnow()
    now = now.strftime('%Y%m%d%H%M%S') # converts timestamp to MediaWiki format

    # Pulling timestamp of the last time the script was run
    query = wptools.query('index', 'select lu_timestamp from lastupdated where lu_key = "new_discussions";', None)
    lastupdated = query[0][0]
    
    # Polling for newest talk page posts in the last thirty minutes
    query = wptools.query('wiki', 'select distinct recentchanges.rc_this_oldid, page.page_id, recentchanges.rc_title, recentchanges.rc_comment, recentchanges.rc_timestamp, page.page_namespace from recentchanges join page on recentchanges.rc_namespace = page.page_namespace and recentchanges.rc_title = page.page_title join categorylinks on page.page_id=categorylinks.cl_from where rc_timestamp >= {0} and rc_timestamp < {1} and rc_comment like "% new section" and rc_deleted = 0 and cl_to like "%_articles" and page_namespace not in (0, 2, 6, 8, 10, 12, 14, 100, 108, 118) order by rc_timestamp asc;'.format(lastupdated, now), None)

    # Update the Last Updated field with new timestamp
    wptools.query('index', 'update lastupdated set lu_timestamp = {0} where lu_key = "new_discussions";'.format(now), None)

    # Cleaning up output
    namespace = {1: 'Talk:', 3: 'User_talk:', 4: 'Wikipedia:', 5: 'Wikipedia_talk:', 7: 'File_talk:', 9: 'MediaWiki_talk:', 11: 'Template_talk:', 13: 'Help_talk:', 15: 'Category_talk:', 101: 'Portal_talk:', 109: 'Book_talk:', 119: 'Draft_talk:', 447: 'Education_Program_talk:', 711: 'TimedText_talk:', 829: 'Module_talk:', 2600: 'Topic:'}

    output = []
    for row in query:
        rc_id = row[0]
        page_id = row[1]
        rc_title = row[2].decode('utf-8')
        rc_comment = row[3].decode('utf-8')
        rc_comment = rc_comment[3:]  # Truncate beginning part of the edit summary
        rc_comment = rc_comment[:-15]  # Truncate end of the edit summary
        rc_timestamp = row[4].decode('utf-8')
        rc_timestamp = datetime.datetime.strptime(rc_timestamp, '%Y%m%d%H%M%S')
        rc_timestamp = rc_timestamp.strftime('%H:%M, %d %B %Y (UTC)')
        page_namespace = row[5]
        page_namespace = namespace[page_namespace]

        session = api.Session("https://en.wikipedia.org/w/api.php", user_agent='WPX Revert Checker')
        session.login(username, password)

        # Check if revision has been reverted
        reverted = reverts.api.check(session, rc_id, page_id, 3, None, 172800, None)
        if reverted is None:
            entry = {'title': (page_namespace + rc_title), 'section': rc_comment, 'timestamp': rc_timestamp}
            output.append(entry)

    # Loading list of WikiProjects signed up to get lists of new discussions
    config = json.loads(wptools.query('index', 'select json from config;', None)[0][0])
    
    if config['defaults']['new_discussions'] == False:  # i.e. if New Discussions is an opt-in system
        whitelist = []  # Whitelisted WikiProjects for new discussion lists
        for project in config['projects']:
            try:
                project['new_discussions']
            except KeyError:
                continue
            else:
                if project['new_discussions'] == True:
                    whitelist.append(project['name'])
    else:
        whitelist = None

    # A whitelist of [] is one where there is a whitelist, but it's just empty.
    # A whitelist of None is for situations where the need for a whitelist has been obviated.

    # Generating list of WikiProjects for each thread
    for thread in output:
        query = wptools.query('index', 'select distinct pi_project from projectindex where pi_page = %s;', (thread['title']))
        thread['wikiprojects'] = []
        for row in query:
            wikiproject = row[0].replace('_', ' ')
            if (whitelist is None) or (wikiproject in whitelist):
                thread['wikiprojects'].append(wikiproject)
        for wikiproject in thread['wikiprojects']:
            saveto = wikiproject + '/New discussions'
            page = pywikibot.Page(bot, saveto)
            draft = '<noinclude><div style="padding-bottom:1em;">{{{{Clickable button 2|{0}|Return to WikiProject|class=mw-ui-neutral}}}}</div>\n</noinclude>===New discussions===\n{{{{WPX last updated|{1}}}}}\n\n'.format(wikiproject, saveto)
            submission = '{{{{WPX new discussion|title={0}|section={1}|timestamp={2}}}}}\n'.format(thread['title'].replace('_', ' '), thread['section'], thread['timestamp'])
            index = mwparserfromhell.parse(page.text)
            index = index.filter_templates()
            templatelist = []
            for i in index:
                if i.name == "WPX new discussion":
                    templatelist.append(str(i))
            templatelist = templatelist[:14]  # Sayonara, old threads!
            page.text = draft + submission
            if len(templatelist) > 3:
                templatelist[2] += "<noinclude>"  # Anything after the third item will not be transcluded
                templatelist[len(templatelist) - 1] += "</noinclude>"
            for i in templatelist:
                page.text += i + "\n"
            page.text += "{{{{WPX block|largetext='''[//en.wikipedia.org/w/index.php?title={0}&action=watch Add this feed to your Watchlist]'''}}}}".format(saveto.replace(' ', '_'))
            page.save('New discussion on [[{0}]]'.format(thread['title'].replace('_', ' ')), minor=False)

if __name__ == "__main__":
    main()