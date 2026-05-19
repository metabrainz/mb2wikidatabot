"""Tests for get_wikidata_itempage_from_wikilink URL routing.

Imports bot.checks directly — no pywikibot mocking needed.
"""

from unittest.mock import MagicMock

import pytest

from bot.checks import get_wikidata_itempage_from_wikilink
from bot.exceptions import PageGone


class NoPageError(Exception):
    pass


def _make_wp():
    """Create a minimal mock wp module with the needed attributes."""
    wp = MagicMock()
    wp.exceptions.NoPageError = NoPageError
    return wp


class TestGetWikidataItempageFromWikilink:
    def test_invalid_url_raises_valueerror(self):
        wp = _make_wp()
        with pytest.raises(ValueError, match="not a link to a wikipedia page"):
            get_wikidata_itempage_from_wikilink(
                "https://example.com/wiki/Foo",
                wp=wp,
                wikidata_datasite=MagicMock(),
                check_skip=MagicMock(),
            )

    def test_wikipedia_url_extracts_language_and_page(self):
        wp = _make_wp()
        mock_item = MagicMock()
        mock_item.get = MagicMock()
        wp.ItemPage.fromPage.return_value = mock_item

        result = get_wikidata_itempage_from_wikilink(
            "https://en.wikipedia.org/wiki/The_Beatles",
            wp=wp,
            wikidata_datasite=MagicMock(),
            check_skip=MagicMock(),
        )

        wp.Site.assert_called_once_with("en", "wikipedia")
        wp.Page.assert_called_once_with(wp.Site.return_value, "The_Beatles")
        assert result == mock_item

    def test_japanese_wikipedia_url(self):
        wp = _make_wp()
        mock_item = MagicMock()
        mock_item.get = MagicMock()
        wp.ItemPage.fromPage.return_value = mock_item

        get_wikidata_itempage_from_wikilink(
            "https://ja.wikipedia.org/wiki/%E6%9D%B1%E4%BA%AC",
            wp=wp,
            wikidata_datasite=MagicMock(),
            check_skip=MagicMock(),
        )

        wp.Site.assert_called_once_with("ja", "wikipedia")

    def test_wikipedia_page_not_found_returns_none(self):
        wp = _make_wp()
        wp.ItemPage.fromPage.side_effect = NoPageError("x")

        result = get_wikidata_itempage_from_wikilink(
            "https://en.wikipedia.org/wiki/Nonexistent",
            wp=wp,
            wikidata_datasite=MagicMock(),
            check_skip=MagicMock(),
        )

        assert result is None

    def test_wikidata_url_creates_item_directly(self):
        wp = _make_wp()
        mock_item = MagicMock()
        mock_item.get = MagicMock()
        wp.ItemPage.return_value = mock_item
        datasite = MagicMock()

        result = get_wikidata_itempage_from_wikilink(
            "https://www.wikidata.org/wiki/Q42",
            wp=wp,
            wikidata_datasite=datasite,
            check_skip=MagicMock(),
        )

        wp.ItemPage.assert_called_once_with(datasite, "Q42")
        assert result == mock_item

    def test_wikidata_page_gone_raises(self):
        wp = _make_wp()
        mock_item = MagicMock()
        mock_item.get.side_effect = NoPageError("x")
        wp.ItemPage.return_value = mock_item

        with pytest.raises(PageGone):
            get_wikidata_itempage_from_wikilink(
                "https://www.wikidata.org/wiki/Q99999999",
                wp=wp,
                wikidata_datasite=MagicMock(),
                check_skip=MagicMock(),
            )
