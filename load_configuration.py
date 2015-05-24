# -*- coding: utf-8 -*-
"""
Loads wikiproject.json, validates it, stores it
Copyright (C) 2015 James Hare
Licensed under MIT License: http://mitlicense.org
"""

import sys
import json
import pywikibot
import datetime
from project_index import WikiProjectTools

class WPXConfig:
    def stopthepresses(self, bot, message):
        now = datetime.datetime.utcnow()
        wikitime = now.strftime('%Y%m%d%H%M%S')
        page = pywikibot.Page(bot, 'Wikipedia talk:WikiProject X/wikiproject.json/Errors')
        page.text = str(wikitime) + ': ' + message
        page.save('Error while loading configuration', minor=False)
        sys.exit()
    
    def validatebyiterate(self, bot, schema, tocheck):
        for entry in tocheck:
            for setting in entry:
                if setting not in schema:
                    self.stopthepresses(bot, 'Invalid setting {0} in project entry {1}'.format(setting, entry))
    
    def now(self):
        bot = pywikibot.Site('en', 'wikipedia')
    
        # Exports the contents of the wikiproject.json page
        page = pywikibot.Page(bot, 'Wikipedia:WikiProject X/wikiproject.json')
        output = page.text
    
        # We now have the JSON blob, in string format.
        try:
            output = json.loads(output)
        except ValueError as ack:  # If JSON is invalid
            self.stopthepresses(bot, str(ack))
    
        # At this point, we have valid JSON at our disposal. But does it comply with the schema?
        schema = list(output['schema'].keys())
        self.validatebyiterate(bot, schema, output['defaults'])
        self.validatebyiterate(bot, schema, output['projects'])
    
        # If the script hasn't been killed yet by validatebyiterate(), 
        output = json.dumps(output)
        wptools = WikiProjectTools()
        wptools.query('index', 'create table config_draft (json mediumtext character set utf8 collate utf8_unicode_ci) engine=innodb character set=utf8;', None)
        wptools.query('index', 'insert into config_draft (json) values (%s);', (str(output),))
        wptools.query('index', 'drop table if exists config', None)
        wptools.query('index', 'rename table config_draft to config', None)

if __name__ == "__main__":
    run = WPXConfig()
    run.now()