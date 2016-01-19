"""
Extracts a list of features for a set of pages after batch computing stats.
Reads page_id[TAB]wikiproject_title[TAB]rating triplets from stdin and writes
feature[TAB]feature[TAB]...[TAB]rating to stdout.

Usage:
    batch_extract_features -h | --help
    batch_extract_features <features> <view-log>...
                           --host=<name> --database=<database>
                           [-p=<num>] [-u=<user>] [--defaults-file=<path>]

Options:
    -h --help               Prints this documentation
    <features>              The python ClassPath of a list of Feature
    <view-log>              The path of a hourly view log file
    --host=<name>                  The hostname of a MediaWiki database
    -p <num> --port=<num>          The port of a MediaWiki database
                                   [default: 3306]
    -d <dbname> --dbname=<dbname>  The database to contect to
    -u <user>  --user=<user>       The username to use when connecting to the
                                   MediaWiki database [default: <current user>]
    --defaults-file=<path>  The path to a MySQL defaults file
                            [default: <~/.my.cnf>]

Example:
    wps batch_extract_features wps.enwiki.importance \
        /project/logs/2015/05/*.gz \
        --hst enwiki.labsdb \
        --dbname enwiki \
"""
import getpass
import gzip
import os

import docopt
import pymysql
from revscoring.dependencies import solve
from revscoring.utilities.util import import_from_path


def main(argv=None):
    args = docopt.docopt(__doc__, argv=argv)

    features = import_from_path(args['<features>'])

    if args['--user'] == "<current user>":
        user = getpass.getuser()
    else:
        user = args['--user']

    if args['--defaults-file'] == "<~/.my.cnf>":
        if os.path.exists(os.path.expanduser("~/.my.cnf")):
            defaults_file = os.path.expanduser("~/.my.cnf")
        else:
            defaults_file = None
    else:
        defaults_file = args['--defaults-file']

    view_logs = (gzip.open(p) for p in args['<view-log>'])

    dbconn = pymysql.connect(
        host=args['--host'],
        port=int(args['--port']),
        db=args['--dbname'],
        read_default_file=defaults_file,
        user=user
    )

    run(features, view_logs, dbconn)

def run(features, view_log_paths, dbconn):

    # Batch and cache PageStats

    # Define page_stats datasource
    # Assumes pages_stats has been populated
    def process_page_stats(page_id, wp_title):
        return pages_stats[(page_id, wp_title)]
    batch_page_stats = Datasource("page.stats", process_page_stats,
                                  depends_on=[page.id, page.wikiproject_title])

    # For each page/rating
    for page_id, wikiproject_title, rating in page_wikiproject_rating:

        # Extract feature values
        values = solve(enwiki.importance,
                       cache={page.id: page_id,
                              page.wikiproject_title: wikiproject_title},
                       context={batch_page_stats})

        # Write features to stdout
        print("\t".join([str(f) for f in values] + rating))
