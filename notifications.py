# -*- coding: utf-8 -*-
"""
Tools related to the WikiProject notification system
Copyright (C) 2015 James Hare
Licensed under MIT License: http://mitlicense.org
"""


import pywikibot
import mwparserfromhell
import datetime
from project_index import WikiProjectTools


class WikiProjectNotifications:
    def __init__(self):
        self.wptools = WikiProjectTools()
        q = ('create table if not exists notifications '
             '(n_id int(11) NOT NULL auto_increment, '
             'n_project VARCHAR(255) character set utf8 collate utf8_unicode_ci, '
             'n_variant VARCHAR(255) character set utf8 collate utf8_unicode_ci, '
             'n_content TEXT character set utf8 collate utf8_unicode_ci, '
             'primary key (n_id)) '
             'engine=innodb character set=utf8;')
        #self.wptools.query('index', q, None)
        self.bot = pywikibot.Site('en', 'wikipedia')

        # Recognized notification variants
        # A variant that is not any of these kinds will cause an error
        # variantname --> template parameter name

        date = datetime.datetime.utcnow().strftime('%d %B %Y')
        self.recognizedvariants = {'newmember': \
                                   'notification_when_a_new_member_joins', \
                                   'newdiscussion': \
                                   'notification_when_a_new_discussion_topic_is_posted'}
        self.varianttext = {'newmember': \
                            '==New member report for ' + date + '==\nThe following users joined the WikiProject in the past day:\n', \
                            'newdiscussion': \
                            '==New discussion report for ' + date + '==\nNew discussions that are of interest to the WikiProject:\n'}


    def post(self, project, variant, content):
        '''
        Adds an item to the WikiProject Notification Center, to be included in the next update
        '''

        if variant in self.recognizedvariants:
            q = 'insert into notifications (n_project, n_variant, n_content) values ("{0}", "{1}", "{2}");'
            q = q.format(project, variant, content)
            self.wptools.query('index', q, None)
        else:
            raise NotificationVariantError(variant)


    def findsubscribers(self):
        '''
        Generates a dictionary of WikiProjects with notification centers and corresponding report subscribers
        '''

        q = ('select page_title from templatelinks '
             'join page on page_id = tl_from and page_namespace = tl_from_namespace '
             'where page_namespace = 2 and tl_namespace = 10 '
             'and tl_title = "WikiProjectCard";')

        output = {}
        for row in self.wptools.query('wiki', q, None):
            title = row[0].decode('utf-8')
            components = title.split('/')  # e.g. ['Harej', 'WikiProjectCards', 'WikiProject_Women_in_Technology']

            title = "User: " + title
            username = components[0]
            wikiproject = '/'.join(components[2:])  # In case the WikiProject name somehow has a slash in it

            page = pywikibot.Page(self.bot, title)
            config = mwparserfromhell.parse(page.text)
            config = config.filter_templates()[0]

            if wikiproject not in output:
                output[wikiproject] = {key:[] for key in self.recognizedvariants.keys()}

            for key, param in self.recognizedvariants.items():
                if param + '=1\n' in config.params or \
                   param + '=1' in config.params:
                    output[wikiproject][key].append(username)

        return output


    def update(self):
        '''
        Posts notifications to relevant WikiProject notification pages
        '''

        subscribers = self.findsubscribers()
        reports = {}  # a dictionary of dictionaries. e.g. {'WikiProject_Biology': {'newmember': blahblahreport, 'newdiscussion': blahblahreport}}
    
        # Take database, turn into Python stuff
        id_to_delete = []
        for row in self.wptools.query('index', 'select n_id, n_project, n_variant, n_content from notifications;', None):
            id_to_delete.append(row[0])
            wikiproject = row[1]
            variant = row[2]
            content = row[3]
    
            # Initializing entry in `reports` just in case
            if wikiproject not in reports:
                reports[wikiproject] = {key:'' for key in self.recognizedvariants.keys()}
    
            # Appending content item to the report accordingly
            reports[wikiproject][variant] += content + '\n'
    
        print(reports)  # debug

        # Appending each subscriber name to the report to tag them
        # And then saving report
        for wikiproject in reports:
            for reportkey in reports[wikiproject]:
                if reports[wikiproject][reportkey] != '':  # i.e. if there is anything to report
                    optout = ('You have received this notification because you signed up to receive it. '
                              'If you wish to no longer receive this notification, '
                              '[https://en.wikipedia.org/wiki/Special:MyPage/WikiProjectCards/' + wikiproject + '?action=edit '
                              'edit your WikiProjectCard] and remove the line that says <tt>|' + self.recognizedvariants[reportkey] + '=1</tt>.'
                              ' ~~~~')
                    reports[wikiproject][reportkey] = self.varianttext[reportkey] + reports[wikiproject][reportkey]
                    for subscriber in subscribers[wikiproject][reportkey]:
                        reports[wikiproject][reportkey] += '[[User:' + subscriber + '| ]]'
                    reports[wikiproject][reportkey] += optout
        
                    # Saving report
                    page = pywikibot.Page(self.bot, 'Wikipedia:' + wikiproject + '/Notifications')
                    page.text = page.text + '\n' + reports[wikiproject][reportkey]
                    page.save("New notification", minor=False, async=True)
    
        # Deleting old records now that notifications have been sent out
        if len(id_to_delete) > 0:
            if len(id_to_delete) == 1:
                self.wptools.query('index', 'delete from notifications where n_id = {0};'.format(id_to_delete[0]), None)
            else:
                self.wptools.query('index', 'delete from notifications where n_id in {0};'.format(tuple(id_to_delete)), None)


if __name__ == "__main__":
    go = WikiProjectNotifications()
    go.update()