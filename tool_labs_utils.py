# -*- coding: utf-8 -*-
"""
Generic utility for querying a database on Tool Labs
Copyright (C) 2015 James Hare
Licensed under MIT License: http://mitlicense.org
"""

import pymysql

class ToolLabs:
    def query(self, host, db, sqlquery, values):
        """Generic wrapper for carrying out MySQL queries"""

        conn = pymysql.connect(host=host, port=3306, db=db, read_default_file='~/.my.cnf', charset='utf8')
        cur = conn.cursor()
        cur.execute(sqlquery, values)
        data = []
        for row in cur:
            data.append(row)
        conn.commit()
        return data

class WMFReplica:
    def query(self, db, sqlquery, values):
        """Queries for WMF wiki database replicas on Labs (e.g. enwiki)"""
        return ToolLabs.query(db + '.labsdb', db + '_p', sqlquery, values)

class ToolsDB:
    def query(self, db, sqlquery, values):
        """Queries a Tool Labs database"""
        return ToolLabs.query('tools-db', db, sqlquery, values)