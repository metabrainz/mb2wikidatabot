"""URL validation and skip-logic checks.

These functions are pure logic with explicit dependencies passed in,
making them easy to test without mocking module-level state.
"""

from collections.abc import Callable
from typing import Any, Protocol
from urllib.parse import urlparse

from .exceptions import (
    HasFragment,
    InstanceOfForbidden,
    IsDisambigPage,
    IsRedirectPage,
    IsRedirectWithItemPage,
    PageGone,
)


class WikiPage(Protocol):
    """Protocol for pywikibot Page-like objects."""

    def full_url(self) -> str: ...
    def isRedirectPage(self) -> bool: ...
    def isDisambig(self) -> bool: ...
    def getRedirectTarget(self) -> "WikiPage": ...


class ItemPageClass(Protocol):
    """Protocol for the ItemPage class (used for isinstance and fromPage)."""

    def fromPage(self, page: Any) -> Any: ...
    def __instancecheck__(self, instance: Any) -> bool: ...  # noqa: N805


def check_has_fragment(url: str) -> None:
    """Check if `url` contains a fragment.

    This is most often the case for discography pages where a single album is
    only mentioned in a few paragraphs."""
    parsed_url = urlparse(url)
    if parsed_url.fragment:
        raise HasFragment(url)


def check_url_needs_to_be_skipped(
    wikilink: str,
    page: Any,
    *,
    item_page_cls: Any,
    no_page_error: type[Exception],
    property_id_instance_of: str,
    skip_instance_of_items: tuple[str, ...],
) -> None:
    """Check if `page` is a redirect or disambiguation page.

    Args:
        wikilink: The original URL string.
        page: A pywikibot Page or ItemPage object.
        item_page_cls: The ItemPage class (for isinstance check and fromPage).
        no_page_error: The NoPageError exception class.
        property_id_instance_of: The property ID for "instance of" (e.g. "P31").
        skip_instance_of_items: Tuple of item IDs to skip (e.g. disambiguation).
    """
    full_url = page.full_url()
    check_has_fragment(full_url)
    if page.isRedirectPage():
        try:
            item_page_cls.fromPage(page)
        except no_page_error:
            pass
        else:
            raise IsRedirectWithItemPage(full_url)
        page = page.getRedirectTarget()
        full_url = page.full_url()
        check_has_fragment(full_url)
        raise IsRedirectPage(wikilink, full_url)
    if page.isDisambig():
        raise IsDisambigPage(full_url)
    if isinstance(page, item_page_cls):
        for key, claims in page.claims.items():
            if key.lower() == property_id_instance_of.lower():
                for claim in claims:
                    item_id = claim.target.getID()
                    if item_id in skip_instance_of_items:
                        raise InstanceOfForbidden(full_url, item_id)


WIKI_PREFIX = "/wiki/"


def get_wikidata_itempage_from_wikilink(
    wikilink: str,
    *,
    wp: Any,
    wikidata_datasite: Any,
    check_skip: Callable[[str, Any], None],
) -> Any | None:
    """Given a link to a wikipedia/wikidata page, retrieve its Wikidata ItemPage.

    Args:
        wikilink: URL string.
        wp: The pywikibot module.
        wikidata_datasite: The Wikidata data repository site object.
        check_skip: A callable(wikilink, page) that raises on skip conditions.
    """
    parsed_url = urlparse(wikilink)
    if "wikipedia" in parsed_url.netloc:
        pagename = parsed_url.path.replace(WIKI_PREFIX, "")
        wikilanguage = parsed_url.netloc.split(".")[0]
        wikisite = wp.Site(wikilanguage, "wikipedia")
        wikipage = wp.Page(wikisite, pagename)
        check_skip(wikilink, wikipage)
        try:
            wikidatapage = wp.ItemPage.fromPage(wikipage)
        except wp.exceptions.NoPageError:
            wp.error("%s does not exist" % wikipage)
            return None
    elif "wikidata" in parsed_url.netloc:
        pagename = parsed_url.path.replace(WIKI_PREFIX, "")
        wikidatapage = wp.ItemPage(wikidata_datasite, pagename)
    else:
        raise ValueError("%s is not a link to a wikipedia page" % wikilink)
    try:
        wikidatapage.get(get_redirect=True)
    except wp.exceptions.NoPageError:
        wp.error("%s does not exist" % pagename)
        raise PageGone(pagename)
    check_skip(wikilink, wikidatapage)
    return wikidatapage
