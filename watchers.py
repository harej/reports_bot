# -*- coding: utf-8 -*-
"""
Prepares list of WikiProject watchers
Copyright (C) 2015 James Hare
Licensed under MIT License: http://mitlicense.org
"""


import datetime
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

        runtime = datetime.datetime.utcnow().strftime('%H:%M, %d %B %Y (UTC)')
        q = ('select distinct page.page_title from page '
             'join categorylinks on page.page_id = categorylinks.cl_from '
             'left join redirect on page.page_id = redirect.rd_from '
             'where page_namespace = 4 '
             'and page_title not like "%/%" '
             'and rd_title is null '
             'and (cl_to in '
             '(select page.page_title from page '
             'where page_namespace = 14 and '
             'page_title like "%\_WikiProjects" '
             'and page_title not like "%\_for\_WikiProjects" '
             'and page_title not like "%\_of\_WikiProjects") '
             'or page_title like "WikiProject\_%");')
        formaldefinition = wptools.query('wiki', q, None)  # http://quarry.wmflabs.org/query/3509
        for row in formaldefinition:
            row = row[0].decode('utf-8')
            if row not in projects:
                projects.append(row)

        projects.sort()
        packages = [projects[i:i+50] for i in range(0, len(projects), 50)]

        report = {}
        for package in packages:
            url = "https://en.wikipedia.org/w/api.php?action=query&format=json&prop=info&inprop=watchers&titles="
            for title in package:
                url += title + "|"
            url = url[:-1]  # Truncate trailing pipe
            apiquery = requests.get(url)
            apiquery = apiquery.json()
            for pagedata in apiquery['query']['pages'].values():
                if 'watchers' in pagedata:
                    if pagedata['watchers'] > 29:  # Required part
                        report[pagedata['title']] = pagedata['watchers']

        report = sorted(report.items(), key=operator.itemgetter(1), reverse=True)

        contents = 'List of WikiProjects by number of watchers of its main page and talk page. A WikiProject not appearing on this list has fewer than 30 watchers. Data as of <onlyinclude>' + runtime + '</onlyinclude>'
        contents += '\n\n{| class="wikitable sortable plainlinks"\n|-\n! No.\n! WikiProject\n! Watchers\n'

        counter = 0
        for pair in report:
            counter += 1
            contents += "|-\n| {0}\n| [[{1}]]\n| {2}\n".format(str(counter), pair[0], pair[1])

        contents += "|}"

        page = pywikibot.Page(bot, saveto)
        page.text = contents
        page.save("Updating report", minor=False)


if __name__ == "__main__":
    go = WikiProjectWatchers()
    go.prepare("Wikipedia:Database reports/WikiProject watchers")