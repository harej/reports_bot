# -*- coding: utf-8 -*-
"""
Predicts article quality and priority with respect to a WikiProject.
Copyright (C) 2015 James Hare
Licensed under MIT License: http://mitlicense.org
"""


import datetime
import gzip
import html
import json
import operator
import os
import numpy as np
from sklearn.multiclass import OneVsRestClassifier
from sklearn.svm import LinearSVC
from math import log  # https://www.youtube.com/watch?v=RTrAVpK9blw
from project_index import WikiProjectTools


def getviewdump(wptools, proj, days=30):
    '''
    Loads the page view dump for the past complete 30 days
    Takes string input (project name/abbreviation as identified in the dump)
    Returns a dict: title => pageviews
    '''

    # Create list of lists; each sub-list is a directory path
    # e.g. ['2015', '2015-06', '20150610-000000']

    filepaths = []
    for i in range(1, days+1):  # day -1 through day -31 (i.e., thirty days in the past, starting with yesterday)
        time = datetime.datetime.now() + datetime.timedelta(-i)
        for j in range(24):  # for each hour
            hourminutesecond = '-' + str(j).zfill(2) + '0000'
            filepaths.append([time.strftime('%Y'), time.strftime('%Y-%m'), time.strftime('%Y%m%d') + hourminutesecond])

    # Generate list of valid article titles (specifically for English Wikipedia) to filter out inane amounts of garbage
    if proj == 'en':
        print("Generating enwiki valid titles list...")
        validtitles = set()
        for row in wptools.query('wiki', 'select page_title from page where page_namespace = 0 and page_is_redirect = 0;', None):
            validtitles.add(row[0].decode('utf-8'))
    else:
        validtitles = None

    # Read through each file, and if it matches with the project, append to output

    counter = 0
    output = {}
    for file in filepaths:
        counter += 1
        print("Processing dump file " + str(counter) + "/" + str(len(filepaths)), end="\r")
        filename = '/public/dumps/pagecounts-raw/{0}/{1}/pagecounts-{2}.gz'.format(file[0], file[1], file[2])

        if os.path.isfile(filename) == False:
            continue

        with gzip.open(filename, mode='rt', encoding='utf-8') as f:
            for line in f:
                entry = line.split(' ')  # It's a space-delimited file, or something
                if entry[0] == proj:
                    entry[1] = html.unescape(entry[1]).replace(' ', '_')
                    if proj == 'en' and entry[1] not in validtitles:  # English Wikipedia specific check
                        continue
                    else:
                        if entry[1] in output:
                            output[entry[1]] += int(entry[2])  # Append to existing record
                        else:
                            output[entry[1]] = int(entry[2])  # Create new record

    print("\nProcessed stats for " + str(len(output)) + " articles.")
    return output


def getpageviews(dump, article):
    '''
    Queries *dump* for the number of page views in the last 30 days
    Takes dict *dump*, string *article* as input, returns view count.
    Does NOT take the logarithm of the view count.
    '''

    if article in dump:
        return dump[article]
    else:
        return 0

def getlinkcount(wptools, package):
    '''
    Gets a list of inbound links for a list of articles
    Takes list *package* as input, returns list of tuples (article, log of linkcount)
    Input MUST be a list. If there is just one article, enter it as such: [article]
    '''

    if len(package) > 1:
        q = 'select pl_title, count(*) from pagelinks where pl_namespace = 0 and pl_title in {0} group by pl_title;'.format(tuple(package))
    else:
        q = 'select pl_title, count(*) from pagelinks where pl_namespace = 0 and pl_title = "{0}" group by pl_title;'.format(package[0])

    output = []
    for row in wptools.query('wiki', q, None):
        output.append((row[0].decode('utf-8'), log(row[1] + 1)))

    if len(output) == 0:
        output = [('', 0)]  # Return a consistent result even if there is nothing

    return output

