"""Tests for bot.queries and bot.exceptions."""

import pytest

from bot.exceptions import (
    HasFragment,
    InstanceOfForbidden,
    IsDisambigPage,
    IsRedirectPage,
    IsRedirectWithItemPage,
    PageGone,
)
from bot.queries import (
    create_already_processed_query,
    create_processed_table_query,
    create_url_mbid_query,
)


class TestExceptionStrMethods:
    def test_has_fragment_str(self):
        assert "has a fragment" in str(HasFragment("http://x.org#foo"))

    def test_is_disambig_str(self):
        assert "disambiguation" in str(IsDisambigPage("http://x.org"))

    def test_instance_of_forbidden_str(self):
        e = InstanceOfForbidden("http://x.org", "Q123")
        assert "Q123" in str(e)
        assert "instance of" in str(e)

    def test_is_redirect_with_item_str(self):
        assert "redirect" in str(IsRedirectWithItemPage("http://x.org"))

    def test_is_redirect_page_str(self):
        e = IsRedirectPage("http://old", "http://new")
        assert "http://old" in str(e)
        assert "http://new" in str(e)

    def test_page_gone_str(self):
        assert "no more" in str(PageGone("SomePage"))


class TestQueryBuilders:
    def test_create_url_mbid_query_uses_custom(self):
        custom_queries = {"artist": "SELECT custom", "work": None}
        result = create_url_mbid_query("artist", None, generic_query="generic", custom_queries=custom_queries)
        assert result == "SELECT custom"

    def test_create_url_mbid_query_uses_generic(self):
        class FakeLinkIDs:
            wikipedia = 179
            wikidata = 352

        custom_queries = {"artist": None}
        result = create_url_mbid_query(
            "artist", FakeLinkIDs(), generic_query="SELECT {etype} {wikipedia_linkid} {wikidata_linkid}", custom_queries=custom_queries
        )
        assert "artist" in result
        assert "179" in result
        assert "352" in result

    def test_create_already_processed_query(self):
        result = create_already_processed_query("artist", template="SELECT FROM {etype}_processed")
        assert result == "SELECT FROM artist_processed"

    def test_create_processed_table_query(self):
        result = create_processed_table_query("label", template="CREATE TABLE {etype}_done")
        assert result == "CREATE TABLE label_done"
