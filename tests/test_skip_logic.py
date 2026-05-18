"""Tests for URL skip/redirect logic in bot.common."""

from unittest.mock import MagicMock

import pytest

from bot.common import (
    HasFragment,
    IsDisambigPage,
    IsRedirectPage,
    IsRedirectWithItemPage,
    InstanceOfForbidden,
    check_has_fragment,
    check_url_needs_to_be_skipped,
    wp,
)


def _make_page(url="https://en.wikipedia.org/wiki/Test", is_redirect=False, is_disambig=False):
    page = MagicMock()
    page.full_url.return_value = url
    page.isRedirectPage.return_value = is_redirect
    page.isDisambig.return_value = is_disambig
    return page


def _make_item_page(url, claims=None):
    """Create a page that passes isinstance(x, wp.ItemPage)."""

    class MockItemPage(wp.ItemPage):
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
        page = _make_page()
        check_url_needs_to_be_skipped("https://en.wikipedia.org/wiki/Test", page)

    def test_fragment_in_url_raises(self):
        page = _make_page(url="https://en.wikipedia.org/wiki/Foo#bar")
        with pytest.raises(HasFragment):
            check_url_needs_to_be_skipped("https://en.wikipedia.org/wiki/Foo#bar", page)

    def test_disambig_page_raises(self):
        page = _make_page(is_disambig=True)
        with pytest.raises(IsDisambigPage):
            check_url_needs_to_be_skipped("https://en.wikipedia.org/wiki/Test", page)

    def test_redirect_without_item_raises_redirect(self):
        """Redirect without its own wikidata item -> IsRedirectPage"""
        page = _make_page(is_redirect=True)
        target = MagicMock()
        target.full_url.return_value = "https://en.wikipedia.org/wiki/Target"
        page.getRedirectTarget.return_value = target

        orig = getattr(wp.ItemPage, "fromPage", None)
        wp.ItemPage.fromPage = MagicMock(side_effect=wp.exceptions.NoPageError("x"))
        try:
            with pytest.raises(IsRedirectPage) as exc_info:
                check_url_needs_to_be_skipped("https://en.wikipedia.org/wiki/Old", page)
            assert exc_info.value.new == "https://en.wikipedia.org/wiki/Target"
        finally:
            if orig is not None:
                wp.ItemPage.fromPage = orig

    def test_redirect_with_item_raises_skip(self):
        """Redirect with its own wikidata item -> IsRedirectWithItemPage"""
        page = _make_page(is_redirect=True)

        orig = getattr(wp.ItemPage, "fromPage", None)
        wp.ItemPage.fromPage = MagicMock(return_value=MagicMock())
        try:
            with pytest.raises(IsRedirectWithItemPage):
                check_url_needs_to_be_skipped("https://en.wikipedia.org/wiki/Old", page)
        finally:
            if orig is not None:
                wp.ItemPage.fromPage = orig

    def test_redirect_target_with_fragment_raises(self):
        """Redirect target has a fragment -> HasFragment"""
        page = _make_page(is_redirect=True)
        target = MagicMock()
        target.full_url.return_value = "https://en.wikipedia.org/wiki/Target#section"
        page.getRedirectTarget.return_value = target

        orig = getattr(wp.ItemPage, "fromPage", None)
        wp.ItemPage.fromPage = MagicMock(side_effect=wp.exceptions.NoPageError("x"))
        try:
            with pytest.raises(HasFragment):
                check_url_needs_to_be_skipped("https://en.wikipedia.org/wiki/Old", page)
        finally:
            if orig is not None:
                wp.ItemPage.fromPage = orig

    def test_item_page_instance_of_disambiguation_raises(self):
        """ItemPage instance of disambiguation -> InstanceOfForbidden"""
        claim = MagicMock()
        claim.target.getID.return_value = "Q4167410"
        page = _make_item_page("https://www.wikidata.org/wiki/Q123", {"P31": [claim]})

        with pytest.raises(InstanceOfForbidden) as exc_info:
            check_url_needs_to_be_skipped("https://www.wikidata.org/wiki/Q123", page)
        assert exc_info.value.item_id == "Q4167410"

    def test_item_page_instance_of_discography_raises(self):
        """ItemPage instance of discography -> InstanceOfForbidden"""
        claim = MagicMock()
        claim.target.getID.return_value = "Q273057"
        page = _make_item_page("https://www.wikidata.org/wiki/Q456", {"P31": [claim]})

        with pytest.raises(InstanceOfForbidden) as exc_info:
            check_url_needs_to_be_skipped("https://www.wikidata.org/wiki/Q456", page)
        assert exc_info.value.item_id == "Q273057"

    def test_item_page_allowed_instance_passes(self):
        """ItemPage with allowed P31 -> passes"""
        claim = MagicMock()
        claim.target.getID.return_value = "Q5"  # human
        page = _make_item_page("https://www.wikidata.org/wiki/Q789", {"P31": [claim]})

        check_url_needs_to_be_skipped("https://www.wikidata.org/wiki/Q789", page)

    def test_item_page_no_claims_passes(self):
        """ItemPage with no claims -> passes"""
        page = _make_item_page("https://www.wikidata.org/wiki/Q999")

        check_url_needs_to_be_skipped("https://www.wikidata.org/wiki/Q999", page)
