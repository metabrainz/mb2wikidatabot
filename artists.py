"""
This is a bot to automatically add MBIDs to Wikidata pages of artists.

Usage: python2 artists.py [options]

Command line options:

-dryrun:    Don't write anything on the server
-limit:x:   Only handle x artists
"""
from bot import common, const


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


if __name__ == '__main__':
    try:
        common.mainloop(const.ARTIST_MBID_PID, CREATE_PROCESSED_TABLE_QUERY,
                    MB_WIKI_ARTIST_QUERY, artist_done)
    except (KeyboardInterrupt, SystemExit):
        # Commit what's already been done and exit
        common.db.commit()
        raise
