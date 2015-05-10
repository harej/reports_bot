# -*- coding: utf-8 -*-
"""
Related Projects -- compares WikiProjects according to pages in common
Copyright (C) 2015 James Hare
Licensed under MIT License: http://mitlicense.org
"""

#import mw_lego # https://github.com/legoktm/supersimplemediawiki
import re
import operator
from project_index import WikiProjectTools

 
def main():
    
    print('Pulling from database...')
    wptools = WikiProjectTools()
    query = wptools.indexquery('select pi_page, pi_project from projectindex;', None)
    
    pages = {}
    for row in query:
        pi_page = row[0]
        pi_project = row[1]
        try:
            pages[pi_project].append(pi_page)
        except KeyError:
            pages[pi_project] = []
    
    # Compare!
    intersect_counts = {}
    counter = 0
    regex = re.compile('/.*')
    for wikiproject_x in pages.keys():  # lol WikiProject X
        counter += 1
        print(str(counter) + '. Working on: ' + wikiproject_x)
        intersect_counts[wikiproject_x] = {}
        for wikiproject_y in pages.keys():
            if wikiproject_x == wikiproject_y:
                continue  # Don't compare a project to itself
                
            test1 = re.sub(regex, '', wikiproject_x)
            test2 = re.sub(regex, '', wikiproject_y)
            if test1 == test2:
                continue  # Filters out comparisons where one is a subpage of another
            
            s = set(pages[wikiproject_x])
            intersect_counts[wikiproject_x][wikiproject_y] = len([n for n in pages[wikiproject_y] if n in s])
    
    for project in intersect_counts.keys():
        # Sorts from highest to lowest
        ordered = sorted(intersect_counts[project].items(), key=operator.itemgetter(1), reverse=True)
        print('\nSimilar to: ' + project)
        for x in range(0, 10):
            if ordered[x][1] > 0:
                print(ordered[x][0] + " sharing " + str(ordered[x][1]) + " articles")
        
if __name__ == "__main__":
    main()
