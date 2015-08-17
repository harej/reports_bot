# -*- coding: utf-8 -*-
"""
Migrates WikiProject categories from the WikiProject page to its category.
Copyright (C) 2015 James Hare
Licensed under MIT License: http://mitlicense.org
"""


import pywikibot as pwb
from project_index import WikiProjectTools


def main():
    wptools = WikiProjectTools()
    bot = pwb.Site('en', 'wikipedia', user='Harej bot')

    # Generate list of WikiProjects with eponymous categories
    q = ('select page_title from page where page_namespace = 14 '
         'and page_title in (select page_title from page where '
         'page_namespace = 4 and page_title like "WikiProject_%" '
         'and page_is_redirect = 0);')

    pairs = [row[0].decode('utf-8') for row in wptools.query('wiki', q, None)]

    for pair in pairs:
        # Load WikiProject page
        project_page = pwb.Page(bot, 'Wikipedia:' + pair)

        # Preserve only categories that aren't in the style "X WikiProjects"
        preserve  = [c for c in pwb.textlib.getCategoryLinks(project_page.text) \
                     if str(c)[-15:] != ' WikiProjects]]']

        # Check for presence of removable categories; otherwise, don't bother
        if preserve != pwb.textlib.getCategoryLinks(project_page.text):

            # Load WikiProject category
            project_cat = pwb.Page(bot, 'Category:' + pair)
    
            # List categories to add to project category
            page_cats = [c for c in pwb.textlib.getCategoryLinks(project_page.text) \
                         if str(c)[-15:] == ' WikiProjects]]']
            cat_cats  = [c for c in pwb.textlib.getCategoryLinks(project_cat.text) \
                         if str(c)[-15:] == ' WikiProjects]]']
            to_add = list(set(page_cats) - set(cat_cats))

            # Make changes and save page
            project_cat.text = pwb.textlib.replaceCategoryLinks(project_cat.text, to_add, addOnly=True)
            project_page.text = pwb.textlib.replaceCategoryLinks(project_page.text, preserve)
            summary = "WikiProject category migration. See [[User:Harej bot/WikiProject category migration]]."
            project_page.save(summary, minor=False)
            project_cat.save(summary, minor=False)


if __name__ == "__main__":
    main()