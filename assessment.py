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
        self.config = json.loads(self.wptools.query('index', 'select json from config;', None)[0][0])
        self.projects = []
        self.predictorseed = {}
        self.unknownquality = {}
        self.unknownpriority = {}

        for project in self.config['projects']:
            if 'assessment_tools' in project \
            and 'at_category' in project \
            and 'at_unknown_quality' in project \
            and 'at_unknown_priority' in project:
                projectname = project['name'][10:]  # Normalizing title
                self.projects.append(projectname)
                self.predictorseed[projectname] = project['at_category'].replace(' ', '_')
                self.unknownquality[projectname] = project['at_unknown_quality'].replace(' ', '_')
                self.unknownpriority[projectname] = project['at_unknown_priority'].replace(' ', '_')


    def qualitypredictor(self, pagetitles):
        '''
        Makes a query to ORES that predicts the quality of an article.
        Takes list *pagetitles* as input, returns a list of tuples (title, prediction)
        Input MUST be a list. If only one title, enter it as [title]
        '''

        output = []

        # Split into packages
        packages = [pagetitles[i:i+50] for i in range(0, len(pagetitles), 50)]

        for package in packages:
            if len(package) > 1:
                q = 'select page_title, page_latest from page where page_namespace = 0 and page_title in {0} order by page_title limit 100;'.format(tuple(package))
            else:
                q = 'select page_title, page_latest from page where page_namespace = 0 and page_title = "{0}";'.format(package[0])

            revision_ids = {str(row[1]):row[0].decode('utf-8') for row in self.wptools.query('wiki', q, None)}
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
            save_to = "User:Reports bot/" + wikiproject + "/Assessment/Assess for quality"
            q = 'select page_title from categorylinks join page on cl_from = page_id where cl_to = "{0}";'.format(category.replace(' ', '_'))
            to_process = [row[0].decode('utf-8') for row in self.wptools.query('wiki', q, None)]
            to_process = self.qualitypredictor(to_process)
            contents = ("====Assess for quality====\n"
                        "Determine the quality of each article, then go to the "
                        "article's talk page and update the quality assessment "
                        "in the WikiProject's banner. Automated predictions are"
                        " provided to help you.\n\n"
                        "{{#invoke:<includeonly>random|bulleted_list|limit=5"
                        "</includeonly><noinclude>list|bulleted</noinclude>|")
            for pair in to_process:
                article = pair[0]
                prediction = pair[1]
                contents += "<b>[[" + article + "]]</b> ([[Talk:" + article + \
                            "|talk]])<br />Predicted quality: " + \
                            prediction + "|"
            contents = contents[:-1] + "}}"

            page = pywikibot.Page(self.bot, save_to)
            page.text = contents
            page.save("Updating listing", minor=False, async=True)
                

    def prioritylist(self):
        print("Agh! Not ready yet!")


    def scopepredictor(self):
        # This query produces a list of pages that belong to categories that
        # have been tagged by the WikiProject
        q = ('select distinct page_namespace, page_title from page '
             'join categorylinks on categorylinks.cl_from = page.page_id '
             'where page_namespace in (0, 14) '
             'and cl_to in ( '
             'select page.page_title from page '
             'join categorylinks on categorylinks.cl_from = page.page_id '
             'where page_namespace = 15 '
             'and cl_to = "{0}");')


if __name__ == "__main__":
    run = WikiProjectAssess()
    run.qualitylist()
    #run.prioritylist()
    #run.scopepredictor()