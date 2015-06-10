# -*- coding: utf-8 -*-
"""
Predicts article quality and priority with respect to a WikiProject.
Copyright (C) 2015 James Hare
Licensed under MIT License: http://mitlicense.org
"""


import json
import operator
import pywikibot
import re
import requests
from math import log  # https://www.youtube.com/watch?v=RTrAVpK9blw
from project_index import WikiProjectTools


def getpageviews(article):
    '''
    Queries stats.grok.se for the number of page views in the last 30 days
    Takes string *article* as input, returns view count.
    Does NOT take the logarithm of the view count.
    '''

    grok = requests.get("http://stats.grok.se/json/en/latest30/{0}".format(article))
    result = grok.json()
    counter = 0
    for dailyvalue in result['daily_views'].values():
        counter += dailyvalue

    return counter

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
        output.append((row[0].decode('utf-8'), log(row[1])))

    return output

class QualityPredictor:
    def qualitypredictor(self, pagetitle):
        print("Argh! Not ready yet!")
        # chat it up with ORES

class PriorityPredictor:
    def __init__(self, wikiproject, unknownpriority):
        print("Initializing the Priority Predictor for: " + wikiproject)
        self.wptools = WikiProjectTools()
        self.score = []  # Sorted list of tuples; allows for ranking
        self.score_unranked = {}  # Unsorted dictionary "article: value"; allows for easily looking up scores later

        # We need all the articles for a WikiProject, since the system works by comparing stats for an article to the others.
        print("Getting list of articles in the WikiProject...")
        self.articles = []   # List of strings (article titles)
        pageviews = []  # List of tuples (article title, log of view count)
        linkcount = []  # List of tuples (article title, log of link count)
        for row in self.wptools.query('index', 'select pi_page from projectindex where pi_project = "Wikipedia:{0}";'.format(wikiproject), None):
            if row[0].startswith("Talk:"):  # 
                article = row[0][5:] # Stripping out "Talk:"
                self.articles.append(article)

                # Page view count
                # Unfortunately, there is no way to batch this.
                print("Getting pageviews for: " + article)
                pageviews.append((article, log(getpageviews(article))))

        # Inbound link count
        # This *is* batched, thus broken out of the loop
        print("Getting inbound link count...")
        packages = []
        for i in range(0, len(self.articles), 10000):
            packages.append(self.articles[i:i+10000])

        for package in packages:
                toappend = getlinkcount(wptools, package)
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
            self.score.append((article, weightscored))
            self.score_unranked[article] = weightedscore

        self.score = sorted(self.score, key=operator.itemgetter(1), reverse=True)

        # Calculating minimum scores
        # The idea is that there is a minimum score for something to be top, high, or mid-priority
        # The script is fed the category name for the unknown-importance/unknown-priority category
        # Based on this, derive category names for top/high/mid/low, add all the counts together...
        # ...then calculate ratio for top/high/mid as a ratio of the total...
        # ...multiply that ratio by the count of self.score, convert to an integer
        # ...and then threshold = self.score[that integer][1]
        # This gives us a general sense of what proportion of articles should be considered top/high/mid/low
        # Far from perfect but it's a start.

        print("Calculating priority thresholds...")
        toppriority = unknownpriority.replace("Unknown-", "Top-")
        highpriority = unknownpriority.replace("Unknown-", "High-")
        midpriority = unknownpriority.replace("Unknown-", "Mid-")
        lowpriority = unknownpriority.replace("Unknown-", "Low-")  # Easy enough...

        toppriority_count = wptools.query('wiki', 'select count(*) from categorylinks where cl_type = "page" and cl_to = {0}'.format(toppriority), None)[0][0]
        highpriority_count = wptools.query('wiki', 'select count(*) from categorylinks where cl_type = "page" and cl_to = {0}'.format(highpriority), None)[0][0]
        midpriority_count = wptools.query('wiki', 'select count(*) from categorylinks where cl_type = "page" and cl_to = {0}'.format(midpriority), None)[0][0]
        lowpriority_count = wptools.query('wiki', 'select count(*) from categorylinks where cl_type = "page" and cl_to = {0}'.format(lowpriority), None)[0][0]

        total_assessed = toppriority_count + highpriority_count + midpriority_count + lowpriority_count

        top_index = int((toppriority_count / total_assessed) * len(self.articles) - 1)
        high_index = int((highpriority_count / total_assessed) * len(self.articles) -1)
        mid_index = int((midpriority_count / total_assessed) * len(self.articles) -1)

        self.threshold_top = self.score[top_index][1]
        self.threshold_high = self.score[high_index][1]
        self.threshold_mid = self.score[mid_index][1]

    def prioritypredictor(self, pagetitle):
        # Pull pagescore if already defined
        # Otherwise, compute it "de novo"
        if pagetitle in self.articles:
            pagescore = self.score_unranked[pagetitle]
        else:
            pageviews = log(getpageviews(pagetitle)) / self.mostviews
            linkcount = getlinkcount([pagetitle])[0][1] / self.mostlinks
            pagescore = (pageviews * 0.75) + (linkcount * 0.25)

        if pagescore >= self.threshold_top:
            return "Top"

        if pagescore >= self.threshold_high:
            return "High"

        if pagescore >= self.threshold_mid:
            return "Mid"

        # If none of these...
        return "Low"