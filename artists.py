"""
This is a bot to automatically add MBIDs to Wikidata pages of artists.

Usage: python2 artists.py [options]

Command line options:

-dryrun:    Don't write anything on the server
-limit:x:   Only handle x artists
"""

import pywikibot as wp


from bot import common, const
from sys import exit


MB_WIKI_ARTIST_QUERY =\
"""
SELECT a.gid, url.url
FROM l_artist_url AS lau
JOIN link AS l
    ON lau.link=l.id
JOIN link_type AS lt
    ON lt.id=l.link_type
JOIN artist AS a
    ON entity0=a.id
JOIN url
    ON lau.entity1=url.id
LEFT JOIN bot_wikidata_artist_processed AS bwap
    ON a.gid=bwap.gid
WHERE
    lt.id=179
AND
    lau.edits_pending=0
AND
    bwap.gid is NULL
LIMIT %s;
"""

CREATE_PROCESSED_TABLE_QUERY =\
"""
CREATE TABLE IF NOT EXISTS bot_wikidata_artist_processed (
    gid uuid NOT NULL PRIMARY KEY,
    processed timestamp with time zone DEFAULT now()
);

"""

ARTIST_DONE_QUERY = \
"""
INSERT INTO bot_wikidata_artist_processed (GID)
    SELECT (%(mbid)s)
    WHERE NOT EXISTS (
        SELECT 1
        FROM bot_wikidata_artist_processed
        WHERE gid = (%(mbid)s)
);
"""

def artist_done(mbid):
    common.db.cursor().execute(ARTIST_DONE_QUERY, {'mbid': mbid})


def add_artist_mbid_claim(item, mbid, simulate):
    """
    Adds an MBID property to `item`

    :type item: pywikibot.ItemPage
    :type mbid: str
    """
    common.add_mbid_claim_to_item(const.ARTIST_MBID_PID, item, mbid, artist_done, simulate)


def main():
    simulate = False
    limit = None

    for arg in wp.handleArgs():
        if arg =='-dryrun':
            simulate = True
        elif arg.startswith('-limit'):
            limit = int(arg[len('-limit:'):])

    common.WIKIDATA.login()
    common.setup_db(CREATE_PROCESSED_TABLE_QUERY)
    results = common.get_entities_with_wikilinks(MB_WIKI_ARTIST_QUERY, limit)

    if results.rowcount == 0:
        wp.output("No more unprocessed entries in MB")
        exit(0)

    for index, (mbid, wikipage) in enumerate(results):
        try:
            itempage = common.get_wikidata_itempage_from_wikilink(wikipage)
        except wp.NoSuchSite:
            wp.output("{page}: no supported family".format(page=wikipage))
            continue
        if itempage is None:
            wp.output(u"There's no wikidata page for {mbid}".format(mbid=mbid))
            continue

        if any(key.lower() == const.ARTIST_MBID_PID.lower() for key in itempage.claims.keys()):
            wp.output(u"{mbid} already has property {pid}".format(mbid=mbid,
                                                                     pid=const.ARTIST_MBID_PID))
            artist_done(mbid)
            continue

        wp.output("{mbid} is not linked in in Wikidata".format(
                    mbid=mbid))
        add_artist_mbid_claim(itempage, mbid, simulate)
        if index % 100 == 0:
            common.db.commit()

    common.db.commit()

if __name__ == '__main__':
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        # Commit what's already been done and exit
        common.db.commit()
        raise
