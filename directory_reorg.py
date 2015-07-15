# -*- coding: utf-8 -*-
"""
Re-organizes the WikiProject Directory without re-running the statistics
Copyright (C) 2015 James Hare, Betacommand, Merlijn Van Deen
Licensed under MIT License: http://mitlicense.org
"""


import mwparserfromhell as mwph
import pywikibot
from directory import WikiProjectDirectory
from project_index import WikiProjectTools
from category_tree import WikiProjectCategories


def main(rootpage):
    d = WikiProjectDirectory()
    wptools = WikiProjectTools()
    wpcats = WikiProjectCategories()
    tree = wpcats.generate()
    bot = pywikibot.Site('en', 'wikipedia')
    directories = {}
    directoryrow = {}
    projects = []

    # Generate directoryrows and projects lists based on the /All directory:
    page = pywikibot.Page(bot, rootpage + '/All')
    contents = mwph.parse(page.text)
    contents = contents.filter_templates()
    for t in contents:
        if t.name.strip() == "WikiProject directory entry":
            name = str(t.get('project').value).strip().replace(' ', '_')
            projects.append(name)
            directoryrow[name] = str(t) + "\n"

    # The rest of this stuff is copied from directory.py
    index_primary = sorted([key for key in tree.keys()])
    index_secondary = {}
    indextext = "'''[[{0}/All|All WikiProjects]]'''\n\n".format(rootpage)
    for firstlevel in tree.keys():
        directories[firstlevel] = "={0}=\n".format(firstlevel.replace('_', ' '))
        directories[firstlevel] += d.listpull(wptools, projects, directoryrow, firstlevel)  # For immmedate subcats of WikiProjects_by_area
        directories[firstlevel] += d.treeiterator(wptools, tree[firstlevel], projects, directoryrow, firstlevel)  # For descendants of those immediate subcats.
        index_secondary[firstlevel] = sorted([key for key in tree[firstlevel].keys()])

    # Updating the directory index
    for firstlevel in index_primary:
        firstlevel_normalized = firstlevel.replace('_', ' ')
        indextext += ";[[{0}/{1}|{1}]]".format(rootpage, firstlevel_normalized)
        if len(tree[firstlevel]) > 0:
            indextext += " : "
            for secondlevel in index_secondary[firstlevel]:
                indextext += "[[{0}/{1}#{2}|{2}]] – ".format(rootpage, firstlevel_normalized, secondlevel.replace('_', ' '))
            indextext = indextext[:-3]  # Truncates trailing dash and is also a cute smiley face
        indextext += "\n\n"
    saveindex = pywikibot.Page(bot, 'Template:WikiProject directory index')
    saveindex.text = indextext
    saveindex.save('Updating', minor=False, async=True)

    # Generate directories and save!
    for directory in directories.keys():
        contents = directories[directory]
        page = pywikibot.Page(bot, rootpage + "/" + directory)
        if contents != page.text:  # Checking to see if a change was made to cut down on API save queries
            oldcontents = page.text
            page.text = contents
            page.save('Updating', minor=False, async=True)


if __name__ == "__main__":
    main('Wikipedia:WikiProject Directory')