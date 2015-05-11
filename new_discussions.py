# -*- coding: utf-8 -*-
"""
New Discussions -- Provides a list of new discussions within a WikiProject's scope
Copyright (C) 2015 James Hare
Licensed under MIT License: http://mitlicense.org
"""

#import mw_lego # https://github.com/legoktm/supersimplemediawiki
#import mw
import re
import time
import datetime
from project_index import WikiProjectTools


def main():
    wptools = WikiProjectTools()

    now = datetime.datetime.utcnow()
    wikitime = now.strftime('%Y%m%d%H%M%S') # converts timestamp to MediaWiki format
    thirtyminutesago = (now - datetime.timedelta(minutes=30)).strftime('%Y%m%d%H%M%S')
    
    query = wptools.query('wiki', 'select distinct recentchanges.rc_title, recentchanges.rc_comment, recentchanges.rc_timestamp, page.page_namespace from recentchanges join page on recentchanges.rc_namespace = page.page_namespace and recentchanges.rc_title = page.page_title join categorylinks on page.page_id=categorylinks.cl_from where rc_timestamp >= ' + thirtyminutesago + ' and rc_timestamp < ' + wikitime + ' and rc_comment like "% new section" and rc_deleted = 0 and cl_to like "%_articles" and page_namespace not in (0, 2, 6, 8, 10, 12, 14, 100, 108, 118) order by rc_timestamp desc;', None)
    output = []

    namespace = {1: 'Talk:', 3: 'User_talk:', 4: 'Wikipedia:', 5: 'Wikipedia_talk:', 7: 'File_talk:', 9: 'MediaWiki_talk:', 11: 'Template_talk:', 13: 'Help_talk:', 15: 'Category_talk:', 101: 'Portal_talk:', 109: 'Book_talk:', 119: 'Draft_talk:'}

    for row in query:
        rc_title = row[0].decode('utf-8')

        rc_comment = row[1].decode('utf-8')
        rc_comment = rc_comment[3:]  # Truncate beginning part of the edit summary
        rc_comment = rc_comment[:-15]  # Truncate end of the edit summary

        rc_timestamp = row[2].decode('utf-8')

        page_namespace = row[3]  # An integer that requires no decoding
        page_namespace = namespace[page_namespace]

        output.append({'namespace': page_namespace, 'title': rc_title, 'section': rc_comment, 'timestamp': rc_timestamp})

    print(output)

if __name__ == "__main__":
    main()