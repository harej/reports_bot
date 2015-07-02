# -*- coding: utf-8 -*-
"""
Article assessment-related worklists for WikiProjects.
Copyright (C) 2015 James Hare
Licensed under MIT License: http://mitlicense.org
"""


import requests
import pywikibot
import json
from project_index import WikiProjectTools


class WikiProjectAssess:
    def __init__(self):
        self.bot = pywikibot.Site('en', 'wikipedia')
        self.wptools = WikiProjectTools()
        self.projects = []
        self.predictorseed = {}
        self.unknownquality = {}
        self.unknownpriority = {}

        self.config = self.wptools.query('index', 'select json from config;', None)
        self.config = json.loads(self.config[0][0])

        for entry in self.config['projects']:
            if 'assessment_tools' in entry \
            and 'at_category' in entry \
            and 'at_unknown_quality' in entry \
            and 'at_unknown_priority' in entry:
                project = entry['name'][10:]  # Normalizing title
                self.projects.append(project)
                self.predictorseed[project] = entry['at_category'].replace(' ', '_')
                self.unknownquality[project] = entry['at_unknown_quality'].replace(' ', '_')
                self.unknownpriority[project] = entry['at_unknown_priority'].replace(' ', '_')


    def qualitypredictor(self, pagetitles):
        '''
        Makes a query to ORES that predicts the quality of an article.
        Takes list *pagetitles* as input
        Returns a list of tuples (title, prediction)
        Input MUST be a list. If only one title, enter it as [title]
        '''

        output = []

        # Split into packages
        packages = [pagetitles[i:i+50] for i in range(0, len(pagetitles), 50)]

        for package in packages:
            if len(package) > 1:
                q = ('select page_title, page_latest from page '
                     'where page_namespace = 0 and page_title in {0} '
                     'order by page_title limit 100;').format(tuple(package))
            else:
                q = ('select page_title, page_latest from page '
                     'where page_namespace = 0 '
                     'and page_title = "{0}";').format(package[0])

            revision_ids = {str(row[1]):row[0].decode('utf-8') \
                           for row in self.wptools.query('wiki', q, None)}
            api_input = [rev_id for rev_id in revision_ids.keys()]

            api_url = "http://ores.wmflabs.org/scores/enwiki/wp10/?revids="
            for rev_id in api_input:
                api_url += rev_id + "|"
            api_url = api_url[:-1]  # Truncating extra vertical pipe

            query = requests.get(api_url)
            query = query.json()
            for rev_id, result in query.items():
                pair = (revision_ids[rev_id], result['prediction'])
                output.append(pair)

        return output


    def qualitylist(self):
        for wikiproject, category in self.unknownquality.items():
            save_to = "User:Reports bot/" + wikiproject + \
                      "/Assessment/Assess for quality"
            q = ('select page_title from categorylinks '
                 'join page on cl_from = page_id '
                 'where cl_to = "{0}";').format(category.replace(' ', '_'))
            to_process = [row[0].decode('utf-8') \
                         for row in self.wptools.query('wiki', q, None)]
            to_process = self.qualitypredictor(to_process)
            contents = ("{{WPX list start|title=Assess for quality|intro="
                        "Determine the quality of these articles<br />"
                        "{{WPX last updated|" + save_to + "}}}}<br />\n\n"
                        "{{#invoke:<includeonly>random|list|limit=5"
                        "</includeonly><noinclude>list|unbulleted</noinclude>|")
            for pair in to_process:
                article = pair[0].replace("_", " ")
                prediction = pair[1]
                contents += "{{WPX block|largetext=<b>[[" + article + "]]</b> "\
                            + "([[Talk:" + article + "|talk]])|smalltext="\
                            + "Predicted class: " + prediction + "}}|"
            contents = contents[:-1] + "}}\n{{WPX list end|more=" + save_to \
                       + "}}"

            page = pywikibot.Page(self.bot, save_to)
            page.text = contents
            page.save("Updating listing", minor=False, async=True)


    def scopepredictor(self):
        for wikiproject, category in self.predictorseed.items():
            category_recs = []
            article_recs = []

            # This query produces a list of pages that belong to categories that
            # have been tagged by the WikiProject
            q = ('select page_namespace, page_title from page '
                 'join categorylinks on categorylinks.cl_from = page.page_id '
                 'where page_namespace in (0, 14) '
                 'and cl_to in ( '
                 'select page.page_title from page '
                 'join categorylinks on categorylinks.cl_from = page.page_id '
                 'where page_namespace = 15 '
                 'and cl_to = "{0}");').format(category)

            for row in self.wptools.query('wiki', q, None):
                ns = row[0]
                page = row[1].decode('utf-8')
                if ns == 0:
                    article_recs.append(page)
                elif ns == 14:
                    category_recs.append(page)

            # Filter against these lists:
            q = ('select pi_page from projectindex '
                 'where pi_project = "Wikipedia:{0}";')
            q = q.format(wikiproject.replace(' ', '_'))
            article_filter = [row[0].replace('Talk:', '') \
                             for row in self.wptools.query('index', q, None) \
                             if row[0].startswith('Talk')]

            q = ('select page_title from page '
                 'join categorylinks on cl_from = page_id '
                 'where page_namespace = 15 '
                 'and cl_to = "{0}";').format(category)
            category_filter = [row[0].decode('utf-8') \
                              for row in self.wptools.query('wiki', q, None)]

            # Now do the filtering...
            category_recs = list(set(category_recs) - set(category_filter))
            article_recs = list(set(article_recs) - set(article_filter))

            # Unite them together...
            recommendations = [':Category:' + name for name in category_recs] \
                              + [name for name in article_recs]

            # And lop it off at 100!
            recommendations = recommendations[:100]

            # Class prediction
            predicted_class = self.qualitypredictor([page for page in recommendations \
                              if page.startswith(':Category:') == False]) + \
                              [(page, 'Category') for page in recommendations \
                              if page.startswith(':Category:') == True]
            predicted_class = {pair[0]:pair[1] for pair in predicted_class}

            save_to = "User:Reports bot/" + wikiproject + "/Assessment/Not tagged"
            contents = ("{{WPX list start|title=Not tagged by the WikiProject|"
                        "intro=Add the WikiProject banner to relevant pages.<br />"
                        "{{WPX last updated|" + save_to + "}}}}<br />\n\n"
                        "{{#invoke:<includeonly>random|list|limit=5"
                        "</includeonly><noinclude>list|unbulleted</noinclude>|")
            for recommendation in recommendations:
                contents += "{{WPX block|largetext=<b>[[" \
                            + recommendation.replace('_', ' ') \
                            + "]]</b> ([[Talk:" + recommendation \
                            + "|talk]])|smalltext=Predicted class: " \
                            + predicted_class[recommendation] + "}}|"
            contents = contents.replace("Talk::Category:", "Category talk:")
            contents = contents[:-1] + "}}\n{{WPX list end|more=" + save_to \
                       + "}}"
            page = pywikibot.Page(self.bot, save_to)
            page.text = contents
            page.save("Updating listing", minor=False, async=True)


if __name__ == "__main__":
    run = WikiProjectAssess()
    run.qualitylist()
    run.scopepredictor()