def getinternalclout(wptools, destination, articlebatch):
    '''
    Gets a list of inbound links from *articlebatch* to *destination*
    Takes lists *articlebatch* and *destination* as input, returns list of tuples (article, log of linkcount)
    Input MUST be a list. If there is just one article, enter it as such: [article]
    '''

    destination_packages = [destination[i:i+1000] for i in range(0, len(destination), 1000)]
    articlebatch_packages = [articlebatch[i:i+1000] for i in range(0, len(articlebatch), 1000)]

    stats = {}  # destination --> count of links from articlebatch

    for destination_package in destination_packages:
        for articlebatch_package in articlebatch_packages:
            if len(destination_package) > 1:
                q = "select pl_title, count(*) from pagelinks join page on pl_from = page_id and pl_from_namespace = page_namespace where pl_namespace = 0 and pl_title in {0} and page_title in {1} group by pl_title;".format(tuple(destination_package), tuple(articlebatch_package))
            else:
                q = 'select pl_title, count(*) from pagelinks join page on pl_from = page_id and pl_from_namespace = page_namespace where pl_namespace = 0 and pl_title = "{0}" and page_title in {1} group by pl_title;'.format(destination_package[0], tuple(articlebatch_package))
        
            for row in wptools.query('wiki', q, None):
                if row[0].decode('utf-8') in stats:
                    stats[row[0].decode('utf-8')] += row[1]  # append to existing record
                else:
                    stats[row[0].decode('utf-8')] = row[1]  # create new record

    output = [(x, log(stats[x] + 1)) for x in stats.keys()]  # I love list comprehensions

    if len(output) == 0:
        output = [('', 0)]  # Return a consistent result even if there is nothing

    return output


def getsopv(wptools, dump, articles):
    '''
    Get "second-order page views"
    SOPV refers to the page views not of the article but of pages linking *to* the article
    Takes list *articles* title as input; returns list of tuples: (page title, log of SOPVs)
    Input MUST be a list. If there is just one article, enter it as such: [article]
    '''

    stats = {}

    packages = [articles[i:i+10000] for i in range(0, len(articles), 10000)]
    for package in packages:
        if len(articles) > 1:
            q = "select pl_title, page_title from pagelinks join page on pl_from = page_id and pl_from_namespace = page_namespace where pl_namespace = 0 and pl_from_namespace = 0 and pl_title in {0};".format(tuple(package))
        else:
            q = 'select pl_title, page_title from pagelinks join page on pl_from = page_id and pl_from_namespace = page_namespace where pl_namespace = 0 and pl_from_namespace = 0 and pl_title = "{0}";'.format(package[0])
    
        for row in wptools.query('wiki', q, None):
            to_title = row[0].decode('utf-8')
            from_title = row[1].decode('utf-8')
            if to_title in stats:
                stats[to_title] += getpageviews(dump, from_title)  # append to existing record
            else:
                stats[to_title] = getpageviews(dump, from_title)  # create new record

    for article in articles:
        if article not in stats:
            stats[article] = 0  # womp

    output = [(x, log(stats[x] + 1)) for x in stats.keys()]

    if len(output) == 0:
        output = [('', 0)]  # Return a consistent result even if there is nothing

    return output


