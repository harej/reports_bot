# -*- coding: utf-8 -*-
"""
Predicts article quality and priority with respect to a WikiProject.
Copyright (C) 2015 James Hare
Licensed under MIT License: http://mitlicense.org
"""


import datetime
import gzip
import html
import operator
import os
import pywikibot
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
        query_builder = 'select pl_title, count(*) from pagelinks where pl_namespace = 0 and pl_title in {0} group by pl_title;'.format(tuple(package))
    else:
        query_builder = 'select pl_title, count(*) from pagelinks where pl_namespace = 0 and pl_title in {0} group by pl_title;'.format(package[0])

    output = []
    for row in wptools.query('wiki', query_builder, None):
        output.append((row[0].decode('utf-8'), log(row[1] + 1)))

    return output

class QualityPredictor:
    def qualitypredictor(self, pagetitle):
        print("Argh! Not ready yet!")
        # chat it up with ORES

class PriorityPredictor:
    def __init__(self):
        print("Initializing the Priority Predictor")
        self.wptools = WikiProjectTools()
        self.dump = getviewdump(self.wptools, 'en', days=30)

    def loadproject(self, wikiproject, unknownpriority):
        self.project = wikiproject
        self.rank = []  # Sorted list of tuples; allows for ranking
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

        # Sorting...
        pageviews = sorted(pageviews, key=operator.itemgetter(1), reverse=True)
        linkcount = sorted(linkcount, key=operator.itemgetter(1), reverse=True)

        # Computing relative pageviews and linkcount
        # "Relative" means "as a ratio to the highest rank".
        # The most viewed article has a relative pageview score of 1.00. Goes lower from there.

        print("Computing relative pageviews and linkcount...")
        pageviews_relative = {}
        linkcount_relative = {}

        self.mostviews = pageviews[0][1]
        self.mostlinks = linkcount[0][1]

        for pair in pageviews:
            article = pair[0]
            count = pair[1]
            pageviews_relative[article] = count / self.mostviews

        for pair in linkcount:
            article = pair[0]
            count = pair[1]
            linkcount_relative[article] = count / self.mostlinks

        for article in self.articles:
            weightedscore = (pageviews_relative[article] * 0.75) + (linkcount_relative[article] * 0.25)
            self.rank.append((article, weightedscore))
            self.score[article] = weightedscore

        self.rank = sorted(self.rank, key=operator.itemgetter(1), reverse=True)

        # Calculating minimum scores
        # The idea is that there is a minimum score for something to be top, high, or mid-priority
        # The script is fed the category name for the unknown-importance/unknown-priority category
        # Based on this, derive category names for top/high/mid/low, add all the counts together...
        # ...then calculate ratio for top/high/mid as a ratio of the total...
        # ...multiply that ratio by the count of self.rank, convert to an integer
        # ...and then threshold = self.rank[that integer][1]
        # This gives us a general sense of what proportion of articles should be considered top/high/mid/low
        # Far from perfect but it's a start.

        print("Calculating priority thresholds...")
        priorities = ['Top-', 'High-', 'Mid-', 'Low-']
        prioritycount = {}

        q = 'select count(*) from categorylinks where cl_type = "page" and cl_to = "{0}";'
        for priority in priorities:
            prioritycategory = unknownpriority.replace("Unknown-", priority)
            prioritycount[priority] = self.wptools.query('wiki', q.format(prioritycategory), None)[0][0]

        total_assessed = sum([x for x in prioritycount.values()])

        top_index = int((prioritycount['Top-'] / total_assessed) * len(self.articles) - 1)
        high_index = top_index + int((prioritycount['High-'] / total_assessed) * len(self.articles) -1)
        mid_index = high_index + int((prioritycount['Mid-'] / total_assessed) * len(self.articles) -1)

        self.threshold_top = self.score[top_index][1]
        self.threshold_high = self.score[high_index][1]
        self.threshold_mid = self.score[mid_index][1]

    def predictpage(self, pagetitle):
        # Pull pagescore if already defined
        # Otherwise, compute it "de novo"
        if pagetitle in self.articles:
            pagescore = self.score[pagetitle]
        else:
            pageviews = log(getpageviews(self.dump, pagetitle) + 1) / self.mostviews
            linkcount = getlinkcount(self.wptools, [pagetitle])[0][1] / self.mostlinks
            pagescore = (pageviews * 0.75) + (linkcount * 0.25)

        if pagescore >= self.threshold_top:
            return "Top"

        if pagescore >= self.threshold_high:
            return "High"

        if pagescore >= self.threshold_mid:
            return "Mid"

        # If none of these...
        return "Low"