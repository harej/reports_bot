# -*- coding: utf-8 -*-
"""
Roundabout implementation of SuggestBot for WikiProjects.
Copyright (C) 2015 James Hare
Licensed under MIT License: http://mitlicense.org
"""


import time  # Whoa.
import json
import pywikibot
from project_index import WikiProjectTools


def main(rootpage):
    bot = pywikibot.Site('en', 'wikipedia')
    wptools = WikiProjectTools()
    config = json.loads(wptools.query('index', 'select json from config;', None)[0][0])

    postto = []
    # In this loop, *project* is a dictionary of configurations
    for project in config['projects']:
        if 'suggestbot' in project:  # Is the key even defined?
            if project['suggestbot'] == True and project['type'] == 'Category':
                postto.append(project['name'])
                page = pywikibot.Page(bot, rootpage + '/SuggestFarm/' + project['name'][10:])
                page.text = "{{{{User:SuggestBot/suggest|Category:{0}}}}}".format(project['source'])
                page.save("Requesting latest recommendations from SuggestBot", minor=False)

    print("Sleeping for 30 minutes.")
    time.sleep(1800)  # Sleeping 30 minutes to wait for SuggestBot to do its thing

    # In this loop, *project* is a string (the name of the project)
    for project in postto:
        page = pywikibot.Page(bot, rootpage + '/SuggestFarm/' + project[10:])\
        # Isolating the table from the output
        table = page.text.split('{|', 1)[1]
        table = table.split('|}', 1)[0]
        table = '{|\n' + table + '\n|}'

        # Saving table to WikiProject
        page = pywikibot.Page(bot, project + '/Edit articles')
        page.text = '===Edit articles===\n{{WPX last updated|' + project + '/Edit articles' + '}}\n\n' + table
        page.save("Updating list", minor=False, async=True)


if __name__ == "__main__":
    main('User:Reports bot')