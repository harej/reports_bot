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
    
    query = wptools.query('wiki', 'select distinct recentchanges.rc_title, recentchanges.rc_comment, recentchances.rc_timestamp, page.page_namespace from recentchanges join page on recentchanges.rc_namespace = page.page_namespace and recentchanges.rc_title = page.page_title join categorylinks on page.page_id=categorylinks.cl_from where rc_timestamp >= %s and rc_timestamp < %s and rc_comment like "% new section" and rc_deleted = 0 and cl_to like "%_articles" and page_namespace not in (0, 2, 6, 8, 10, 12, 14, 100, 108, 118) order by rc_timestamp desc;', (wikitime, thirtyminutesago))
    
    rows = []
    for row in query:
        print(row)

if __name__ == "__main__":
    main()