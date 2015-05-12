# -*- coding: utf-8 -*-
"""
New Discussions -- Provides a list of new discussions within a WikiProject's scope
Copyright (C) 2015 James Hare
Licensed under MIT License: http://mitlicense.org
"""


import os
import configparser
import re
import time
import datetime
from mw import api
from mw.libs import reverts
from project_index import WikiProjectTools


def main():
    loginfile = configparser.ConfigParser()
    loginfile.read([os.path.expanduser('~/.wiki.ini')])
    username = loginfile.get('wiki', 'username')
    password = loginfile.get('wiki', 'password')

    wptools = WikiProjectTools()

    now = datetime.datetime.utcnow()
    wikitime = now.strftime('%Y%m%d%H%M%S') # converts timestamp to MediaWiki format
    thirtyminutesago = (now - datetime.timedelta(minutes=30)).strftime('%Y%m%d%H%M%S')
    
    # Polling for newest talk page posts in the last thirty minutes
    query = wptools.query('wiki', 'select distinct recentchanges.rc_id, page.page_id, recentchanges.rc_title, recentchanges.rc_comment, recentchanges.rc_timestamp, page.page_namespace from recentchanges join page on recentchanges.rc_namespace = page.page_namespace and recentchanges.rc_title = page.page_title join categorylinks on page.page_id=categorylinks.cl_from where rc_timestamp >= ' + thirtyminutesago + ' and rc_timestamp < ' + wikitime + ' and rc_comment like "% new section" and rc_deleted = 0 and cl_to like "%_articles" and page_namespace not in (0, 2, 6, 8, 10, 12, 14, 100, 108, 118) order by rc_timestamp desc;', None)

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
        page_namespace = row[5]
        page_namespace = namespace[page_namespace]

        entry = {'revid': rc_id, 'pageid': page_id, 'namespace': page_namespace, 'title': rc_title, 'section': rc_comment, 'timestamp': rc_timestamp}

        session = api.Session("https://en.wikipedia.org/w/api.php")
        session.login(username, password)

        # Check if revision has been reverted
        reverted = reverts.api.check(session, entry['revid'], entry['pageid'], 3, None, 172800, None)
        if reverted is not None:
            continue

        output.append(entry)

    print(output)

if __name__ == "__main__":
    main()