# -*- coding: utf-8 -*-
"""
Audits WikiProjects for inconsistencies between their project pages and their categories
Copyright (C) 2015 James Hare
Licensed under MIT License: http://mitlicense.org
"""

import pywikibot

from project_index import WikiProjectTools


class ProjectCategoryAudit:
    def go(self):
        wptools = WikiProjectTools()

        # Get list of WikiProjects that also have a self-named category

        output = 'This report highlights discrepancies in WikiProject categorization between WikiProjects and their self-named categories.\n\n'
        query = 'select page_title from page left join redirect on page.page_id = redirect.rd_from where page_title like "WikiProject\_%" and page_namespace = 4 and page_title in (select page_title from page where page_title like "WikiProject\_%" and page_namespace = 14) and rd_title is null;'

        for row in wptools.query('wiki', query, None):
            project = row[0].decode('utf-8')

            cl_projectspace = []  # read as "category links, Wikipedia namespace"
            cl_categoryspace = []  # read as "category links, Category namespace"

            for match in wptools.query('wiki', 'select cl_to from categorylinks join page on categorylinks.cl_from=page.page_id where page_namespace = 4 and page_title = "{0}" and cl_to like "%\_WikiProjects" and cl_to not like "Active\_%" and cl_to not like "Semi-active\_%" and cl_to not like "Inactive\_%" and cl_to not like "Defunct\_%";'.format(project), None):
                cl_projectspace.append(match[0].decode('utf-8').replace('_', ' '))

            for match in wptools.query('wiki', 'select cl_to from categorylinks join page on categorylinks.cl_from=page.page_id where page_namespace = 14 and page_title = "{0}" and cl_to like "%\_WikiProjects" and cl_to not like "Active\_%" and cl_to not like "Semi-active\_%" and cl_to not like "Inactive\_%" and cl_to not like "Defunct\_%";'.format(project), None):
                cl_categoryspace.append(match[0].decode('utf-8').replace('_', ' '))

            cl_projectspace.sort()
            cl_categoryspace.sort()

            if cl_projectspace == cl_categoryspace:
                continue  # Don't bother generating a report if both category lists match perfectly

            both = list(set(cl_projectspace).intersection(cl_categoryspace))

            project = project.replace('_', ' ')

            output += "* '''{0}'''\n".format(project)
            output += "** [[Wikipedia:{0}]]: ".format(project)
            for entry in cl_projectspace:
                if entry in both:
                    output += "<span style='color: #999'>{0}</span> – ".format(entry)
                else:
                    output += "<span style='color: #FF0000'>{0}</span> – ".format(entry)

            output = output[:-2] + "\n"  # Truncate trailing endash and add line break

            output += "** [[:Category:{0}]]: ".format(project)
            for entry in cl_categoryspace:
                if entry in both:
                    output += "<span style='color: #999'>{0}</span> –".format(entry)
                else:
                    output += "<span style='color: #FF0000'>{0}</span> –".format(entry)

            output = output[:-2] + "\n"  # Truncate trailing endash and add line break

        return output


if __name__ == "__main__":
    audit = ProjectCategoryAudit()
    report = audit.go()
    bot = pywikibot.Site('en', 'wikipedia')
    page = pywikibot.Page(bot, 'User:Reports bot/WikiProject category audit')
    page.text = report
    page.save('Updating report', minor=False, quiet=True)
