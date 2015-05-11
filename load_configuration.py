# -*- coding: utf-8 -*-
"""
Loads wikiproject.json, validates it, stores it
Copyright (C) 2015 James Hare
Licensed under MIT License: http://mitlicense.org
"""

import os
import sys
import configparser
import json
import mw
import datetime
from bs4 import BeautifulSoup
from project_index import WikiProjectTools


def main():

    loginfile = configparser.ConfigParser()
    loginfile.read([os.path.expanduser('~/.wiki.ini')])
    username = loginfile.get('wiki', 'username')
    password = loginfile.get('wiki', 'password')

    enwp = mw.Wiki('https://en.wikipedia.org/w/api.php')
    enwp.login(username, password)

    # Exports the contents of the wikiproject.json page
    params = {'action': 'query', 'format': 'json', 'titles': 'Wikipedia:WikiProject X/wikiproject.json', 'export': ''}
    data = enwp.request(params)

    dump = data['query']['export']['*']

    # We now have a calzone with JSON filling in an XML crust. Boy is this stupid.
    output = BeautifulSoup(dump, 'xml')
    output = output.find('text')  # The contents are stored in an XML field called 'text'
    output = output.get_text()

    # We now have the JSON blob, in string format.
    try:
        output = json.loads(output)
    except ValueError as ack:  # If JSON is invalid
        now = datetime.datetime.utcnow()
        wikitime = now.strftime('%Y%m%d%H%M%S')
        report = str(wikitime) + ': ' + str(ack)
        filename = "errors.log"
        save = open(filename, "w")
        save.write(report)
        save.close()
        sys.exit()

    print(output)

if __name__ == "__main__":
    main()