"""
This is a bot to automatically add MBIDs to Wikidata pages of artists.

Usage: python2 artists.py [options]

Command line options:

-dryrun:    Don't write anything on the server
-limit:x:   Only handle x artists
"""

import pywikibot as wp


from bot import common
from sys import exit


ARTIST_MBID_PID = 'P434'


MB_WIKI_ARTIST_LINK_ID = 179
MB_WIKI_ALBUM_LINK_ID = 89
MB_WIKI_LABEL_LINK_ID = 216
MB_WIKI_WORK_LINK_ID = 279

MB_WIKI_ARTIST_QUERY =\
"""
SELECT an.name, a.gid, url.url
FROM l_artist_url AS lau
JOIN link AS l
    ON lau.link=l.id
JOIN link_type AS lt
    ON lt.id=l.link_type
JOIN artist AS a
    ON entity0=a.id
JOIN artist_name AS an
    ON an.id=a.name
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
AND
    url.url LIKE 'http://en.%%'
ORDER BY a.id
LIMIT (%s) ;
"""

CREATE_PROCESSED_TABLE_QUERY =\
"""
CREATE TABLE IF NOT EXISTS bot_wikidata_artist_processed (
    gid uuid NOT NULL PRIMARY KEY,
    processed timestamp with time zone DEFAULT now()
);

"""


def artist_done(mbid):
    common.db.cursor().execute("INSERT INTO bot_wikidata_artist_processed (GID) VALUES (%s)", (mbid, ))


def add_mbid_claim_to_item(pid, item, mbid, simulate=False):
    """
    Adds a claim with pid `pid` with value `mbid` to `item`

    :type pid: str
    :type mbid: str
    :type item: pywikibot.ItemPage
    """
    claim = wp.Claim(common.WIKIDATA, pid)
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
        artist_done(mbid)


def add_artist_mbid_claim(item, mbid, simulate):
    """
    Adds an MBID property to `item`

    :type item: pywikibot.ItemPage
    :type mbid: str
    """
    add_mbid_claim_to_item(ARTIST_MBID_PID, item, mbid, simulate)


def main():
    simulate = False
    limit = 100

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

    for name, mbid, wikipage in results:
        itempage = common.get_wikidata_itempage_from_wikilink(wikipage)
        if itempage is None:
            wp.output(u"There's no wikidata page for {name}".format(name=name))
            continue

        if any(key.lower() == ARTIST_MBID_PID.lower() for key in itempage.claims.keys()):
            wp.output(u"{name} is already has property {pid}".format(name=name,
                                                                     pid=ARTIST_MBID_PID))
            artist_done(mbid)
            continue

        wp.output("The MBID for {name} is {mbid} and does not exist in Wikidata".format(
                    name=name, mbid=mbid))
        add_artist_mbid_claim(itempage, mbid, simulate)

    common.db.commit()

if __name__ == '__main__':
    main()
