"""Query builder functions for the wikidata bot.

Pure string formatting — no database or network dependencies.
"""


def create_url_mbid_query(entitytype, linkids, *, generic_query, custom_queries):
    """Creates a specific query for `entitytype` and `linkids`.

    Args:
        entitytype: The entity type string (e.g. "artist").
        linkids: A LinkIDsTuple with .wikipedia and .wikidata attributes.
        generic_query: The generic query template string.
        custom_queries: A dict mapping entity types to custom queries (or None).
    """
    custom = custom_queries[entitytype]
    if custom is not None:
        return custom
    return generic_query.format(etype=entitytype, wikipedia_linkid=linkids.wikipedia, wikidata_linkid=linkids.wikidata)


def create_already_processed_query(entitytype, *, template):
    """Creates a specific query for `entitytype` from a template."""
    return template.format(etype=entitytype)


def create_processed_table_query(entitytype, *, template):
    """Creates a CREATE TABLE query for `entitytype` from a template."""
    return template.format(etype=entitytype)
