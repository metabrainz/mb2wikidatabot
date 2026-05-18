# coding: utf-8
"""Bot orchestration: main loop, database access, and the Bot class.

This module wires together the pure-logic modules (checks, queries, exceptions,
mb_client) with pywikibot, psycopg2, and the musicbrainz-bot editing library.
It contains module-level initialization (DB connections, signal handlers) and
is not directly importable in tests without mocking pywikibot.
"""

import datetime
from importlib import reload
from time import sleep

import psycopg2 as pg
import psycopg2.extensions

psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)
import signal

import pywikibot as wp

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
    from musicbrainz_bot import editing

from .mb_client import mb_request_with_retry


# Set up a signal handler to reload the settings on SIGHUP
def signal_handler(signal, frame):
    """Handle SIGHUP by reloading settings and restarting the main loop."""
    wp.output("HUP received")
    reload_settings()
    raise SettingsReloadedException("Settings have been reloaded during HUP")


signal.signal(signal.SIGHUP, signal_handler)


readonly_db = None
readwrite_db = None


from .exceptions import (
    IsRedirectPage,
    PageGone,
    SettingsReloadedException,
    SkipPage,
)
from .queries import create_already_processed_query as _create_already_processed_query
from .queries import create_processed_table_query as _create_processed_table_query
from .queries import create_url_mbid_query as _create_url_mbid_query


def create_url_mbid_query(entitytype, linkids):
    return _create_url_mbid_query(
        entitytype, linkids, generic_query=const.GENERIC_URL_MBID_QUERY, custom_queries=const.QUERIES
    )


def create_already_processed_query(entitytype):
    return _create_already_processed_query(entitytype, template=const.GENERIC_ALREADY_PROCESSED_QUERY)


def create_done_func(entitytype):
    """Creates a specific function for `entitytype` from
    `const.GENERIC_DONE_QUERY`.
    """
    query = const.GENERIC_DONE_QUERY.format(etype=entitytype)

    def func(mbid):
        do_readwrite_query(query, {"mbid": mbid})

    return func


def create_processed_table_query(entitytype):
    return _create_processed_table_query(entitytype, template=const.GENERIC_CREATE_PROCESSED_TABLE_QUERY)


def reload_settings():
    """Reload bot/settings.py and log the old/new connection strings."""
    wp.output("Old RO connection: {}".format(settings.readonly_connection_string))
    wp.output("Old RW connection: {}".format(settings.readwrite_connection_string))
    wp.output("Old mb_user {}".format(repr(settings.mb_user)))
    reload(settings)
    wp.output("New RO connection: {}".format(settings.readonly_connection_string))
    wp.output("New RW connection: {}".format(settings.readwrite_connection_string))
    wp.output("New mb_user {}".format(repr(settings.mb_user)))


def setup_db():
    """Initialize (or reinitialize) the readonly and readwrite DB connections."""
    global readonly_db
    if readonly_db is not None:
        readonly_db.close()
    readonly_db = pg.connect(settings.readonly_connection_string, application_name="mb2wikidatabot_readonly")
    readonly_db.autocommit = True

    global readwrite_db
    if readwrite_db is not None:
        readwrite_db.close()
    readwrite_db = pg.connect(settings.readwrite_connection_string, application_name="mb2wikidatabot_readwrite")
    readwrite_db.autocommit = True


def create_table(query):
    """Execute a CREATE TABLE query on the readwrite database."""
    cur = readwrite_db.cursor()
    cur.execute(query)
    readwrite_db.commit()


def do_readonly_query(query, limit):
    """Perform `query` against the read only database."""
    cur = readonly_db.cursor()
    cur.execute(query, (limit,))
    return cur


def do_readwrite_query(query, vars=None):
    """Perform `query` against the read-write database."""
    cur = readwrite_db.cursor()
    cur.execute(query, vars)
    return cur


from .checks import check_url_needs_to_be_skipped as _check_url_needs_to_be_skipped


def check_url_needs_to_be_skipped(wikilink, page):
    """Check if `page` is a redirect or disambiguation page"""
    _check_url_needs_to_be_skipped(
        wikilink,
        page,
        item_page_cls=wp.ItemPage,
        no_page_error=wp.exceptions.NoPageError,
        property_id_instance_of=const.PROPERTY_ID_INSTANCE_OF,
        skip_instance_of_items=const.SKIP_INSTANCE_OF_ITEMS,
    )


