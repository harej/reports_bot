# -*- coding: utf-8 -*-
"""
Related Projects -- compares WikiProjects according to pages in common
Copyright (C) 2015 James Hare
Licensed under MIT License: http://mitlicense.org
"""


# import mw_lego # https://github.com/legoktm/supersimplemediawiki
import re
import operator
import pywikibot
from project_index import WikiProjectTools


def main():

    print("Loading...")
    wptools = WikiProjectTools()
    query = wptools.query('index', 'select pi_page, pi_project from projectindex;', None)

    pages = {}
    for row in query:
        pi_page = row[0]
        pi_project = row[1]
        try:
            pages[pi_project].append(pi_page)
        except KeyError:
            pages[pi_project] = [pi_page]

    # Compare!
    intersect_counts = {}
    regex = re.compile('/.*')
    for wikiproject_x in pages.keys():  # lol WikiProject X
        print("Working on: " + wikiproject_x)
        intersect_counts[wikiproject_x] = {}
        for wikiproject_y in pages.keys():
            if wikiproject_x == wikiproject_y:
                continue  # Don't compare a project to itself

            test1 = re.sub(regex, '', wikiproject_x)
            test2 = re.sub(regex, '', wikiproject_y)
            if test1 == test2:
                continue  # Filters out comparisons where one is a subpage of another

            s = set(pages[wikiproject_x])
            intersect_counts[wikiproject_x][wikiproject_y] = len([n for n in pages[wikiproject_y] if n in s])

    bot = pywikibot.Site('en', 'wikipedia')

    print("Sorting and saving...")
    for project in intersect_counts.keys():
        # Sorts from highest to lowest
        ordered = sorted(intersect_counts[project].items(), key=operator.itemgetter(1), reverse=True)
        saveto = 'Wikipedia:Related_WikiProjects/' + project[10:]
        page = pywikibot.Page(bot, saveto)
        draft = '<noinclude>\n===Related to [[' \
                + project.replace('_', ' ') + '|]]===\n</noinclude>'
        draft += '{{WPX list start|intro={{WPX last updated|' + saveto + '}}}}\n'
        for x in range(0, 10):
            if ordered[x][1] > 0:
                draft += "{{WPX block|color={{{1|#37f}}}|" \
                         + "largetext='''[[{0}|]]''' ([[Wikipedia:Related WikiProjects/{1}|view related]])|".format(ordered[x][0].replace('_', ' '), ordered[x][0].replace('_', ' ')[10:]) \
                         + "smalltext={0} articles in common}}}}\n".format(str(ordered[x][1]))
        draft += '{{WPX list end|more=' + saveto + '}}'
        if page.text != draft:
            page.text = draft
            page.save('Updating', minor=False, async=True, quiet=True)

if __name__ == "__main__":
    main()