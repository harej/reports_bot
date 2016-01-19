# -*- coding: utf-8 -*-
"""
Generates feed of subjects that have entries on Wikidata but not enwiki
Copyright (C) 2015 James Hare
Licensed under MIT License: http://mitlicense.org
"""


import json
import pywikibot
import requests
from project_index import WikiProjectTools


class WikidataMagic:
    def __init__(self):
        self.wptools = WikiProjectTools()
        self.bot = pywikibot.Site('en', 'wikipedia')


    def entitydata(self, item):
        url = 'https://www.wikidata.org/wiki/Special:EntityData/' + item + \
              '.json'
        r = requests.get(url)
        return r.json()


    def wikidataquery(self, query):
        url = 'https://wdq.wmflabs.org/api?q=' + query
        r = requests.get(url)
        return ['Q' + str(item) for item in r.json()['items']]


    def missing_from_enwiki(self, total_item_list):
        q = ("select pp_value from page_props "
             "where pp_propname = 'wikibase_item' and pp_value in {0}")
        q = q.format(tuple(total_item_list))
        on_enwiki = [item[0].decode('utf-8') \
                     for item in self.wptools.query('wiki', q, None) \
                     if item != None]
        return list(set(total_item_list) - set(on_enwiki))


    def missing_articles_report(self):
        config = self.wptools.query('index', 'select json from config;', None)
        config = json.loads(config[0][0])
        for entry in config['projects']:
            if 'wikidata_missing_articles' in entry:
                wikiproject = entry['name']  # e.g. "Wikipedia:WikiProject Something"
                wdq_query = entry['wikidata_missing_articles']

                # Coming up with list of Wikidata items of missing articles
                items_for_report = self.wikidataquery(wdq_query)
                items_for_report = self.missing_from_enwiki(items_for_report)
                items_for_report = items_for_report[:100]  # Truncate list

                # Generate the report itself!
                save_to = wikiproject + "/Tasks/Wikidata Missing Article Report"
                content = ("{{WPX list start|title=From Wikidata|"
                           "intro=Automatically generated list of missing articles"
                           "<br />{{WPX last updated|" + save_to + "}}}}\n"
                           "{{#invoke:<includeonly>random|list|limit=3"
                           "</includeonly><noinclude>list|unbulleted</noinclude>\n")

                for item in items_for_report:
                    data = self.entitydata(item)
                    data = data['entities'][item]

                    if 'labels' in data:
                        if 'en' in data['labels']:
                            label = "[[" + data['labels']['en']['value'] + "]]"
                        else:
                            label = "No English title available"
                    else:
                        label = "No English title available"

                    if 'descriptions' in data:
                        if 'en' in data['descriptions']:
                            description = data['descriptions']['en']['value']
                        else:
                            description = "No English description available"
                    else:
                        description = "No English Description available"
                    
                    content += "| {{WPX block|largetext='''" + label + \
                               "'''|smalltext=" + description + \
                               "<br />([[d:" + item + \
                               "|More information on Wikidata]])" + \
                               "|color={{{1|#37f}}}}}\n"

                # Wrap up report and save

                content += "}}\n{{WPX list end|more=" + save_to + "}}"

                page = pywikibot.Page(self.bot, save_to)
                page.text = content
                page.save("Updating task list", minor=False, async=True, quiet=True)


if __name__ == "__main__":
    run = WikidataMagic()
    run.missing_articles_report()