# coding: utf-8
from time import sleep
import psycopg2 as pg
import psycopg2.extensions
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)
import pywikibot as wp
import signal


while True:
    try:
        from . import const, settings
        break
    except ImportError:
        wp.output("No config info available yet. Sleeping 2 seconds.")
        sleep(2)
        
if settings.mb_user is None or settings.mb_password is None:
    wp.output("No MusicBrainz login data, no redirects will be fixed")
    editing = None
else:
    from .musicbrainz_bot import editing
from time import sleep
from urlparse import urlparse


# Set up a signal handler to reload the settings on SIGHUP
def signal_handler(signal, frame):
    wp.output("HUP received")
    wp.output("Old RO connection: {}".format(settings.readonly_connection_string))
    wp.output("Old RW connection: {}".format(settings.readwrite_connection_string))
    wp.output("Old mb_user {}".format(repr(settings.mb_user)))
    reload(settings)
    wp.output("New RO connection: {}".format(settings.readonly_connection_string))
    wp.output("New RW connection: {}".format(settings.readwrite_connection_string))
    wp.output("New mb_user {}".format(repr(settings.mb_user)))
    setup_db()


signal.signal(signal.SIGHUP, signal_handler)


WIKI_PREFIX = "/wiki/"


readonly_db = None
readwrite_db = None


class IsDisambigPage(Exception):
    pass


class IsRedirectPage(Exception):
    def __init__(self, old, new):
        self.old = old
        self.new = new

    def __str__(self):
        return "%s is a redirect to %s" % (self.old, self.new)


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


def create_already_processed_query(entitytype):
    """Creates a specific query for `entitytype` from
    `CONST.GENERIC_ALREADY_PROCESSED_QUERY`

    """
    return const.GENERIC_ALREADY_PROCESSED_QUERY.format(etype=entitytype)


def create_done_func(entitytype):
    """Creates a specific function for `entitytype` from
    `const.GENERIC_DONE_QUERY`.
    """
    query = const.GENERIC_DONE_QUERY.format(etype=entitytype)
    func = lambda mbid: readwrite_db.cursor().execute(query, {'mbid': mbid})
    return func


def create_processed_table_query(entitytype):
    """Creates a specific query for `entitytype` from
    `const.GENERIC_CREATE_PROCESSED_TABLE_QUERY`.
    """
    return const.GENERIC_CREATE_PROCESSED_TABLE_QUERY.format(etype=entitytype)


def setup_db():
    global readonly_db
    if readonly_db is not None:
        readonly_db.close()
    readonly_db = pg.connect(settings.readonly_connection_string)
    readonly_db.autocommit = True

    global readwrite_db
    if readwrite_db is not None:
        readonly_db.close()
    readwrite_db = pg.connect(settings.readonly_connection_string)
    readwrite_db.autocommit = True


def create_table(query):
    cur = readwrite_db.cursor()
    cur.execute(query)
    readwrite_db.commit()


def do_readonly_query(query, limit):
    """Perform `query` against the read only database."""
    cur = readonly_db.cursor()
    cur.execute(query, (limit,))
    return cur


def do_readwrite_query(query):
    """Perform `query` against the read-write database."""
    cur = readonly_db.cursor()
    cur.execute(query)
    return cur


def check_redirect_and_disambig(wikilink, page):
    """Check if `page` is a redirect or disambiguation page"""
    if page.isRedirectPage():
        page = page.getRedirectTarget()
        raise IsRedirectPage(wikilink, page.full_url())
    if page.isDisambig():
        raise IsDisambigPage()


def get_wikidata_itempage_from_wikilink(wikilink):
    """Given a link to a wikipedia page, retrieve its page on Wikidata"""
    parsed_url = urlparse(wikilink)
    if "wikipedia" in parsed_url.netloc:
        pagename = parsed_url.path.replace(WIKI_PREFIX, "")
        wikilanguage = parsed_url.netloc.split(".")[0]
        wikisite = wp.Site(wikilanguage, "wikipedia")
        enwikipage = wp.Page(wikisite, pagename)
        check_redirect_and_disambig(wikilink, enwikipage)
        try:
            wikidatapage = wp.ItemPage.fromPage(enwikipage)
        except wp.NoPage:
            wp.output("%s does not exist" % enwikipage)
            return None
    elif "wikidata" in parsed_url.netloc:
        pagename = parsed_url.path.replace(WIKI_PREFIX, "")
        wikidatapage = wp.ItemPage(const.WIKIDATA_DATASITE, pagename)
        check_redirect_and_disambig(wikilink, wikidatapage)
    else:
        raise ValueError("%s is not a link to a wikipedia page" % wikilink)
    try:
        wikidatapage.get()
    except wp.NoPage:
        return None
    return wikidatapage


