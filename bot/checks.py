"""URL validation and skip-logic checks.

These functions are pure logic with explicit dependencies passed in,
making them easy to test without mocking module-level state.
"""

from urllib.parse import urlparse

from .exceptions import (
    HasFragment,
    InstanceOfForbidden,
    IsDisambigPage,
    IsRedirectPage,
    IsRedirectWithItemPage,
)


def check_has_fragment(url):
    """Check if `url` contains a fragment.

    This is most often the case for discography pages where a single album is
    only mentioned in a few paragraphs."""
    parsed_url = urlparse(url)
    if parsed_url.fragment:
        raise HasFragment(url)


def check_url_needs_to_be_skipped(wikilink, page, *, item_page_cls, no_page_error, property_id_instance_of, skip_instance_of_items):
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
