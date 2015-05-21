# -*- coding: utf-8 -*-
"""
Updates the WikiProject Directory
Copyright (C) 2015 Betacommand, James Hare
Licensed under MIT License: http://mitlicense.org
"""


import re
import pywikibot
from project_index import WikiProjectTools


def main():
    # Initializing...
    bot = pywikibot.Site('en', 'wikipedia')
    wptools = WikiProjectTools()
    config = eval(wptools.query('index', 'select json from config;', None)[0][0])
    print("Let's get this show on the road!")

    # Get list of people who opted out
    optout = pywikibot.Page(bot, 'User:Reports bot/Opt-out')
    blacklist = []
    regexes =[re.findall('\[\[User:(.*?)\|',optout.text,re.I), re.findall('\{\{user\|(.*?)\}\}',optout.text,re.I), re.findall('\[\[:User:(.*?)\]',optout.text,re.I), re.findall('\[\[:User talk:(.*?)\]',optout.text,re.I)]
    for results in regexes:
        for user in results:
            blacklist.append(user)
    print(str(len(blacklist)) + ' users opting out')
    # Bots are to be excluded
    for result in wptools.query('wiki', "select user_name from user_groups left join user on user_id = ug_user where ug_group = 'bot';", None):
        blacklist.append(result[0].decode('utf-8'))
    print('With bots, there are ' + str(len(blacklist)) + ' usernames on the blacklist.')

    # Loading the Project Index
    projectindex = wptools.query('index', 'select pi_page, pi_project from projectindex;', None)

    # List of projects we are working on
    # Methodology: List from Project Index + List from Formal Definition, minus duplicates
    # This will cover all of our bases.
    projects = []
    articlecounter = {}
    for pair in projectindex:
        if pair[1] not in projects:
            projects.append(pair[1])
            articlecounter[pair[1]] = 1  # Establishing counter in the article counter
        else:
            articlecounter[pair[1]] += 1
    
    formaldefinition = wptools.query('wiki', 'select distinct page.page_title from page join categorylinks on page.page_id = categorylinks.cl_from left join redirect on page.page_id = redirect.rd_from where page_namespace = 4 and page_title not like "%/%" and rd_title is null and (cl_to in (select page.page_title from page where page_namespace = 14 and page_title like "%\_WikiProjects" and page_title not like "%\_for\_WikiProjects" and page_title not like "%\_of\_WikiProjects") or page_title like "WikiProject\_%");', None)  # http://quarry.wmflabs.org/query/3509
    for row in formaldefinition:
        row = 'Wikipedia:' + row[0].decode('utf-8')  # Making output consistent with formatting used in projects list
        if row not in projects:
            projects.append(row)
    
    projects.sort()
    print('There are ' + str(len(projects)) + ' total WikiProjects and task forces.')

    # Alright! Let's run some reports!
    for project in projects:
        if project not in articlecounter:
            articlecounter[project] = None  # Filling in article counts for projects not in Project Index

        # Profile Page: List of active project participants (less blacklist)
        profilepage[project] = "{{WikiProject description page | project = {0} | number_of_article = {1}".format(project[10:].replace('_', ' '), articlecounter[project])

        # Directory Entry: Count of active project participants

        # Profile Page: List of act subject area editors (less blacklist)
        # Directory Entry: Count of active editors this past month

        # Save Profile Page
        # Construct Directory Entry
        # Assign directory entry to relevant directory pages ("All entries" and relevant subdirectory pages)

if __name__ == "__main__":
    main()