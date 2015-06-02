# -*- coding: utf-8 -*-
"""
Produces a list of uncategorized WikiProjects
Copyright (C) 2015 James Hare, Legoktm
Licensed under MIT License: http://mitlicense.org
"""


import mwparserfromhell as mwph
import pywikibot
from project_index import WikiProjectTools
from category_tree import WikiProjectCategories


def treegen(tree):
    for key, value in tree.items():
        yield key
        if len(value) >  0:
            yield from treegen(value)


def main(rootpage, saveto):
    wptools = WikiProjectTools()
    bot = pywikibot.Site('en', 'wikipedia')
    projects = []
    output = 'These WikiProjects are not in any WikiProject meta-categories:\n\n'

    # Generating category whitelist
    wpcats = WikiProjectCategories()
    tree = wpcats.generate()
    whitelist = list(treegen(tree))  # Run through a simple generator function to produce a flat list
    whitelist = tuple(set(whitelist))  # De-duplicating and making into a tuple

    page = pywikibot.Page(bot, rootpage + '/All')
    contents = mwph.parse(page.text)
    contents = contents.filter_templates()
    for t in contents:
        if t.name.strip() == "WikiProject directory entry small":
            project = str(t.get('project').value).strip()

            # Give me a list of all the categories, as long as it's on the whitelist
            query = wptools.query('wiki', "select distinct cl_to from categorylinks join page on categorylinks.cl_from=page.page_id where page_namespace in (4, 14) and page_title = {0} and cl_to in {1};".format('"' + project + '"', whitelist), None)
            if len(query) == 0:  # If page is in none of the whitelisted categories
                output += "# [[Wikipedia:{0}|{0}]]\n".format(project.replace('_', ' '))

    page = pywikibot.Page(bot, saveto)
    page.text = output
    page.save('Updating', minor=False)
    

if __name__ == "__main__":
    main('Wikipedia:WikiProject Directory', 'User:Reports bot/Uncategorized WikiProjects')