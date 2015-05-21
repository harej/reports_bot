# -*- coding: utf-8 -*-
"""
Updates the WikiProject Directory
Copyright (C) 2015 Betacommand, James Hare
Licensed under MIT License: http://mitlicense.org
"""

import sys
import json
import codecs
import re
import os
import time
import pywikibot
from project_index import WikiProjectTools


site = wikipedia.getSite('en','wikipedia')
# Basic object for getting a time delta, IE tracking how long different parts of the code take to run
default_config = get_wiki_json()
class td(object):
    def __init__(self):
        self.start_time = None
        self.delta = None
        self.start()
    def start(self):
        self.start_time = time.time()
    def stop(self):
        self.delta = time.time()-self.start_time
    def diff(self):
        self.stop()
        hours, remainder= divmod(self.delta, 60*60)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return u'%02d:%02d:%02ds' % (hours,minutes,seconds)
        else:
            return u'%02d:%02ds' % (minutes,seconds)

def main():
    wptools = WikiProjectTools()

    # Purge the two runtime logs.
    log2('','project_analysis.log')
    log2('','project_stats.log')

    # List of projects we are working on
    # Methodology: List from Project Index + List from Formal Definition, minus duplicates
    # This will cover all of our bases.
    projects = []
    projectindex = wptools.query('index', 'select distinct pi_project from projectindex;', None)
    for row in projectindex:
        projects.append(row[0])
    formaldefinition = wptools.query('wiki', 'select distinct page.page_title from page join categorylinks on page.page_id = categorylinks.cl_from left join redirect on page.page_id = redirect.rd_from where page_namespace = 4 and page_title not like "%/%" and rd_title is null and (cl_to in (select page.page_title from page where page_namespace = 14 and page_title like "%\_WikiProjects" and page_title not like "%\_for\_WikiProjects" and page_title not like "%\_of\_WikiProjects") or page_title like "WikiProject\_%");', None)  # http://quarry.wmflabs.org/query/3509
    for row in formaldefinition:
        row = 'Wikipedia:' + row[0].decode('utf-8')  # Making output consistent with formatting used in projects list
        if row not in projects:
            projects.append(row)

    # Get our list of users who opted out
    opted_out = get_opt_out()
    # iterate over the project list and run a report for each
    for project in projects:
        report = project_stats(project,opted_out)
        report.run()

def get_opt_out():
    text = wikipedia.Page(site,'User:Reports bot/Opt-out').get()
    users = []
    regexes =[re.findall('\[\[User:(.*?)\|',text,re.I), re.findall('\{\{user\|(.*?)\}\}',text,re.I), re.findall('\[\[:User:(.*?)\]',text,re.I), re.findall('\[\[:User talk:(.*?)\]',text,re.I)]
    for results in regexes:
        for user in results:
            users.append(user)
    users.extend(get_bots())
    return users
def get_wiki_json():
    data = wptools.query('index', 'select json from config;', None)
    data = eval(data[0][0])
    return data
