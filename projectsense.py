# -*- coding: utf-8 -*-
"""
ProjectSense -- does set analysis between WikiProjects
Copyright (C) 2015 James Hare
Licensed under MIT License: http://mitlicense.org
"""

import sys
#import json
#import mw_lego # https://github.com/legoktm/supersimplemediawiki
#import mw # the one by Aaron Halfaker
import pymysql
import re
import operator
#from pprint import pprint as print # legoktm magic

def dbquery(sqlquery):
    """Constructs a MySQL query to the Tool Labs database replica."""
    conn = pymysql.connect(host='enwiki.labsdb', port=3306, db='enwiki_p', read_default_file='~/.my.cnf', charset='utf8')
    cur = conn.cursor()
    cur.execute(sqlquery)
    data = []
    for row in cur:
        data.append(row)
    return data
    
def masterlist():
    """
    Prepares the master list of WikiProject quality assessment categories.
    Returns a dictionary of lists, with the key being the page_title of the WikiProject (or task force)
    and the value being a list of categories.
    """
    
    query = dbquery('select page_title from page where page_namespace = 14 and (page_title like "%-Class_%_articles" or page_title like "Unassessed_%_articles" or page_title like "WikiProject_%_articles") and page_title not like "%-importance_%" and page_title not like "Wikipedia_%" and page_title not like "Template-%" and page_title not like "Redirect-%" and page_title not like "Project-%" and page_title not like "Portal-%" and page_title not like "File-%" and page_title not like "FM-%" and page_title not like "Category-%" and page_title not like "Cat-%" and page_title not like "Book-%" and page_title not like "NA-%" and page_title not like "%_Operation_Majestic_Titan_%" and page_title not like "%_Version_%" and page_title not like "All_Wikipedia_%" and page_title not like "%_Wikipedia-Books_%" and page_title not like "Assessed-%" and page_title not like "%-Priority_%" and page_title not like "Unassessed_field_%" and page_title not like "Unassessed_importance_%" and page_title not like "Unassessed-Class_articles" and page_title not like "%_Article_quality_research_articles" and page_title not like "WikiProject_lists_of_encyclopedic_articles";')
    categories = []
    for row in query:
        categories.append(row[0].decode('utf-8'))
    
    # Record in a dictionary of lists? wikiprojects = {'Military history': ['Category:A', 'Category:B']}
    buckets = {}
    
    for category in categories:
        projectname = category
        projectname = re.sub('WikiProject_', '', projectname) # Some categories include "WikiProject" in the category name.
        projectname = re.sub('-related', '', projectname) # e.g. "Museum-related" -> "Museum"
        projectname = re.sub('_quality', '', projectname) # e.g. "Unassessed_quality" -> "Unassessed"
        projectname = re.sub('_task_forces_by', '', projectname)
        projectname = re.sub('_task_force', '', projectname)
        projectname = re.sub('_taskforce', '', projectname)
        projectname = re.sub('_work_group', '', projectname)
        projectname = re.sub('_workgroup', '', projectname)
        projectname = re.sub('_subproject_selected_articles', '', projectname)
        projectname = re.sub('_automatically_assessed', '', projectname)
        projectname = re.sub(r'_articles$', '', projectname)
        projectname = re.sub(r'_newsletter$', '', projectname)
        projectname = re.sub(r'^((.*)-Class|Unassessed)_', '', projectname)
        projectname = projectname[0].upper() + projectname[1:] # Capitalize the first letter
        try:
            buckets[projectname].append(category)
        except KeyError:
            buckets[projectname] = []
            buckets[projectname].append(category)
        
    # For each key in buckets, try to match it to a real WikiProject or task force name
    # Checks against the redirect table so that it can follow redirects

    pagetitles = {}
    namespaces = {2: 'User:', 3: 'User_talk:', 4: 'Wikipedia:', 5: 'Wikipedia_talk:', 100: 'Portal:', 101: 'Portal_talk:'}
    # Heavens help me if WikiProjects end up in namespaces other than those.
    
    for key in buckets.keys():
        project_area = key
        query = dbquery('select page.page_title,redirect.rd_namespace,redirect.rd_title from page left join redirect on redirect.rd_from = page.page_id where page_title = "WikiProject_' + key + '" and page_namespace = 4;')
        if len(query) == 0:
            query = dbquery('select page.page_title,redirect.rd_namespace,redirect.rd_title from page left join redirect on redirect.rd_from = page.page_id where page_title = "WikiProject_' + key + 's" and page_namespace = 4;')
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
    output = {}
        
    for key in buckets.keys():
        for category in buckets[key]:
            try:
                output[pagetitles[key]].append(category)
            except KeyError:
                output[pagetitles[key]] = []
                output[pagetitles[key]].append(category)
                
    return output
   
def projectscope(project,categories):
    """
    Returns a list of articles in the scope of a WikiProject
    Requires the string 'project' and the list 'categories'
    """
    
    query_builder = 'select distinct page.page_title,page.page_namespace from categorylinks inner join page on categorylinks.cl_from=page.page_id where (page_namespace = 1 or page_namespace = 119) and ('
    for category in categories:
        query_builder += 'cl_to = "' + category + '" or '
    query_builder = re.sub(r' or $', ');', query_builder) # Wrap up query
    
    query = dbquery(query_builder)
    namespaces = {1: "Talk:", 119: "Draft_talk:"}
    output = []
    
    for row in query:
        page_title = row[0].decode('utf-8')
        page_namespace = namespaces[row[1]]
        output.append(page_namespace + page_title)
    
    return output
 
def main():
    # Prepare list of WikiProjects and their categories
    print('Preparing master list of WikiProjects...')
    wikiprojects = masterlist()
    
    # Get list of pages for each WikiProject
    print('Getting list of pages for each WikiProject...')
    pages = {}
    for wikiproject in wikiprojects.keys():
        pages[wikiproject] = projectscope(wikiproject, wikiprojects[wikiproject])
    
    # Compare!
    intersect_counts = {}
    counter = 0
    for wikiproject_x in pages.keys(): # lol WikiProject X
        counter += 1
        print(str(counter) + '. Working on: ' + wikiproject_x)
        intersect_counts[wikiproject_x] = {}
        for wikiproject_y in pages.keys():
            if wikiproject_x == wikiproject_y:
                continue; # Don't compare a project to itself
                
            regex = re.compile('/.*')
            test1 = re.sub(regex, '', wikiproject_x)
            test2 = re.sub(regex, '', wikiproject_y)
            if test1 == test2:
                continue;  # Filters out comparisons where one is a subpage of another
            
            s = set(pages[wikiproject_x])
            intersect_counts[wikiproject_x][wikiproject_y] = len([n for n in pages[wikiproject_y] if n in s])
    
    for project in intersect_counts.keys():
        ordered = sorted(intersect_counts[project].items(), key=operator.itemgetter(1), reverse=True) # Sorts from highest to lowest 
        print('\nSimilar to: ' + project)
        for x in range(0, 10):
            if ordered[x][1] > 0:
                print(ordered[x][0] + " sharing " + str(ordered[x][1]) + " articles")
        
if __name__ == "__main__":
    main()
