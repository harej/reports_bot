# -*- coding: utf-8 -*-
"""
Updates the WikiProject Directory
Copyright (C) 2015 Betacommand, James Hare
Licensed under MIT License: http://mitlicense.org
"""


import re
import time
import pywikibot
import json
from collections import Counter
from project_index import WikiProjectTools


def main():
    # Initializing...
    bot = pywikibot.Site('en', 'wikipedia')
    wptools = WikiProjectTools()
    config = json.loads(wptools.query('index', 'select json from config;', None)[0][0])
    rootpage = 'User:Reports bot/Directory/'
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
    articles = {}
    for pair in projectindex:
        pair = list(pair)  # For manipulation
        pair[0] = re.sub(r'(Draft_)?[Tt]alk:', '', pair[0])  # Normalizing by getting rid of namespace
        pair[1] = pair[1][10:]  # Normalizing by getting rid of "Wikipedia:"
        if pair[1] not in projects:
            projects.append(pair[1])
            articles[pair[1]] = [pair[0]]
        else:
            articles[pair[1]].append(pair[0])
    
    formaldefinition = wptools.query('wiki', 'select distinct page.page_title from page join categorylinks on page.page_id = categorylinks.cl_from left join redirect on page.page_id = redirect.rd_from where page_namespace = 4 and page_title not like "%/%" and rd_title is null and (cl_to in (select page.page_title from page where page_namespace = 14 and page_title like "%\_WikiProjects" and page_title not like "%\_for\_WikiProjects" and page_title not like "%\_of\_WikiProjects") or page_title like "WikiProject\_%");', None)  # http://quarry.wmflabs.org/query/3509
    for row in formaldefinition:
        row = row[0].decode('utf-8')
        if row not in projects:
            projects.append(row)
    projects.sort()
    projects = projects[:150] # DEBUG MODE
    print('There are ' + str(len(projects)) + ' total WikiProjects and task forces.')

    directories = {'All': ''}  # In the future, there will be other directories in addition to the exhaustive one.

    # Alright! Let's run some reports!
    for project in projects:
        print("Working on: " + project)

        # Seeding directory row and profile page
        if project not in articles:
            articles[project] = []
        project_normalized = project.replace('_', ' ')

        # List of active project participants (less blacklist)
        wp_editors = []
        start_date = time.strftime('%Y%m%d000000',time.gmtime(time.time()-(60*60*24*90)))  # 90 days
        end_date = time.strftime('%Y%m%d000000',time.gmtime(time.time()))  # Today
        query = "select rev_user_text from page left join revision on page_id = rev_page where (page_namespace = 4 OR page_namespace = 5) and (page_title like \"{0}/%%\" OR page_title = \"{0}\") and rev_timestamp > {1} and rev_timestamp < {2} group by rev_user_text HAVING count(*) > 1;".format(project, start_date, end_date)
        for result in wptools.query('wiki', query, None):
            if result[0] is not None:
                user = result[0].decode('utf-8')
                if user not in blacklist:
                    wp_editors.append(user)
        wp_editors.sort()

        # List of active subject area editors (less blacklist)
        start_date = time.strftime('%Y%m%d000000',time.gmtime(time.time()-(60*60*24*30)))  # 30 days
        end_date = time.strftime('%Y%m%d000000',time.gmtime(time.time()))  # Today

        if len(articles[project]) > 0:
            subject_editors = []
            packages = []
            for i in range(0, len(articles[project]), 10000):
                packages.append(articles[project][i:i+10000])
    
            counter = 0
            for package in packages:
                counter += 1
                print('Executing batch query no. ' + str(counter))
                query_builder = 'select rev_user_text from page left join revision on page_id = rev_page where page_namespace in (0, 1, 118, 119) and page_title in {0} and rev_timestamp > {1} and rev_timestamp < {2} order by rev_user_text;'.format(tuple(package), start_date, end_date)
                for result in wptools.query('wiki', query_builder, None):
                    if result[0] is not None:
                        subject_editors.append(result[0].decode('utf-8'))

            subject_editors = dict(Counter(subject_editors))  # Convert the list to a dictionary with username as key and edit count as value
            subject_editors_filtered = []
            for user in subject_editors.keys():
                if user not in blacklist:
                    if subject_editors[user] > 4:
                        subject_editors_filtered.append(user)
            subject_editors = subject_editors_filtered   # And now assigned back.
            subject_editors.sort()

        else:
            subject_editors = []

        # Generate and Save Profile Page
        wp_editors_formatted = ""
        subject_editors_formatted = ""
        if len(wp_editors) > 0:
            for editor in wp_editors:
                wp_editors_formatted += "\n* {{{{user|{0}}}}}".format(editor)
        else:
                wp_editors_formatted = "\n* N/A"
        if len(subject_editors) > 0:
            for editor in subject_editors:
                subject_editors_formatted += "\n* {{{{user|{0}}}}}".format(editor)
        else:
                subject_editors_formatted = "\n* N/A"
        
        profilepage = "{{{{WikiProject description page | project = {0} | list_of_active_wikiproject_participants = {1} | list_of_active_subject_area_editors = {2}}}}}".format(project_normalized, wp_editors_formatted, subject_editors_formatted)
        page = pywikibot.Page(bot, rootpage + 'Description/' + project_normalized)
        if profilepage != page.text:  # Checking to see if a change was made to cut down on API queries
            page.text = profilepage
            page.save('Updating', minor=False, async=True)

        # Construct directory entry
        directoryrow = "{{{{WikiProject directory entry | project = {0} | number_of_articles = {1} | wp_editors = {2} | scope_editors = {3}}}}}\n".format(project_normalized, len(articles[project]), len(wp_editors), len(subject_editors))

        # Assign directory entry to relevant directory pages ("All entries" and relevant subdirectory pages)
        directories['All'] += directoryrow

    # Generate directories and save!
    for directory in directories.keys():
        contents = "{{WikiProject directory top}}\n" + directories[directory] + "|}"
        page = pywikibot.Page(bot, rootpage + directory)
        if contents != page.text:  # Checking to see if a change was made to cut down on API queries
            page.text = contents
            page.save('Updating', minor=False, async=True)


if __name__ == "__main__":
    main()