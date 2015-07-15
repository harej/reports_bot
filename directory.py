# -*- coding: utf-8 -*-
"""
Updates the WikiProject Directory
Copyright (C) 2015 James Hare, Betacommand, Merlijn Van Deen
Licensed under MIT License: http://mitlicense.org
"""


import re
import time
import pywikibot
import json
import operator
import mwparserfromhell as mwph
from collections import Counter
from project_index import WikiProjectTools
from category_tree import WikiProjectCategories

class WikiProjectDirectory:
    def listpull(self, wptools, projects, directoryrow, key):
        query = wptools.query('wiki', 'select distinct page.page_title from categorylinks join page on categorylinks.cl_from=page.page_id where page_namespace in (4, 14) and cl_to = "{0}" order by page.page_title'.format(key), None)
        output = ''
        for row in query:
            proj = row[0].decode('utf-8')
            if proj in projects:  # This check is to filter against query results like "WikiProject_Stupid/talkheader" from being considered as projects.
                output += directoryrow[proj]
        if output != "":
            output = "{{WikiProject directory top}}\n" + output + "|}\n\n"

        return output


    def treeiterator(self, wptools, tree, projects, directoryrow, key, counter=2):
        output = ''
        if len(tree) > 0:
            header = "=" * counter  # Python always finds new ways to amaze me.
            for step in tree.keys():
                output += header + step.replace('_', ' ') + header + "\n" + self.listpull(wptools, projects, directoryrow, step) + "\n"
                if len(tree[step]) > 0:
                    output += self.treeiterator(wptools, tree[step], projects, directoryrow, step, counter=counter+1)
        return output


    def main(self, rootpage):
        # Initializing...
        bot = pywikibot.Site('en', 'wikipedia')
        wptools = WikiProjectTools()
        config = json.loads(wptools.query('index', 'select json from config;', None)[0][0])
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

        # List of projects we are working on
        # Methodology: List from Project Index + List from Formal Definition, minus duplicates
        # This will cover all of our bases.
        print("Loading the Project Index...")
        articles = {}
        counter = 0
        while True:  # I am a bad man for doing this
            print("Query for IDs " + str(counter + 1) + " through " + str(counter+ 1000000))
            query = wptools.query('index', 'select pi_page, pi_project from projectindex where pi_id > {0} and pi_id <= {1};'.format(counter, counter+1000000), None)
            if len(query) == 0:
                break
            for pair in query:
                # Normalizing by getting rid of namespace
                page = pair[0]
                page = page.replace('Draft_talk:', '')
                page = page.replace('Talk:', '')
                proj = pair[1][10:]  # Normalizing by getting rid of "Wikipedia:"
                try:
                    articles[proj].append(page)
                except KeyError:
                    articles[proj] = [page]
            counter += 1000000

        projects = [project for project in articles.keys()]

        print("Preparing the Formal Definition index...")
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
        print('There are ' + str(len(projects)) + ' total WikiProjects and task forces.')

        directories = {'All': ''}  # All projects, plus subdirectories to be defined below.
        directoryrow = {}

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
                    if len(package) > 1:
                        query_builder = 'select rev_user_text from page left join revision on page_id = rev_page where page_namespace in (0, 1, 118, 119) and page_title in {0} and rev_timestamp > {1} and rev_timestamp < {2} order by rev_user_text;'.format(tuple(package), start_date, end_date)
                    else:
                        query_builder = 'select rev_user_text from page left join revision on page_id = rev_page where page_namespace in (0, 1, 118, 119) and page_title = "{0}" and rev_timestamp > {1} and rev_timestamp < {2} order by rev_user_text;'.format(package[0], start_date, end_date)

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
                    wp_editors_formatted += "\n* {{{{user|1={0}}}}}".format(editor)
            else:
                    wp_editors_formatted = ""
            if len(subject_editors) > 0:
                for editor in subject_editors:
                    subject_editors_formatted += "\n* {{{{user|1={0}}}}}".format(editor)
            else:
                    subject_editors_formatted = ""
    
            profilepage = "{{{{WikiProject description page | project = {0} | list_of_active_wikiproject_participants = {1} | list_of_active_subject_area_editors = {2}}}}}".format(project_normalized, wp_editors_formatted, subject_editors_formatted)
            page = pywikibot.Page(bot, rootpage + '/Description/' + project_normalized)
            if profilepage != page.text:  # Checking to see if a change was made to cut down on API queries
                page.text = profilepage
                page.save('Updating', minor=False, async=True)

            # Construct directory entry
            directoryrow[project] = "{{{{WikiProject directory entry | project = {0} | number_of_articles = {1} | wp_editors = {2} | scope_editors = {3}}}}}\n".format(project_normalized, len(articles[project]), len(wp_editors), len(subject_editors))

        # Assign directory entry to relevant directory pages ("All entries" and relevant subdirectory pages)
        print("Populating directory pages...")
        for entry in sorted(directoryrow.items(), key=operator.itemgetter(1)):  # Sorting into alphabetical order
            directories['All'] += entry[1]
        directories['All'] = "{{WikiProject directory top}}\n" + directories['All'] + "|}"

        wpcats = WikiProjectCategories()
        tree = wpcats.generate()
        index_primary = sorted([key for key in tree.keys()])
        index_secondary = {}
        indextext = "'''[[{0}/All|All WikiProjects]]'''\n\n".format(rootpage)
        for firstlevel in tree.keys():
            directories[firstlevel] = "={0}=\n".format(firstlevel.replace('_',  ' ' ))
            directories[firstlevel] += self.listpull(wptools, projects, directoryrow, firstlevel)  # For immmedate subcats of WikiProjects_by_area
            directories[firstlevel] += self.treeiterator(wptools, tree[firstlevel], projects, directoryrow, firstlevel)  # For descendants of those immediate subcats.
            index_secondary[firstlevel] = sorted([key for key in tree[firstlevel].keys()])

        # Updating the directory index
        for firstlevel in index_primary:
            firstlevel_normalized = firstlevel.replace('_', ' ')
            indextext += ";[[{0}/{1}|{1}]]".format(rootpage, firstlevel_normalized)
            if len(tree[firstlevel]) > 0:
                indextext += " : "
                for secondlevel in index_secondary[firstlevel]:
                    indextext += "[[{0}/{1}#{2}|{2}]] – ".format(rootpage, firstlevel_normalized, secondlevel.replace('_', ' '))
                indextext = indextext[:-3]  # Truncates trailing dash and is also a cute smiley face
            indextext += "\n\n"
        saveindex = pywikibot.Page(bot, 'Template:WikiProject directory index')
        saveindex.text = indextext
        saveindex.save('Updating', minor=False, async=True)

        # Generate directories and save!
        for directory in directories.keys():
            contents = directories[directory]
            page = pywikibot.Page(bot, rootpage + "/" + directory)
            if contents != page.text:  # Checking to see if a change was made to cut down on API save queries
                oldcontents = page.text
                page.text = contents
                page.save('Updating', minor=False, async=True)
                # Cleanup of obsolete description pages and "Related WikiProjects" pages
                if directory == 'All':
                    oldcontents = mwph.parse(oldcontents)
                    oldcontents = oldcontents.filter_templates()
                    oldprojectlist = []
                    for t in oldcontents:
                        if t.name.strip() == "WikiProject directory entry":
                            oldprojectlist.append(str(t.get('project').value))
                    for oldproject in oldprojectlist:
                        oldproject = oldproject.strip().replace(' ', '_')  # Normalizing
                        if oldproject not in projects:
                            deletethis = pywikibot.Page(bot, rootpage + '/Description/' + oldproject)
                            deletethis.text = "{{db-g6|rationale=A bot has automatically tagged this page as obsolete. This means that the WikiProject described on this page has been deleted or made into a redirect}}\n"
                            deletethis.save('Nominating page for deletion', minor=False, async=True)
                            deletethis = pywikibot.Page(bot, 'Wikipedia:Related WikiProjects/' + oldproject)
                            if deletethis.text != "":
                                deletethis.text = "{{db-g6|rationale=A bot has automatically tagged this page as obsolete. This means that the WikiProject described on this page has been deleted or made into a redirect}}\n"
                                deletethis.save('Nominating page for deletion', minor=False, async=True)


if __name__ == "__main__":
    d = WikiProjectDirectory()
    d.main('Wikipedia:WikiProject Directory')