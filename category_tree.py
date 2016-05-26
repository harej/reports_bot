# -*- coding: utf-8 -*-
"""
Prepares the WikiProject category tree
Copyright (C) 2015 James Hare, Merlijn Van Deen
Licensed under MIT License: http://mitlicense.org
"""

from pprint import pprint

from project_index import WikiProjectTools

def build_cat_tree(cat_name, max_depth=5):
    if max_depth == 0:
        return None
    wptools = WikiProjectTools()
    query = wptools.query('wiki', 'select distinct page.page_title from categorylinks join page on categorylinks.cl_from=page.page_id where page_namespace = 14 and cl_to = "{0}" and page_title like "%\_WikiProjects" and page_title not like "Inactive_%";'.format(cat_name), None)
    retval = {}
    for row in query:
        category = row[0].decode('utf-8')
        retval[category] = build_cat_tree(category, max_depth=max_depth-1)
    return retval


class WikiProjectCategories:
    def generate(self, audit=False, production=True):
        '''
        "audit" prints the category tree to stdout
        "production" returns a dictionary for use in some other script
        '''

        tree = build_cat_tree('WikiProjects_by_area', max_depth=10)

        if audit == True:
            pprint(tree)

        if production == True:
            return tree


if __name__ == "__main__":
    wpc = WikiProjectCategories()
    wpc.generate(audit=True, production=False)  # If the script is invoked directly, run in audit mode
