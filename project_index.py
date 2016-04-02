# -*- coding: utf-8 -*-
"""
Project Index -- prepares an index of WikiProjects and their in-scope pages for use by scripts
Copyright (C) 2015 James Hare
Licensed under MIT License: http://mitlicense.org
"""


import pymysql
import re


class WikiProjectTools:
    def query(self, switch, sqlquery, values):
        """Carries out MySQL queries"""
        if switch == 'wiki':  # Queries to the English Wikipedia database
            host, db = 'enwiki.labsdb', 'enwiki_p'
        elif switch == 'index':  # Queries to our article-WikiProject pair index
            host, db = 'tools-db', 's52475__wpx_p'
        else:
            raise ValueError

        conn = pymysql.connect(host=host, port=3306, db=db, read_default_file='~/.my.cnf', charset='utf8')
        cur = conn.cursor()
        cur.execute(sqlquery, values)
        data = []
        for row in cur:
            data.append(row)
        conn.commit()
        return data

    def masterlist(self):
        """
        Prepares the master list of WikiProject quality assessment categories.
        Returns a dictionary of lists, with the key being the page_title of the WikiProject (or task force)
        and the value being a list of categories.
        """

        q = ('select page_title from page where page_namespace = 14 and '
             '(page_title like "%-Class\_%\_articles" '
             'or page_title like "Unassessed\_%\_articles" '
             'or page_title like "WikiProject\_%\_articles") '
             'and page_title not like "%-importance\_%" '
             'and page_title not like "Wikipedia\_%" '
             'and page_title not like "Template-%" '
             'and page_title not like "Redirect-%" '
             'and page_title not like "Project-%" '
             'and page_title not like "Portal-%" '
             'and page_title not like "File-%" '
             'and page_title not like "FM-%" '
             'and page_title not like "Category-%" '
             'and page_title not like "Cat-%" '
             'and page_title not like "Book-%" '
             'and page_title not like "NA-%" '
             'and page_title not like "%\_Operation\_Majestic\_Titan_%" '
             'and page_title not like "%\_Version_%" '
             'and page_title not like "All\_Wikipedia\_%" '
             'and page_title not like "%\_Wikipedia-Books\_%" '
             'and page_title not like "Assessed-%" '
             'and page_title not like "%-Priority\_%" '
             'and page_title not like "Unassessed\_field\_%" '
             'and page_title not like "Unassessed\_importance\_%" '
             'and page_title not like "Unassessed-Class\_articles" '
             'and page_title not like "%\_Article\_quality\_research\_articles" '
             'and page_title not like "WikiProject\_lists\_of\_encyclopedic\_articles";')
        query = self.query('wiki', q, None)
        categories = []
        for row in query:
            categories.append(row[0].decode('utf-8'))

        # Record in a dictionary of lists? wikiprojects = {'Military history': ['Category:A', 'Category:B']}
        buckets = {}

        for category in categories:
            projectname = category
            projectname = projectname.replace('WikiProject_', '')  # Some categories include "WikiProject" in the category name.
            projectname = projectname.replace('-related', '')  # e.g. "Museum-related" -> "Museum"
            projectname = projectname.replace('_quality', '')  # e.g. "Unassessed_quality" -> "Unassessed"
            projectname = projectname.replace('_subproject_selected_articles', '')
            projectname = projectname.replace('_automatically_assessed', '')
            projectname = re.sub(r'_task_?forces?(_by)?', '', projectname)
            projectname = re.sub(r'_work_?group', '', projectname)
            projectname = re.sub(r'_articles$', '', projectname)
            projectname = re.sub(r'_newsletter$', '', projectname)
            projectname = re.sub(r'^((.*)-Class|Unassessed)_', '', projectname)
            projectname = projectname[0].upper() + projectname[1:]  # Capitalize the first letter
            # TODO: Use collections.defaultdict
            try:
                buckets[projectname].append(category)
            except KeyError:
                buckets[projectname] = [category]

        # For each key in buckets, try to match it to a real WikiProject or task force name
        # Checks against the redirect table so that it can follow redirects

        pagetitles = {}
        namespaces = {2: 'User:', 3: 'User_talk:', 4: 'Wikipedia:', 5: 'Wikipedia_talk:', 100: 'Portal:', 101: 'Portal_talk:'}
        # Heavens help me if WikiProjects end up in namespaces other than those.

        output = {}
        for key in buckets.keys():
            query = self.query('wiki', 'select page.page_title,redirect.rd_namespace,redirect.rd_title from page left join redirect on redirect.rd_from = page.page_id where page_title = %s and page_namespace = 4;', ('WikiProject_'+key,))
            if len(query) == 0:
                query = self.query('wiki', 'select page.page_title,redirect.rd_namespace,redirect.rd_title from page left join redirect on redirect.rd_from = page.page_id where page_title = %s and page_namespace = 4;', ('WikiProject_'+key+'s',))  # Checks for plural
                if len(query) == 0:
                    print('Warning: No project page found for key: ' + key)
                    continue

            page_title = query[0][0]
            rd_namespace = query[0][1]
            rd_title = query[0][2]

            if rd_title is not None:
                pagetitles[key] = namespaces[rd_namespace] + rd_title.decode('utf-8')
            elif rd_title is None and page_title is not None:
                pagetitles[key] = namespaces[4] + page_title.decode('utf-8')

            # At this point, each key of buckets should be tied to an actual page name
            for category in buckets[key]:
                # TODO: Use a collections.defaultdict here
                try:
                    output[pagetitles[key]].append(category)
                except KeyError:
                    output[pagetitles[key]] = []
                    output[pagetitles[key]].append(category)

        return output

    def projectscope(self, project, categories):
        """
        Returns a list of articles in the scope of a WikiProject
        Requires the string 'project' and the list 'categories'
        """

        query_builder = 'select distinct page.page_title,page.page_namespace from categorylinks join page on categorylinks.cl_from=page.page_id where page_namespace in (1, 119) and cl_to in ('
        mastertuple = ()
        for category in categories:
            query_builder += '%s, '
            mastertuple += (category,)
        query_builder = query_builder[:-2]  # Truncate extraneous "or"
        query_builder += ');'  # Wrap up query

        query = self.query('wiki', query_builder, mastertuple)
        namespaces = {1: "Talk:", 119: "Draft_talk:"}
        output = []

        for row in query:
            page_title = row[0].decode('utf-8')
            page_namespace = namespaces[row[1]]
            output.append(page_namespace + page_title)

        output = list(set(output))  # De-duplication
        return output

    def main(self):
        # Prepare list of WikiProjects and their categories
        print('Preparing master list of WikiProjects...')
        wikiprojects = self.masterlist()

        # Get list of pages for each WikiProject
        print('Getting list of pages for each WikiProject...')
        pages = {}
        for wikiproject in wikiprojects.keys():
            pages[wikiproject] = self.projectscope(wikiproject, wikiprojects[wikiproject])

        dbinput = []
        for wikiproject in pages.keys():
            for page in pages[wikiproject]:
                dbinput.append((page, wikiproject))

        # Saves it to the database
        print('Saving to the database...')
        self.query('index', 'create table projectindex_draft (pi_id int(11) NOT NULL auto_increment, pi_page VARCHAR(255) character set utf8 collate utf8_unicode_ci, pi_project VARCHAR(255) character set utf8 collate utf8_unicode_ci, primary key (pi_id)) engine=innodb character set=utf8;', None)

        packages = []
        for i in range(0, len(dbinput), 10000):
            packages.append(dbinput[i:i+10000])

        counter = 0
        for package in packages:
            query_builder = 'insert into projectindex_draft (pi_page, pi_project) values '  # Seeding really long query
            mastertuple = ()
            for item in package:
                query_builder += '(%s, %s), '
                mastertuple += item
            query_builder = query_builder[:-2]  # Truncating the terminal comma and space
            query_builder += ';'
            counter += 1
            print('Executing batch query no. ' + str(counter))
            self.query('index', query_builder, mastertuple)

        self.query('index', 'drop table if exists projectindex', None)
        self.query('index', 'rename table projectindex_draft to projectindex', None)  # Moving draft table over to live table
        self.query('index', 'create index projectindex_pageindex on projectindex (pi_page)', None)  # Creating index

if __name__ == "__main__":
    wptools = WikiProjectTools()
    wptools.main()