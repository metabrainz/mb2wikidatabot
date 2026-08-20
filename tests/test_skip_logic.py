"""Tests for URL skip/redirect logic in bot.checks.

These tests import bot.checks directly — no pywikibot mocking needed
since the functions take all dependencies as explicit parameters.
"""

from unittest.mock import MagicMock

import pytest

from bot.checks import check_has_fragment, check_url_needs_to_be_skipped
from bot.exceptions import (
    HasFragment,
    InstanceOfForbidden,
    IsDisambigPage,
    IsRedirectPage,
    IsRedirectWithItemPage,
)


class FakeItemPage:
    pass


class NoPageError(Exception):
    pass


def _check(wikilink, page, item_page_cls=FakeItemPage):
    """Helper that calls check_url_needs_to_be_skipped with test defaults."""
    check_url_needs_to_be_skipped(
        wikilink,
        page,
        item_page_cls=item_page_cls,
        no_page_error=NoPageError,
        property_id_instance_of="P31",
        skip_instance_of_items=("Q4167410", "Q273057"),
    )


def _make_page(url="https://en.wikipedia.org/wiki/Test", is_redirect=False, is_disambig=False):
    page = MagicMock()
    page.full_url.return_value = url
    page.isRedirectPage.return_value = is_redirect
    page.isDisambig.return_value = is_disambig
    return page


def _make_item_page(url, claims=None):
    class MockItemPage(FakeItemPage):
        pass

    page = MockItemPage()
    page.full_url = lambda: url
    page.isRedirectPage = lambda: False
    page.isDisambig = lambda: False
    page.claims = claims or {}
    return page


class TestCheckHasFragment:
    def test_raises_on_fragment(self):
        with pytest.raises(HasFragment):
            check_has_fragment("https://en.wikipedia.org/wiki/Foo#section")

    def test_no_fragment_passes(self):
        check_has_fragment("https://en.wikipedia.org/wiki/Foo")

    def test_empty_fragment_passes(self):
        check_has_fragment("https://en.wikipedia.org/wiki/Foo#")


class TestCheckUrlNeedsToBeSkipped:
    def test_normal_page_passes(self):
        _check("https://en.wikipedia.org/wiki/Test", _make_page())

    def test_fragment_in_url_raises(self):
        page = _make_page(url="https://en.wikipedia.org/wiki/Foo#bar")
        with pytest.raises(HasFragment):
            _check("https://en.wikipedia.org/wiki/Foo#bar", page)

    def test_disambig_page_raises(self):
        page = _make_page(is_disambig=True)
        with pytest.raises(IsDisambigPage):
            _check("https://en.wikipedia.org/wiki/Test", page)

    def test_redirect_without_item_raises_redirect(self):
        page = _make_page(is_redirect=True)
        target = MagicMock()
        target.full_url.return_value = "https://en.wikipedia.org/wiki/Target"
        page.getRedirectTarget.return_value = target

        item_page_cls = MagicMock()
        item_page_cls.fromPage = MagicMock(side_effect=NoPageError("x"))

        with pytest.raises(IsRedirectPage) as exc_info:
            check_url_needs_to_be_skipped(
                "https://en.wikipedia.org/wiki/Old",
                page,
                item_page_cls=item_page_cls,
                no_page_error=NoPageError,
                property_id_instance_of="P31",
                skip_instance_of_items=("Q4167410",),
            )
        assert exc_info.value.new == "https://en.wikipedia.org/wiki/Target"

    def test_redirect_with_item_raises_skip(self):
        page = _make_page(is_redirect=True)

        item_page_cls = MagicMock()
        item_page_cls.fromPage = MagicMock(return_value=MagicMock())

        with pytest.raises(IsRedirectWithItemPage):
            check_url_needs_to_be_skipped(
                "https://en.wikipedia.org/wiki/Old",
                page,
                item_page_cls=item_page_cls,
                no_page_error=NoPageError,
                property_id_instance_of="P31",
                skip_instance_of_items=("Q4167410",),
            )

    def test_redirect_target_with_fragment_raises(self):
        page = _make_page(is_redirect=True)
        target = MagicMock()
        target.full_url.return_value = "https://en.wikipedia.org/wiki/Target#section"
        page.getRedirectTarget.return_value = target

        item_page_cls = MagicMock()
        item_page_cls.fromPage = MagicMock(side_effect=NoPageError("x"))

        with pytest.raises(HasFragment):
            check_url_needs_to_be_skipped(
                "https://en.wikipedia.org/wiki/Old",
                page,
                item_page_cls=item_page_cls,
                no_page_error=NoPageError,
                property_id_instance_of="P31",
                skip_instance_of_items=("Q4167410",),
            )

    def test_item_page_instance_of_disambiguation_raises(self):
        claim = MagicMock()
        claim.target.getID.return_value = "Q4167410"
        page = _make_item_page("https://www.wikidata.org/wiki/Q123", {"P31": [claim]})

        with pytest.raises(InstanceOfForbidden) as exc_info:
            _check("https://www.wikidata.org/wiki/Q123", page)
        assert exc_info.value.item_id == "Q4167410"

    def test_item_page_instance_of_discography_raises(self):
        claim = MagicMock()
        claim.target.getID.return_value = "Q273057"
        page = _make_item_page("https://www.wikidata.org/wiki/Q456", {"P31": [claim]})

        with pytest.raises(InstanceOfForbidden) as exc_info:
            _check("https://www.wikidata.org/wiki/Q456", page)
        assert exc_info.value.item_id == "Q273057"

    def test_item_page_allowed_instance_passes(self):
        claim = MagicMock()
        claim.target.getID.return_value = "Q5"
        page = _make_item_page("https://www.wikidata.org/wiki/Q789", {"P31": [claim]})

        _check("https://www.wikidata.org/wiki/Q789", page)

    def test_item_page_no_claims_passes(self):
        page = _make_item_page("https://www.wikidata.org/wiki/Q999")

        _check("https://www.wikidata.org/wiki/Q999", page)
