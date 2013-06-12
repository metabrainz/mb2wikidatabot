"""
This is a bot to automatically add MBIDs to Wikidata pages of release groups.

Usage: python2 rg.py [options]

Command line options:

-createtable: Create the table storing the processed MBIDs
-dryrun:    Don't write anything on the server
-limit:x:   Only handle x release groups
"""
from bot import common, const


MB_WIKI_RG_QUERY =\
"""
SELECT rg.gid, url.url
FROM l_release_group_url AS lrgu
JOIN link AS l
    ON lrgu.link=l.id
JOIN link_type AS lt
    ON lt.id=l.link_type
JOIN release_group AS rg
    ON entity0=rg.id
JOIN url
    ON lrgu.entity1=url.id
LEFT JOIN bot_wikidata_rg_processed AS bwrgp
    ON rg.gid=bwrgp.gid
WHERE
    lt.id=89
AND
    lrgu.edits_pending=0
AND
    bwrgp.gid is NULL
LIMIT %s;
"""

CREATE_PROCESSED_TABLE_QUERY =\
"""
CREATE TABLE bot_wikidata_rg_processed (
    gid uuid NOT NULL PRIMARY KEY,
    processed timestamp with time zone DEFAULT now()
);

"""

RG_DONE_QUERY = \
"""
INSERT INTO bot_wikidata_rg_processed (GID)
    SELECT (%(mbid)s)
    WHERE NOT EXISTS (
        SELECT 1
        FROM bot_wikidata_rg_processed
        WHERE gid = (%(mbid)s)
);
"""


def rg_done(mbid):
    common.db.cursor().execute(RG_DONE_QUERY, {'mbid': mbid})


if __name__ == '__main__':
    common.mainloop(const.RELEASE_GROUP_MBID_PID, CREATE_PROCESSED_TABLE_QUERY,
                MB_WIKI_RG_QUERY, rg_done)
