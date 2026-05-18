"""Tests for get_wikidata_itempage_from_wikilink URL routing."""

from unittest.mock import MagicMock, patch

import pytest

from bot.common import (
    PageGone,
    get_wikidata_itempage_from_wikilink,
    wp,
)


class TestGetWikidataItempageFromWikilink:
    def test_invalid_url_raises_valueerror(self):
        with pytest.raises(ValueError, match="not a link to a wikipedia page"):
            get_wikidata_itempage_from_wikilink("https://example.com/wiki/Foo")

    @patch("bot.common.wp.Page")
    @patch("bot.common.wp.Site")
    @patch("bot.common.check_url_needs_to_be_skipped")
    def test_wikipedia_url_extracts_language_and_page(self, mock_skip, mock_site, mock_page):
        mock_wiki_page = MagicMock()
        mock_page.return_value = mock_wiki_page
        mock_item = MagicMock()
        mock_item.get = MagicMock()
        wp.ItemPage.fromPage = MagicMock(return_value=mock_item)

        result = get_wikidata_itempage_from_wikilink("https://en.wikipedia.org/wiki/The_Beatles")

        mock_site.assert_called_once_with("en", "wikipedia")
        mock_page.assert_called_once_with(mock_site.return_value, "The_Beatles")
        assert result == mock_item

    @patch("bot.common.wp.Page")
    @patch("bot.common.wp.Site")
    @patch("bot.common.check_url_needs_to_be_skipped")
    def test_japanese_wikipedia_url(self, mock_skip, mock_site, mock_page):
        mock_wiki_page = MagicMock()
        mock_page.return_value = mock_wiki_page
        mock_item = MagicMock()
        mock_item.get = MagicMock()
        wp.ItemPage.fromPage = MagicMock(return_value=mock_item)

        get_wikidata_itempage_from_wikilink("https://ja.wikipedia.org/wiki/%E6%9D%B1%E4%BA%AC")

        mock_site.assert_called_once_with("ja", "wikipedia")

    @patch("bot.common.wp.Page")
    @patch("bot.common.wp.Site")
    @patch("bot.common.check_url_needs_to_be_skipped")
    def test_wikipedia_page_not_found_returns_none(self, mock_skip, mock_site, mock_page):
        wp.ItemPage.fromPage = MagicMock(side_effect=wp.exceptions.NoPageError("x"))

        result = get_wikidata_itempage_from_wikilink("https://en.wikipedia.org/wiki/Nonexistent")

        assert result is None

    @patch("bot.common.check_url_needs_to_be_skipped")
    @patch("bot.common.wp.ItemPage")
    def test_wikidata_url_creates_item_directly(self, mock_item_cls, mock_skip):
        mock_item = MagicMock()
        mock_item.get = MagicMock()
        mock_item_cls.return_value = mock_item

        result = get_wikidata_itempage_from_wikilink("https://www.wikidata.org/wiki/Q42")

        mock_item_cls.assert_called_once()
        args = mock_item_cls.call_args[0]
        assert args[1] == "Q42"

    @patch("bot.common.check_url_needs_to_be_skipped")
    @patch("bot.common.wp.ItemPage")
    def test_wikidata_page_gone_raises(self, mock_item_cls, mock_skip):
        mock_item = MagicMock()
        mock_item.get.side_effect = wp.exceptions.NoPageError("x")
        mock_item_cls.return_value = mock_item

        with pytest.raises(PageGone):
            get_wikidata_itempage_from_wikilink("https://www.wikidata.org/wiki/Q99999999")
