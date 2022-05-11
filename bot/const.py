import pywikibot as wp


from collections import defaultdict, namedtuple


WIKIDATA = wp.Site('wikidata', 'wikidata')
WIKIDATA_DATASITE = WIKIDATA.data_repository()


LinkIDsTuple = namedtuple("LinkIDs", "wikipedia wikidata")


# The property id and item id for "is a disambiguation page" claims
PROPERTY_ID_INSTANCE_OF = u"P31"
SKIP_INSTANCE_OF_ITEMS = ("Q4167410",  # disambiguation page
                          "Q273057",  # discography
                          )


PROPERTY_IDS = {
    "area": "P982",
    "artist": "P434",
    "instrument": "P1330",
    "label": "P966",
    "place": "P1004",
    "release_group": "P436",
    "series": "P1407",
    # "work": "P435",
}


LINK_IDS = {
    "area": LinkIDsTuple(355, 358),
    "artist": LinkIDsTuple(179, 352),
    "instrument": LinkIDsTuple(731, 733),
    "label": LinkIDsTuple(216, 354),
    "place": LinkIDsTuple(595, 594),
    "release_group": LinkIDsTuple(89, 353),
    "series": LinkIDsTuple(744, 749),
    # "work": LinkIDsTuple(279, 351),
}


MUSICBRAINZ_WIKIDATAPAGE = wp.ItemPage(WIKIDATA_DATASITE, "Q14005")
MUSICBRAINZ_CLAIM = wp.Claim(WIKIDATA_DATASITE, "P248")
RETRIEVED_CLAIM = wp.Claim(WIKIDATA_DATASITE, "P813")

GENERIC_URL_MBID_QUERY =\
    """
    SELECT {etype}.gid, url.gid, url.url, l_table.id, lt.id
    FROM l_{etype}_url l_table
    JOIN link AS l
        ON l_table.link=l.id
    JOIN link_type AS lt
        ON lt.id=l.link_type
    JOIN {etype}
        ON entity0={etype}.id
    JOIN url
        ON l_table.entity1=url.id
    WHERE
        lt.id IN ({wikipedia_linkid}, {wikidata_linkid})
    AND
        l_table.edits_pending=0
    AND
        url.edits_pending=0
    AND
        l.ended=FALSE
    LIMIT %s;
    """

GENERIC_ALREADY_PROCESSED_QUERY =\
    """
    SELECT gid
    FROM bot_wikidata_{etype}_processed;
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
    CREATE TABLE IF NOT EXISTS bot_wikidata_{etype}_processed (
        gid uuid NOT NULL PRIMARY KEY,
        processed timestamp with time zone DEFAULT now()
    );

    """

QUERIES = defaultdict(lambda: None,
    {
        'work':
        """
        SELECT w.gid, url.gid, url.url, lwu.id, lt.id
        FROM l_url_work AS lwu
        JOIN link AS l
            ON lwu.link=l.id
        JOIN link_type AS lt
            ON lt.id=l.link_type
        JOIN work AS w
            ON entity1=w.id
        JOIN url
            ON lwu.entity0=url.id
        WHERE
            lt.id IN (279, 351)
        AND
            lwu.edits_pending=0
        AND
            url.edits_pending=0
        AND
            l.ended=FALSE
        LIMIT %s;

        """,
        'area':
        """
        SELECT area.gid, url.gid, url.url, l_area_url.id, lt.id
        FROM l_area_url
        JOIN link AS l
            ON l_area_url.link=l.id
        JOIN link_type AS lt
            ON lt.id=l.link_type
        JOIN area
            ON entity0=area.id
        JOIN url
            ON l_area_url.entity1=url.id
        WHERE
            lt.id IN (355, 358)
        AND
            l_area_url.edits_pending=0
        AND
            url.edits_pending=0
        AND
            l.ended=FALSE
        AND
        area.id IN (
            SELECT area
            FROM place
            UNION ALL
            SELECT area
            FROM label
            UNION ALL
            SELECT area
            FROM artist
            UNION ALL
            SELECT begin_area
            FROM artist
            UNION ALL
            SELECT end_area
            FROM artist
            UNION ALL
            SELECT area
            FROM country_area
                JOIN release_country
                ON release_country.country = country_area.area
            UNION ALL
            SELECT entity0
            FROM l_area_recording
            UNION ALL
            SELECT entity0
            FROM l_area_release
            UNION ALL
            SELECT entity0
            FROM l_area_work
        )
        LIMIT %s;
        """
    }
)
