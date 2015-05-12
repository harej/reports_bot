# -*- coding: utf-8 -*-
"""
Loads wikiproject.json, validates it, stores it
Copyright (C) 2015 James Hare
Licensed under MIT License: http://mitlicense.org
"""

import os
import sys
import configparser
import json
import pywikibot
import datetime
from project_index import WikiProjectTools


def main():

    bot = pywikibot.Site('en', 'wikipedia')

    # Exports the contents of the wikiproject.json page
    page = pywikibot.Page(bot, 'Wikipedia:WikiProject X/wikiproject.json')
    output = page.text

    # We now have the JSON blob, in string format.
    try:
        output = json.loads(output)
    except ValueError as ack:  # If JSON is invalid
        now = datetime.datetime.utcnow()
        wikitime = now.strftime('%Y%m%d%H%M%S')
        page = pywikibot.Page(bot, 'Wikipedia talk:WikiProject X/wikiproject.json/Errors')
        page.text = str(wikitime) + ': ' + str(ack)
        page.save('Error while loading configuration')
        sys.exit()

    # At this point, we have valid JSON at our disposal. Time to save to the database.

    wptools = WikiProjectTools()
    wptools.query('index', 'create table config_draft (json mediumtext character set utf8 collate utf8_unicode_ci) engine=innodb character set=utf8;', None)
    wptools.query('index', 'insert into config_draft (json) values (%s);', (str(output),))
    wptools.query('index', 'drop table if exists config', None)
    wptools.query('index', 'rename table config_draft to config', None)

if __name__ == "__main__":
    main()