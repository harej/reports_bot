# -*- coding: utf-8 -*-
"""
Prepares list of WikiProject watchers
Copyright (C) 2015 James Hare
Licensed under MIT License: http://mitlicense.org
"""


import operator
import pywikibot
import requests
from project_index import WikiProjectTools


class WikiProjectWatchers:
    def prepare(self, saveto):
        wptools = WikiProjectTools()
        bot = pywikibot.Site('en', 'wikipedia')

        # Retrieve list of WikiProjects
        projects = []
        for row in wptools.query('index', 'select distinct pi_project from projectindex;', None):
            projects.append(row[0])

        packages = []
        for i in range(0, len(projects), 250):
            packages.append(projects[i:i+50])

        report = {}
        for package in packages:
            url = "https://en.wikipedia.org/w/api.php?action=query&format=json&prop=info&inprop=watchers&titles="
            for title in package:
                url += title + "|"
            url = url[:-1]  # Truncate trailing pipe
            apiquery = requests.get(url)
            for pagedata in apiquery['query']['pages']:
                if 'watchers' in pagedata:
                    report[pagedata['title']] = pagedata['watchers']

        report = sorted(report.items(), key=operator.itemgetter(1), reverse=True)

        contents = 'List of WikiProjects by number of watchers of its main page and talk page. A WikiProject not appearing on this list has fewer than 30 watchers.'
        contents += '\n\n{| class="wikitable sortable plainlinks"\n|-\n! No.\n! WikiProject\n! Watchers\n'

        counter = 0
        for pair in report:
            counter += 1
            contents += "|-\n| {0}\n| {1}\n| {2}\n".format(str(counter), pair[0], pair[1])

        contents += "|}"

        page = pywikibot.Page(bot, saveto)
        page.text = contents
        page.save("Updating report", minor=False)


if __name__ == "__main__":
    go = WikiProjectWatchers()
    go.prepare("Wikipedia:Database reports/WikiProject watchers")