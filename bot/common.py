import psycopg2 as pg
import psycopg2.extensions
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)
import pywikibot as wp


from . import const, settings
from urlparse import urlparse


WIKI_PREFIX = "/wiki/"


db = None


class IsDisambigPage(Exception):
    pass


def create_url_mbid_query(entitytype, linkids):
    """Creates a specific query for `entitytype` and `linkids` from
    `const.GENERIC_URL_MBID_QUERY`.
    """
    custom = const.QUERIES[entitytype]
    if custom is not None:
        return custom
    return const.GENERIC_URL_MBID_QUERY.format(etype=entitytype,
                                               wikipedia_linkid=linkids.wikipedia,
                                               wikidata_linkid=linkids.wikidata)


def create_done_func(entitytype):
    """Creates a specific function for `entitytype` from
    `const.GENERIC_DONE_QUERY`.
    """
    query = const.GENERIC_DONE_QUERY.format(etype=entitytype)
    func = lambda mbid: db.cursor().execute(query, {'mbid': mbid})
    return func


def create_processed_table_query(entitytype):
    """Creates a specific query for `entitytype` from
    `const.GENERIC_CREATE_PROCESSED_TABLE_QUERY`.
    """
    return const.GENERIC_CREATE_PROCESSED_TABLE_QUERY.format(etype=entitytype)


def setup_db():
    global db
    db = pg.connect(settings.connection_string)
    db.autocommit = True


def create_table(query):
    cur = db.cursor()
    cur.execute("SET search_path TO musicbrainz")
    cur.execute(query)
    db.commit()


def get_entities_with_wikilinks(query, limit):
    cur = db.cursor()
    cur.execute(query, (limit,))
    return cur


def get_wikidata_itempage_from_wikilink(wikilink):
    """Given a link to a wikipedia page, retrieve its page on Wikidata"""
    parsed_url = urlparse(wikilink)
    if "wikipedia" in parsed_url.netloc:
        pagename = parsed_url.path.replace(WIKI_PREFIX, "")
        wikilanguage = parsed_url.netloc.split(".")[0]
        wikisite = wp.Site(wikilanguage, "wikipedia")
        enwikipage = wp.Page(wikisite, pagename)
        if enwikipage.isDisambig():
            raise IsDisambigPage()
        try:
            wikidatapage = wp.ItemPage.fromPage(enwikipage)
        except wp.NoPage:
            return None
    elif "wikidata" in parsed_url.netloc:
        pagename = parsed_url.path.replace(WIKI_PREFIX, "")
        wikidatapage = wp.ItemPage(const.WIKIDATA_DATASITE, pagename)
    try:
        wikidatapage.get()
    except wp.NoPage:
        return None
    return wikidatapage


def add_mbid_claim_to_item(pid, item, mbid, donefunc):
    """
    Adds a claim with pid `pid` with value `mbid` to `item` and call `donefunc`
    with `mbid` to signal the completion.

    :type pid: str
    :type mbid: str
    :type item: pywikibot.ItemPage
    """
    claim = wp.Claim(const.WIKIDATA_DATASITE, pid)
    claim.setTarget(mbid)
    wp.output(u"Adding property {pid}, value {mbid} to {title}".format
              (pid=pid, mbid=mbid, title=item.title()))
    if wp.config.simulate:
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
        wp.output("Adding the source Claim")
        claim.addSource(const.MUSICBRAINZ_CLAIM, bot=True)
        donefunc(mbid)


def process_results(results, donefunc, pid):
    for index, (mbid, wikipage) in enumerate(results):
        try:
            itempage = get_wikidata_itempage_from_wikilink(wikipage)
        except wp.NoSuchSite:
            wp.output("{page} no supported family".format(page=wikipage))
            continue
        except IsDisambigPage:
            wp.output("{page} is a disambiguation page".format(page=wikipage))
            continue
        except wp.IsRedirectPage:
            wp.output("{page} is a redirect".format(page=wikipage))
            continue
        if itempage is None:
            wp.debug(u"There's no wikidata page for {mbid}".format(mbid=mbid),
                     layer="")
            continue

        if any(key.lower() == pid.lower() for key in itempage.claims.keys()):
            wp.output(u"{mbid} already has property {pid}".format(mbid=mbid,
                                                                  pid=pid))
            donefunc(mbid)
            continue

        wp.output("{mbid} is not linked in Wikidata".format(
                  mbid=mbid))
        add_mbid_claim_to_item(pid, itempage, mbid, donefunc)


def mainloop():
    create_table = False
    limit = None
    entities = None

    for arg in wp.handleArgs():
        if arg.startswith('-limit'):
            limit = int(arg[len('-limit:'):])
        elif arg == "-createtable":
            create_table = True
        elif arg.startswith("-entities"):
            entities = arg[len("-entities:"):].split(",")

    const.WIKIDATA.login()
    const.MUSICBRAINZ_CLAIM.setTarget(const.MUSICBRAINZ_WIKIDATAPAGE)
    setup_db()

    for entitytype in entities:
        property_id = const.PROPERTY_IDS[entitytype]
        linkids = const.LINK_IDS[entitytype]
        if create_table:
            processed_table_query = create_processed_table_query(entitytype)
            create_table(processed_table_query)
        wiki_entity_query = create_url_mbid_query(entitytype, linkids)
        donefunc = create_done_func(entitytype)
        results = get_entities_with_wikilinks(wiki_entity_query, limit)

        if results.rowcount == 0:
            wp.output("No more unprocessed entries in MB")
            continue

        process_results(results, donefunc, property_id)
