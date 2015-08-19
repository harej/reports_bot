# -*- coding: utf-8 -*-
"""
Generates a report for English Wikipedia articles with no Wikidata item
Copyright (C) 2015 James Hare
Licensed under MIT License: http://mitlicense.org
"""

import pywikibot
from project_index import WikiProjectTools
from urllib.parse import quote


def main():
    wptools = WikiProjectTools()
    bot = pywikibot.Site('en', 'wikipedia')

    q = ('select page_title from page where page_namespace = 0 '
         'and page_is_redirect = 0 order by page_id;'
    all_articles = [x[0].decode('utf-8') for x in wptools.query('wiki', q, None)]

    q = ('select page_title from page join page_props on pp_page = page_id '
         'where page_namespace = 0 and pp_propname = "wikibase_item '
         'order by page_id";')
    articles_on_wikidata = [x[0].decode('utf-8') \
                            for x in wptools.query('wiki', q, None)]

    no_wikidata = []
    for title in all_articles:
        if title not in articles_on_wikidata:
            no_wikidata.append(title)

    total_count = len(no_wikidata)  # Capturing this before truncating list
    no_wikidata = no_wikidata[:100]

    page = pywikibot.Page(bot, 'User:Reports_bot/No_Wikidata_item')

    content = "'''Total Articles Missing From Wikidata:''' " + str(total_count) + "\n\n"
    for title in no_wikidata:
        content += "* [[" + title.replace('_', ' ') + \
                   "]] ([https://www.wikidata.org/w/index.php?search=" + \
                   quote(title) + \
                   "&title=Special%3ASearch&fulltext=1 Search on Wikidata])\n"

    page.text = content
    page.save("Updating list", minor=False)


if __name__ == "__main__":
    main()