from .checks import get_wikidata_itempage_from_wikilink as _get_wikidata_itempage_from_wikilink


def get_wikidata_itempage_from_wikilink(wikilink):
    """Given a link to a wikipedia page, retrieve its page on Wikidata"""
    return _get_wikidata_itempage_from_wikilink(
        wikilink,
        wp=wp,
        wikidata_datasite=const.WIKIDATA_DATASITE,
        check_skip=check_url_needs_to_be_skipped,
    )


class Bot(object):
    """Main bot that processes MusicBrainz entities and adds MBIDs to Wikidata.

    Handles the decision logic for each entity: resolve its Wikipedia/Wikidata
    URL, check if the MBID claim already exists, and either add it or handle
    redirects/dead links on the MusicBrainz side.
    """

    redirect_edit_note = "%s is only a redirect to %s"

    removed_edit_note = "%s no longer exists, marking as ended"

    def __init__(self):
        if not settings.mb_user or not settings.mb_password or not settings.mb_editor_id:
            wp.output("MusicBrainz credentials are not configured, not enabling editing.")
            self.client = None
        else:
            wp.output("MusicBrainz credentials are configured, enabling editing.")
            self.client = editing.MusicBrainzClient(
                settings.mb_user, settings.mb_password, "https://musicbrainz.org", settings.mb_editor_id
            )
            self.update_rate_limits()

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

    @property
    def can_edit(self):
        if self.client is None:
            return False
        if not self.number_of_allowed_edits:
            return False
        if wp.config.simulate:
            return False
        return True

    def update_rate_limits(self):
        """
        Retrieve the current rate limit status from MusicBrainz.
        """
        if self.client is None:
            self.number_of_allowed_edits = 0
            return
        try:
            self.number_of_allowed_edits = mb_request_with_retry(self.client.edits_left)
        except Exception as e:
            wp.warning("Could not determine remaining edits: %s" % e)
            self.number_of_allowed_edits = 0

        # This includes those for today
        if not self.number_of_allowed_edits:
            wp.output("Reached the limit of open edits.")

    def _performed_edit(self):
        """
        Callback for decrementing the number of edits that can still be opened.
        Prints an informational method when the limit is reached.
        """
        self.number_of_allowed_edits -= 1
        if not self.number_of_allowed_edits:
            wp.output("Reached the limit of open edits, disabling editing")
        sleep(settings.mb_edit_delay)

    def add_mbid_claim_to_item(self, item, mbid, entity_name):
        """
        Adds a claim with pid `pid` with value `mbid` to `item`,
        with qualifiers to indicate the MB source and name,
        and call `donefunc` with `mbid` to signal the completion.

        :type pid: str
        :type mbid: str
        :type entity_name: str
        :type item: pywikibot.ItemPage
        """
        claim = wp.Claim(const.WIKIDATA_DATASITE, self.property_id)
        claim.setTarget(mbid)
        wp.output(
            "Adding property {pid}, value {mbid} to {title}".format(pid=self.property_id, mbid=mbid, title=item.title())
        )

        wp.debug("Adding the named as qualifier", layer="")
        const.NAMED_AS_CLAIM.setTarget(entity_name)
        claim.addQualifier(
            const.NAMED_AS_CLAIM.copy(),
            bot=True,
        )

        wp.debug("Adding the source claims", layer="")
        today = datetime.datetime.today()
        date = wp.WbTime(year=today.year, month=today.month, day=today.day)
        const.RETRIEVED_CLAIM.setTarget(date)
        claim.addSources(
            [const.MUSICBRAINZ_CLAIM.copy(), const.RETRIEVED_CLAIM.copy()],
            bot=True,
        )

        if wp.config.simulate:
            wp.output("Simulation, no property has been added")
            return
        try:
            item.addClaim(claim, True)
        except wp.exceptions.OtherPageSaveError:
            wp.warning("Page is protected, cannot save")
            return
        except wp.exceptions.Error as e:
            wp.warning(e)
            return
        else:
            self.donefunc(mbid)

    def fix_redirect(self, gid, old, new):
        """Edit the URL in MusicBrainz to point to the redirect target."""
        wp.output("Fixing the redirect from %s to %s" % (old, new))
        mb_request_with_retry(self.client.edit_url, gid, old, new, self.redirect_edit_note % (old, new))
        self._performed_edit()

    def end_removed(self, rel_id, link_type_id, entity_gid, url_gid, entitytype, wikipage):
        """Mark a URL relationship as ended in MusicBrainz (page no longer exists)."""
        url_entity = {"type": "url", "gid": url_gid, "url": wikipage}
        other_entity = {"type": entitytype, "gid": entity_gid}
        entity0 = other_entity if (entitytype < "url") else url_entity
        entity1 = url_entity if (entitytype < "url") else other_entity
        wp.output("Removing non existing page %s" % (wikipage))
        mb_request_with_retry(
            self.client.edit_relationship,
            rel_id,
            entity0,
            entity1,
            link_type_id,
            {},
            {},
            {},
            True,
            self.removed_edit_note % (wikipage),
            False,
        )
        self._performed_edit()

    def process_result(self, result):
        """Process a single entity result from the database.

        Resolves the Wikipedia/Wikidata URL, checks skip conditions, and either:
        - Adds the MBID claim to Wikidata if not already present
        - Fixes a redirect URL in MusicBrainz
        - Ends a relationship for a dead Wikipedia page
        - Skips disambiguation/forbidden pages
        """
        entity_gid, url_gid, wikipage, rel_id, link_type_id, entity_name = result
        wp.output(
            "» {wp} https://musicbrainz.org/{entitytype}/{gid}".format(
                entitytype=self._current_entity_type.replace("_", "-"), wp=wikipage, gid=entity_gid
            )
        )
        try:
            itempage = get_wikidata_itempage_from_wikilink(wikipage)
        except wp.exceptions.SiteDefinitionError:
            wp.warning("{page} no supported family".format(page=wikipage))
            return
        except wp.exceptions.InvalidTitleError as e:
            wp.error("Bad or invalid title received while processing {page}".format(page=wikipage))
            wp.exception(e, tb=True)
            return
        except SkipPage as e:
            wp.warning("{page} is being skipped because: {reason}".format(page=wikipage, reason=e))
            return
        except IsRedirectPage as e:
            wp.output("{page} is a redirect".format(page=wikipage))
            if self.can_edit:
                self.fix_redirect(url_gid, e.old, e.new)
            return
        except ValueError as e:
            wp.output(e)
            return
        except PageGone:
            if self.can_edit:
                self.end_removed(rel_id, link_type_id, entity_gid, url_gid, self._current_entity_type, wikipage)
            return
        if itempage is None:
            wp.warning("There's no wikidata page for {mbid}".format(mbid=entity_gid))
            return

        if any(
            (key.lower() == self.property_id.lower() and claim.target == entity_gid)
            for key, claims in itempage.claims.items()
            for claim in claims
        ):
            wp.debug(
                "{page} already has property {pid} with value {mbid}".format(
                    page=wikipage, mbid=entity_gid, pid=self.property_id
                )
            )
            self.donefunc(entity_gid)
            return

        wp.output("{mbid} is not linked in Wikidata".format(mbid=entity_gid))
        self.add_mbid_claim_to_item(itempage, entity_gid, entity_name)


