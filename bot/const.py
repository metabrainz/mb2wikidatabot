import pywikibot as wp


WIKIDATA = wp.Site('wikidata', 'wikidata')
WIKIDATA_DATASITE = WIKIDATA.data_repository()


PROPERTY_IDS = {
    "area": "P982",
    "artist": "P434",
    "label": "P966",
    "place": "P1004",
    "release_group": "P436",
    "work": "P435",
}


LINK_IDS = {
    "area": 355,
    "artist": 179,
    "label": 216,
    "place": 595,
    "release_group": 89,
    "work": 279,
}


MUSICBRAINZ_WIKIDATAPAGE = wp.ItemPage(WIKIDATA_DATASITE, "Q14005")
MUSICBRAINZ_CLAIM = wp.Claim(WIKIDATA_DATASITE, "P248")

GENERIC_URL_MBID_QUERY =\
    """
    SELECT {etype}.gid, url.url
    FROM l_{etype}_url
    JOIN link AS l
        ON l_{etype}_url.link=l.id
    JOIN link_type AS lt
        ON lt.id=l.link_type
    JOIN {etype}
        ON entity0={etype}.id
    JOIN url
        ON l_{etype}_url.entity1=url.id
    LEFT JOIN bot_wikidata_{etype}_processed AS bwep
        ON {etype}.gid=bwep.gid
    WHERE
        lt.id={linkid}
    AND
        l_{etype}_url.edits_pending=0
    AND
        bwep.gid is NULL
    LIMIT %s;
    """

GENERIC_DONE_QUERY =\
    """
    INSERT INTO bot_wikidata_{etype}_processed (GID)
        SELECT (%(mbid)s)
        WHERE NOT EXISTS (
            SELECT 1
            FROM bot_wikidata_{etype}_processed
            WHERE gid = (%(mbid)s)
    );
    """

GENERIC_CREATE_PROCESSED_TABLE_QUERY =\
    """
    CREATE TABLE bot_wikidata_{etype}_processed (
        gid uuid NOT NULL PRIMARY KEY,
        processed timestamp with time zone DEFAULT now()
    );

    """

MB_WIKI_WORKS_QUERY =\
    """
    SELECT w.gid, url.url
    FROM l_url_work AS lwu
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
