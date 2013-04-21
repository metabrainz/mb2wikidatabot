import psycopg2 as pg
import pywikibot as wp


from urlparse import urlparse

WIKIDATA = wp.Site('wikidata', 'wikidata')
ENWIKI = wp.Site('en', 'wikipedia')

ENWIKI_PREFIX = "/wiki/"

DB_USER = 'musicbrainz'
DB = 'musicbrainz'

db = None

def get_entities_with_wikilinks(processed_table_query, query):
    global db
    db = pg.connect(database=DB, user=DB_USER)
    cur = db.cursor()
    cur.execute("SET search_path TO musicbrainz")
    cur.execute(processed_table_query)
    db.commit()
    cur.execute(query)
    return cur


def get_wikidata_itempage_from_wikilink(wikilink):
    """Given a link to a wikipedia page, retrieve its page on Wikidata"""
    pagename = urlparse(wikilink).path.replace(ENWIKI_PREFIX, "")
    enwikipage = wp.Page(ENWIKI, pagename)
    wikidatapage = wp.ItemPage.fromPage(enwikipage)
    try:
        wikidatapage.get()
    except wp.NoPage as e:
        return None
    return wikidatapage