class Bot(object):
    edit_note = "%s is only a redirect to %s"

    def __init__(self):
        if settings.mb_user is None or settings.mb_password is None:
            wp.output("MusicBrainz credentials are not configured, not enabling editing.")
            self.client = None
        else:
            wp.output("MusicBrainz credentials not configured, enabling editing.")
            self.client = editing.MusicBrainzClient(settings.mb_user,
                                                    settings.mb_password,
                                                    "https://musicbrainz.org")
        self._current_entity_type = None
        self.linkids = None
        self.property_id = None

    @property
    def current_entity_type(self):
        return self._current_entity_type

    @current_entity_type.setter
    def current_entity_type(self, new_type):
        self.donefunc = create_done_func(new_type)
        self.linkids = const.LINK_IDS[new_type]
        self.property_id = const.PROPERTY_IDS[new_type]
        self._current_entity_type = new_type

    def add_mbid_claim_to_item(self, item, mbid):
        """
        Adds a claim with pid `pid` with value `mbid` to `item` and call `donefunc`
        with `mbid` to signal the completion.

        :type pid: str
        :type mbid: str
        :type item: pywikibot.ItemPage
        """
        claim = wp.Claim(const.WIKIDATA_DATASITE, self.property_id)
        claim.setTarget(mbid)
        wp.output(u"Adding property {pid}, value {mbid} to {title}".format
                  (pid=self.property_id, mbid=mbid, title=item.title()))
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
            self.donefunc(mbid)

    def fix_redirect(self, gid, old, new):
        """
        :param gid str:
        :param old str:
        :param new str:
        """
        if wp.config.simulate:
            wp.output("Simulation, not fixing the redirect from %s to %s" %
                      (old, new))
            return
        if self.client is None:
            return
        wp.output("Fixing the redirect from %s to %s" % (old, new))
        self.client.edit_url(gid, old, new, self.edit_note % (old, new))

    def process_result(self, result):
        entity_gid, url_gid, wikipage = result
        wp.output("» {wp} https://musicbrainz.org/{entitytype}/{gid}".format(
            entitytype=self._current_entity_type.replace("_", "-"),
            wp=wikipage,
            gid=entity_gid
        ))
        try:
            itempage = get_wikidata_itempage_from_wikilink(wikipage)
        except wp.NoSuchSite:
            wp.output("{page} no supported family".format(page=wikipage))
            return
        except IsDisambigPage:
            wp.output("{page} is a disambiguation page".format(page=wikipage))
            return
        except IsRedirectPage as e:
            wp.output("{page} is a redirect".format(page=wikipage))
            self.fix_redirect(url_gid, e.old, e.new)
            return
        except ValueError as e:
            wp.output(e)
            return

        if itempage is None:
            wp.debug(u"There's no wikidata page for {mbid}".format(mbid=entity_gid),
                     layer="")
            return

        if any((key.lower() == self.property_id.lower() and
               claim.target == entity_gid)
               for key, claims in itempage.claims.items() for claim in claims):
            wp.output(u"{page} already has property {pid} with value {mbid}".
                      format(page=wikipage,
                             mbid=entity_gid,
                             pid=self.property_id))
            self.donefunc(entity_gid)
            return

        wp.output("{mbid} is not linked in Wikidata".format(
                  mbid=entity_gid))
        self.add_mbid_claim_to_item(itempage, entity_gid)


def entity_type_loop(bot, entitytype, limit):
    """Processes up to `limit` entities of type `entitytype`.

    :param bot Bot:
    :param entitytype str:
    :param limit int:
    """
    bot.current_entity_type = entitytype
    linkids = const.LINK_IDS[entitytype]

    wiki_entity_query = create_url_mbid_query(entitytype, linkids)
    all_results = do_readonly_query(wiki_entity_query, limit)
    already_processed_query = create_already_processed_query(entitytype)
    already_processed_results = frozenset(
           do_readwrite_query(already_processed_query))

    results_to_process = [r for r in all_results if r[0] not in
                          already_processed_results]

    if len(results_to_process) == 0:
        wp.output("No more unprocessed entries in MB")

    map(bot.process_result, results_to_process)


def mainloop():
    limit = None
    entities = sorted(const.PROPERTY_IDS.keys())

    for arg in wp.handle_args():
        if arg.startswith('-limit'):
            limit = int(arg[len('-limit:'):])
        elif arg.startswith("-entities"):
            entities = arg[len("-entities:"):].split(",")

    const.MUSICBRAINZ_CLAIM.setTarget(const.MUSICBRAINZ_WIKIDATAPAGE)
    setup_db()

    for entitytype in entities:
        processed_table_query = create_processed_table_query(entitytype)
        create_table(processed_table_query)

    bot = Bot()

    while True:
        const.WIKIDATA.login()
        for entitytype in entities:
            entity_type_loop(bot, entitytype, limit)
        sleep(settings.sleep_time_in_seconds)