# main report object
class project_stats(object):
    def __init__(self,project,opted_out):
        # takes a unicode project name, and a list of users who do not want to be in the reports.
        self.opted_out = opted_out
        self.project = project
        self.project_users = []
        self.scope_users = []
        self.project_totals = []
        self.scope_totals = []
        self.number_of_articles = None
        self.total_scope_editcount = None
        self.scope_member_edit_count = 0
        self.report_page = {
                                                    'brand_background_color':None,
                                                    'brand_image':None,
                                                    'name':None,
                                                    'article_count':None,
                                                    'project_editors':None,
                                                    'scope_editors':None,
                                                    'scope_member_editcount':None,
                                                    'scope_editcount':None,
                                                    'project_editors':None,
                                                    'scope_editors':None,
                                                }
    def log(self,text,file=None):
        # This is a dual purpose log method. It can be used to log to any given 
        # file, or defaults to a master file with timestamp. If a filename is given,
        # it is assumed that the higher logger is handeling new lines where needed
        if not file:
            file = u'project_analysis.log'
            tm = time.strftime(u'%Y%m%d %H:%M:%S',time.localtime())
            text = u'* %s %s\n'    % (tm,text)
        f3 = codecs.open(file, 'a', 'utf-8')
        f3.write(text)
        f3.close()
    def run(self):
        # Main thread of the report
        if default_config['projects'].has_key(self.project):
            for key in self.report_page: 
                if key in default_config['projects'][project]:
                    self.report_page[key] = default_config['projects'][project][key]
        # combined user list for both scope and project editors
        users = []
        # diag log info
        self.log(self.project)
        timer = td()
        # diag log info and populating the number of articles within the scope of the project
        self.log('Article count: %s' % self.get_article_count())
        self.log(timer.diff())
        timer = td()
        # this is getting a list of username, edit counts for project editors
        self.project_totals = [x for x in self.query_wikiproject_edits()]
        for user,editcount in self.project_totals:
            if user not in self.opted_out:
                users.append(u'* {{user|%s}}' % user)
        self.log('Project editors: %s' % len(users))
        self.log(timer.diff())
        # add project editors to the master user list
        timer = td()
        # same as above but for scope edits
        self.scope_totals = [x for x in self.query_scope_editors()]
        # iterate over the user/editcount list for scope edits and extract total edit count and user list
        scope_editors = []
        for user,editcount in self.scope_totals:
            if user not in self.opted_out:
                self.scope_member_edit_count+=editcount
                scope_editors.append(u'* {{user|%s}}' % user)
        self.log("Scope editors: %s" % len(scope_editors))
        self.log(timer.diff())
        timer = td()
        # Get a count for the number of edits to the scope in the given timeframe
        self.log("Scope edits: %s" % self.query_scope_edits())
        self.log(timer.diff())
        # log the stats for each project in a primary list log
        self.log(u'{{WikiProject directory entry|project=%s|number_of_articles=%s|wp_editors=%s|scope_editors=%s|scope_member_edit_count=%s|scope_edit_count=%s}}\n' % (self.project,self.number_of_articles,len(self.project_totals),len(self.scope_totals),self.scope_member_edit_count,self.total_scope_editcount),'project_stats.log')
        # dump a list of users who have not opted out to a file in the wp_reports subdirectory
        log_lines(sorted(set(users),'wp_reports/%s_project.log' % self.project)
        log_lines(sorted(list(set(scope_editors))),'wp_reports/%s_scope.log' % self.project)
        
        wikipedia.Page(site,u'User:Reports bot/Directory/%s' % self.project)
        text = "{{WikiProject description page\n| project = %(name)s\n| number_of_articles = %(article_count)s\n| wp_editors = %(project_editors)s\n| scope_editors = %(scope_editors)s\n| scope_member_edit_count = %(scope_member_editcount)s\n| scope_edit_count = %(scope_editcount)s\n| list_of_active_wikiproject_participants = %(project_editors)s\n| list_of_active_subject_area_editors = %(scope_editors)s\n}}\n"

        
    # gets a count ff the number of articles within the project scope
    def get_article_count(self):
        self._get_article_count_template(self)
    
    
    def _get_article_count_template(self):
        # sanitize the page name to a degree
        self.project = re.sub(u'^Wikipedia:','',self.project)
        self.project = re.sub(u' ','_',self.project)
        # using a dictionary enables a little more sane and human readable SQL creation
        data = {
                        'wp_name': self.project,
                        }
        query = "SELECT count(page_title) FROM templatelinks LEFT JOIN page ON page_id = tl_from WHERE tl_namespace = 10 AND tl_title = \"%(wp_name)s\"" % data
        self.number_of_articles = run_query(query,'enwiki_p')[0][0]
        return self.number_of_articles
    # get a count of the number of edits to the wikiproject space
    
    def query_scope_edits(self):
        # sanitize the page name to a degree
        self.project = re.sub(u'^Wikipedia:','',self.project)
        self.project = re.sub(u' ','_',self.project)

        # using a dictionary enables a little more sane and human readable SQL creation
        data = {
                        'wp_name': self.project,
                         # setting default historical limitation to 90 days
                        'start_date':time.strftime('%Y%m%d000000',time.gmtime(time.time()-(60*60*24*30))),
                        # setting the end date as today, if we want to change this later we can for historical information.
                        'end_date'    :time.strftime('%Y%m%d000000',time.gmtime(time.time())),
                        }
        query = "SELECT COUNT(*) FROM revision_userindex LEFT JOIN page ON page_id = rev_page WHERE (page_namespace = 0 OR page_namespace = 1) AND page_title IN (SELECT page_title FROM templatelinks LEFT JOIN page ON page_id = tl_from WHERE tl_namespace = 10 AND tl_title = \"%(wp_name)s\") AND rev_timestamp > %(start_date)s AND rev_timestamp < %(end_date)s;" % data
        # print query
        self.total_scope_editcount = run_query(query,'enwiki_p')[0][0]
        return self.total_scope_editcount

    # get a list of editors and edit count for contributions to the project scope in the last 30 days and at least 5 edits
    def query_scope_editors(self):
        # sanitize the page name to a degree
        self.project = re.sub(u'^Wikipedia:','',self.project)
        self.project = re.sub(u' ','_',self.project)

        # using a dictionary enables a little more sane and human readable SQL creation
        data = {
                        'wp_name': self.project,
                         # setting default historical limitation to 90 days
                        'start_date':time.strftime('%Y%m%d000000',time.gmtime(time.time()-(60*60*24*30))),
                        # setting the end date as today, if we want to change this later we can for historical information.
                        'end_date'    :time.strftime('%Y%m%d000000',time.gmtime(time.time())),
                        }
        query = "SELECT rev_user_text,COUNT(*) FROM revision_userindex LEFT JOIN page ON page_id = rev_page WHERE (page_namespace = 0 OR page_namespace = 1) AND page_title IN (SELECT page_title FROM templatelinks LEFT JOIN page ON page_id = tl_from WHERE tl_namespace = 10 AND tl_title = \"%(wp_name)s\") AND rev_timestamp > %(start_date)s AND rev_timestamp < %(end_date)s GROUP BY rev_user_text HAVING count(*) >= 5 ORDER BY COUNT(*) DESC;" % data
        # print query
        for result in run_query(query,'enwiki_p'):
            yield result[0].decode('utf-8'),result[1]
    # same as above but for the last 90 days and at least 2 edits
    def query_wikiproject_edits(self):
        # sanitize the page name to a degree
        self.project = re.sub(u'^Wikipedia:','',self.project)
        self.project = re.sub(u' ','_',self.project)

        # using a dictionary enables a little more sane and human readable SQL creation
        data = {
                        'wp_name': self.project,
                         # setting default historical limitation to 90 days
                        'start_date':time.strftime('%Y%m%d000000',time.gmtime(time.time()-(60*60*24*90))),
                        # setting the end date as today, if we want to change this later we can for historical information.
                        'end_date'    :time.strftime('%Y%m%d000000',time.gmtime(time.time())),
                        }
        query = "select rev_user_text,count(*) from page left join revision on page_id = rev_page where (page_namespace = 4 OR page_namespace = 5) and (page_title like \"%(wp_name)s/%%\" OR page_title = \"%(wp_name)s\")    and rev_timestamp > %(start_date)s and rev_timestamp < %(end_date)s group by rev_user_text HAVING count(*) > 1 ORDER BY COUNT(*) DESC;"    % data
        for result in run_query(query,'enwiki_p'):
            yield result[0].decode('utf-8'),result[1]


# abstract wrapper for running queries, handles opening, retrieving results, and closing the database
def run_query(query,database):
    # query        : a string formatted mysql query
    # database : the database that you want to run the query on formatted in a enwiki_p format

    # strip the _p from the database name so we can connect to the correct host.
    database2 = re.sub(u'_p',u'',database)
    # create connection, and use the credential file in the tool account
    db = MySQLdb.connect(db=database, host=database2+".labsdb", read_default_file=os.path.expanduser("~/replica.my.cnf"))
    cursor = db.cursor()
    cursor.execute(query)
    # grab results
    results = cursor.fetchall()
    # close the connection to avoid issues.
    db.close()
    # return the unprocessed database query results
    return results

# basic function for taking a list and iterating over it to save each item into a file
def get_bots():
    bots = []
    for result in run_query("select user_name from user_groups left join user on user_id = ug_user where ug_group = 'bot';",'enwiki_p'):
        bots.append(result[0].decode('utf-8'))
    return bots
def log_lines(list,file,purge = True):
    str = u'\n'
    f3 = codecs.open(file, 'a', 'utf-8')
    if purge:
        f3.truncate(0)
    for item in list:
        try:
            str=u'%s\n' % unicode(item)
            f3.write(str)
        except:
            pass
    f3.close()
# similar to the log() function above, but truncates the file before saving to it
def log2(text,file):
    f3 = codecs.open(file, 'a', 'utf-8')
    f3.truncate(0)
    f3.write(text)
    f3.close()
# basic function to get the contents of a file
def get_file(file):
    f = codecs.open(file,'r', 'utf-8')
    names = f.read()
    f.close()
    return names

if __name__ == "__main__":
    main()