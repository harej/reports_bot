# -*- coding: utf-8 -*-
"""
Prepares the WikiProject category tree
Copyright (C) 2015 James Hare
Licensed under MIT License: http://mitlicense.org
"""

from pprint import pprint
from project_index import WikiProjectTools


class WikiProjectCategories:
    def generate(audit=False, production=True):
        '''
        "audit" prints the category tree to stdout
        "production" returns a dictionary for use in some other script
        '''

        wptools = WikiProjectTools()

        tree = {}
        query = 'select distinct page.page_title from categorylinks join page on categorylinks.cl_from=page.page_id where page_namespace = 14 and cl_to = "WikiProjects_by_area" and page_title like "%\_WikiProjects";'
        for row in wptools.query('wiki', query, None):
            category = row[0].decode('utf-8')
            tree[category] = {}
            nextquery = 'select distinct page.page_title from categorylinks join page on categorylinks.cl_from=page.page_id where page_namespace = 14 and cl_to = {0} and page_title like "%\_WikiProjects";'.format(category)
            for nextrow in wptools.query('wiki', nextquery, None):
                nextcategory = nextrow[0].decode('utf-8')
                tree[category][nextcategory] = {}

        if audit == True:
            pprint(tree)

        if production == True:
            return tree

if __name__ == "__main__":
    wpc = WikiProjectCategories()
    wpc.generate(audit=True, production=False)  # If the script is invoked directly, run in audit mode