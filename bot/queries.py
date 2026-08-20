"""Query builder functions for the wikidata bot.

Pure string formatting — no database or network dependencies.
"""

from typing import Protocol


class LinkIDs(Protocol):
    wikipedia: int | None
    wikidata: int


def create_url_mbid_query(
    entitytype: str, linkids: LinkIDs, *, generic_query: str, custom_queries: dict[str, str | None]
) -> str:
    """Creates a specific query for `entitytype` and `linkids`.

    Note: entitytype is interpolated into SQL via str.format(). This is safe
    because entity types come from the hardcoded PROPERTY_IDS dict keys, never
    from user input.

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


def create_already_processed_query(entitytype: str, *, template: str) -> str:
    """Creates a specific query for `entitytype` from a template."""
    return template.format(etype=entitytype)


def create_processed_table_query(entitytype: str, *, template: str) -> str:
    """Creates a CREATE TABLE query for `entitytype` from a template."""
    return template.format(etype=entitytype)
