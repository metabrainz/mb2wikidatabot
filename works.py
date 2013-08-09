"""
This is a bot to automatically add MBIDs to Wikidata pages of works.

Usage: python2 works.py [options]

Command line options:

-createtable: Create the table storing the processed MBIDs
-dryrun:    Don't write anything on the server
-limit:x:   Only handle x works
"""
from bot import common, const


MB_WIKI_WORKS_QUERY =\
"""
SELECT w.gid, url.url
FROM l_work_url AS lwu
JOIN link AS l
    ON lwu.link=l.id
JOIN link_type AS lt
    ON lt.id=l.link_type
JOIN work AS w
    ON entity1=w.id
JOIN url
    ON lwu.entity0=url.id
LEFT JOIN bot_wikidata_work_processed AS bwwp
    ON w.gid=bwwp.gid
WHERE
    lt.id=279
AND
    lwu.edits_pending=0
AND
    bwwp.gid is NULL
LIMIT %s;
"""

CREATE_PROCESSED_TABLE_QUERY =\
"""
CREATE TABLE bot_wikidata_work_processed (
    gid uuid NOT NULL PRIMARY KEY,
    processed timestamp with time zone DEFAULT now()
);

"""

ARTIST_DONE_QUERY = \
"""
INSERT INTO bot_wikidata_work_processed (GID)
    SELECT (%(mbid)s)
    WHERE NOT EXISTS (
        SELECT 1
        FROM bot_wikidata_artist_processed
        WHERE gid = (%(mbid)s)
);
"""


def work_done(mbid):
    common.db.cursor().execute(ARTIST_DONE_QUERY, {'mbid': mbid})


if __name__ == '__main__':
    common.mainloop(const.WORK_MBID_PID, CREATE_PROCESSED_TABLE_QUERY,
                MB_WIKI_WORK_QUERY, work_done)