class PriorityPredictor:
    def __init__(self, viewdump=None):
        print("Initializing the Priority Predictor")
        self.wptools = WikiProjectTools()

        if viewdump == None:  # If a dumped JSON file of pageviews is not specified
            self.dump = getviewdump(self.wptools, 'en', days=30)
        else:
            with open(viewdump, 'r') as f:
                self.dump = json.load(f)  # Load pageviews from a dumped JSON file


    def loadproject(self, wikiproject, unknownpriority):
        self.projectcat = unknownpriority.replace("Unknown-", "")
        self.project = wikiproject
        self.score = {}  # Unsorted dictionary "article: value"; allows for easily looking up scores later
        # We need all the articles for a WikiProject, since the system works by comparing stats for an article to the others.
        print("Preparing Priority Predictor for: " + self.project)
        self.articles = []   # List of strings (article titles)
        pageviews = []  # List of tuples (article title, log of view count)
        linkcount = []  # List of tuples (article title, log of link count)
        for row in self.wptools.query('index', 'select pi_page from projectindex where pi_project = "Wikipedia:{0}";'.format(self.project), None):
            if row[0].startswith("Talk:"):  # 
                article = row[0][5:] # Stripping out "Talk:"
                self.articles.append(article)
                pageviews.append((article, log(getpageviews(self.dump, article) + 1)))

        # Inbound link count
        # This is batched, thus broken out of the loop
        print("Getting inbound link count...")
        packages = []
        for i in range(0, len(self.articles), 10000):
            packages.append(self.articles[i:i+10000])

        for package in packages:
                toappend = getlinkcount(self.wptools, package)
                for item in toappend:
                    linkcount.append(item)

        # "Internal Clout"
        # This measures, within a group of articles, the number of links to each other
        # Works amazingly well as a metric

        print("Measuring internal clout...")
        internalclout = getinternalclout(self.wptools, self.articles, self.articles)


        # SOPV, Second-Order Page Views
        # Calculates the page views of the articles linking to the article being assessed

        print("Measuring second-order page views...")
        sopv = getsopv(self.wptools, self.dump, self.articles)

        # Sorting...
        pageviews = sorted(pageviews, key=operator.itemgetter(1), reverse=True)
        linkcount = sorted(linkcount, key=operator.itemgetter(1), reverse=True)
        internalclout = sorted(internalclout, key=operator.itemgetter(1), reverse=True)
        sopv = sorted(sopv, key=operator.itemgetter(1), reverse=True)

        # Converting to dictionary to weight factors and add them all together

        print("Prepared weighted scores...")
        pageviews_weighted = {}
        linkcount_weighted = {}
        internalclout_weighted = {}
        sopv_weighted = {}

        # Weights assigned to different factors.
        self.weight_pageviews = 1
        self.weight_linkcount = 1
        self.weight_internalclout = 1
        self.weight_sopv = 1

        for pair in pageviews:
            article = pair[0]
            count = pair[1]
            pageviews_weighted[article] = count * self.weight_pageviews

        for pair in linkcount:
            article = pair[0]
            count = pair[1]
            linkcount_weighted[article] = count * self.weight_linkcount

        for pair in internalclout:
            article = pair[0]
            count = pair[1]
            internalclout_weighted[article] = count * self.weight_internalclout

        for pair in sopv:
            article = pair[0]
            count = pair[1]
            sopv_weighted[article] = count * self.weight_sopv

        for article in self.articles:
            if article in internalclout_weighted and article in pageviews_weighted and article in linkcount_weighted and article in sopv_weighted:
                scorearray = [internalclout_weighted[article], sopv_weighted[article]]
                self.score[article] = scorearray

        # Multiclass classification

        print("Making calculations...")
        self.threshold = {}
        self.scorelist = {}
        q = 'select page_title from categorylinks join page on cl_from = page_id where cl_type = "page" and cl_to = "{0}";'
        for priority in ['Top-', 'High-', 'Mid-', 'Low-']:
            prioritycategory = priority + self.projectcat
            self.scorelist[priority] = [(row[0].decode('utf-8'), self.score[row[0].decode('utf-8')]) for row in self.wptools.query('wiki', q.format(prioritycategory), None) if row[0].decode('utf-8') in self.score]

        X = np.array([(x[1]) for x in self.scorelist['Top-']] + [(x[1]) for x in self.scorelist['High-']] + [(x[1]) for x in self.scorelist['Mid-']] + [(x[1]) for x in self.scorelist['Low-']])

        y = np.array([0 for x in self.scorelist['Top-']] + [1 for x in self.scorelist['High-']] + [2 for x in self.scorelist['Mid-']] + [3 for x in self.scorelist['Low-']])

        model = OneVsRestClassifier(LinearSVC(random_state=0)).fit(X, y)

        print(list(model.predict(X)))
        print(model.score(X, y))