def entity_type_loop(bot, entitytype, limit):
    """Processes up to `limit` entities of type `entitytype`.

    :param bot Bot:
    :param entitytype str:
    :param limit int:
    """
    bot.current_entity_type = entitytype
    linkids = const.LINK_IDS[entitytype]

    wiki_entity_query = create_url_mbid_query(entitytype, linkids)
    already_processed_query = create_already_processed_query(entitytype)

    with (
        do_readonly_query(wiki_entity_query, limit) as all_results,
        do_readwrite_query(already_processed_query) as already_processed,
    ):
        already_processed_results = frozenset((row[0] for row in already_processed))

        results_to_process = [r for r in all_results if r[0] not in already_processed_results]

    if not results_to_process:
        wp.output("No more unprocessed entries of type {etype} in MB".format(etype=entitytype))
    else:
        wp.output("Processing {amount} {etype}s".format(amount=len(results_to_process), etype=entitytype))

    for r in results_to_process:
        bot.process_result(r)


def mainloop():
    """Main entry point: parse args, set up DB, and loop through entity types forever."""
    limit = None
    entities = sorted(const.PROPERTY_IDS.keys())

    for arg in wp.handle_args():
        if arg.startswith("-limit"):
            limit = int(arg[len("-limit:") :])
        elif arg.startswith("-entities"):
            entities = arg[len("-entities:") :].split(",")

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
        bot.update_rate_limits()
        sleep(settings.sleep_time_in_seconds)
