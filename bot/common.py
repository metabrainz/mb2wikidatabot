import psycopg2 as pg
import psycopg2.extensions
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)
import pywikibot as wp


from urlparse import urlparse

WIKIDATA = wp.Site('wikidata', 'wikidata')

WIKI_PREFIX = "/wiki/"

DB_USER = 'musicbrainz'
DB = 'musicbrainz'

db = None


def setup_db(processed_table_query):
    global db
    db = pg.connect(database=DB, user=DB_USER)
    cur = db.cursor()
    cur.execute("SET search_path TO musicbrainz")
    cur.execute(processed_table_query)
    db.commit()


def get_entities_with_wikilinks(query, limit):
    cur = db.cursor()
    cur.execute(query, (limit,))
    return cur


def get_wikidata_itempage_from_wikilink(wikilink):
    """Given a link to a wikipedia page, retrieve its page on Wikidata"""
    parsed_url = urlparse(wikilink)
    pagename = parsed_url.path.replace(WIKI_PREFIX, "")
    wikilanguage = parsed_url.netloc.split(".")[0]
    wikisite = wp.Site(wikilanguage, "wikipedia")
    enwikipage = wp.Page(wikisite, pagename)
    wikidatapage = wp.ItemPage.fromPage(enwikipage)
    try:
        wikidatapage.get()
    except wp.NoPage as e:
        return None
    return wikidatapage


def add_mbid_claim_to_item(pid, item, mbid, donefunc, simulate=False):
    """
    Adds a claim with pid `pid` with value `mbid` to `item` and call `donefunc`
    with `mbid` to signal the completion.

    :type pid: str
    :type mbid: str
    :type item: pywikibot.ItemPage
    """
    claim = wp.Claim(WIKIDATA, pid)
    claim.setTarget(mbid)
    wp.output(u"Adding property {pid}, value {mbid} to {title}".format
              (pid=pid, mbid=mbid, title=item.title()))
    if simulate:
        wp.output("Simulation, no property has been added")
        return
    try:
        item.addClaim(claim, True)
    except wp.UserBlocked as e:
        wp.error("I have been blocked")
        exit(1)
    except wp.Error as e:
        wp.warning(e)
        return
    else:
        donefunc(mbid)


def mainloop(pid, create_processed_table_query, wiki_entity_query, donefunc):
    simulate = False
    limit = None

    for arg in wp.handleArgs():
        if arg == '-dryrun':
            simulate = True
        elif arg.startswith('-limit'):
            limit = int(arg[len('-limit:'):])

    WIKIDATA.login()
    setup_db(create_processed_table_query)
    results = get_entities_with_wikilinks(wiki_entity_query, limit)

    if results.rowcount == 0:
        wp.output("No more unprocessed entries in MB")
        exit(0)

    for index, (mbid, wikipage) in enumerate(results):
        try:
            itempage = get_wikidata_itempage_from_wikilink(wikipage)
        except wp.NoSuchSite:
            wp.output("{page}: no supported family".format(page=wikipage))
            continue
        if itempage is None:
            wp.output(u"There's no wikidata page for {mbid}".format(mbid=mbid))
            continue

        if any(key.lower() == pid.lower() for key in itempage.claims.keys()):
            wp.output(u"{mbid} already has property {pid}".format(mbid=mbid,
                                                                     pid=pid))
            donefunc(mbid)
            continue

        wp.output("{mbid} is not linked in in Wikidata".format(
                    mbid=mbid))
        add_mbid_claim_to_item(pid, itempage, mbid, donefunc, simulate)
        if index % 100 == 0:
            db.commit()
