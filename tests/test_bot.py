"""Tests for Bot.process_result and entity_type_loop in bot.common."""

from unittest.mock import MagicMock, patch

import pytest

from bot.common import Bot, entity_type_loop, wp


@pytest.fixture
def bot():
    """Create a Bot instance with mocked dependencies."""
    with patch("bot.common.editing", None):
        b = Bot()
    b.client = MagicMock()
    b.number_of_allowed_edits = 10
    b.current_entity_type = "artist"
    b.donefunc = MagicMock()
    return b


class TestBotCanEdit:
    def test_can_edit_true(self, bot):
        assert bot.can_edit is True

    def test_can_edit_false_no_client(self, bot):
        bot.client = None
        assert bot.can_edit is False

    def test_can_edit_false_no_edits_left(self, bot):
        bot.number_of_allowed_edits = 0
        assert bot.can_edit is False

    def test_can_edit_false_simulate(self, bot):
        wp.config.simulate = True
        try:
            assert bot.can_edit is False
        finally:
            wp.config.simulate = False


class TestBotPerformedEdit:
    @patch("bot.common.sleep")
    def test_decrements_edits(self, mock_sleep, bot):
        bot.number_of_allowed_edits = 5
        bot._performed_edit()
        assert bot.number_of_allowed_edits == 4

    @patch("bot.common.sleep")
    def test_sleeps_after_edit(self, mock_sleep, bot):
        from bot import settings

        bot._performed_edit()
        mock_sleep.assert_called_once_with(settings.mb_edit_delay)

    @patch("bot.common.sleep")
    def test_disables_editing_at_zero(self, mock_sleep, bot):
        bot.number_of_allowed_edits = 1
        bot._performed_edit()
        assert bot.number_of_allowed_edits == 0
        assert bot.can_edit is False


class TestBotUpdateRateLimits:
    def test_sets_edits_from_client(self, bot):
        bot.client.edits_left.return_value = 42
        bot.update_rate_limits()
        assert bot.number_of_allowed_edits == 42

    def test_falls_back_to_zero_on_error(self, bot):
        bot.client.edits_left.side_effect = Exception("connection refused")
        bot.update_rate_limits()
        assert bot.number_of_allowed_edits == 0

    def test_no_client_sets_zero(self, bot):
        bot.client = None
        bot.update_rate_limits()
        assert bot.number_of_allowed_edits == 0


class TestBotFixRedirect:
    @patch("bot.common.sleep")
    @patch("bot.common.mb_request_with_retry")
    def test_calls_edit_url_with_retry(self, mock_retry, mock_sleep, bot):
        bot.fix_redirect("gid-1", "http://old", "http://new")
        mock_retry.assert_called_once_with(
            bot.client.edit_url, "gid-1", "http://old", "http://new", "http://old is only a redirect to http://new"
        )

    @patch("bot.common.sleep")
    @patch("bot.common.mb_request_with_retry")
    def test_decrements_edits_after_fix(self, mock_retry, mock_sleep, bot):
        bot.number_of_allowed_edits = 5
        bot.fix_redirect("gid-1", "http://old", "http://new")
        assert bot.number_of_allowed_edits == 4


class TestBotEndRemoved:
    @patch("bot.common.sleep")
    @patch("bot.common.mb_request_with_retry")
    def test_calls_edit_relationship_with_retry(self, mock_retry, mock_sleep, bot):
        bot.end_removed("rel-1", "lt-1", "entity-gid", "url-gid", "artist", "http://gone")
        mock_retry.assert_called_once()
        args = mock_retry.call_args[0]
        assert args[0] == bot.client.edit_relationship
        # ended=True is the 8th positional arg to edit_relationship
        assert args[8] is True

    @patch("bot.common.sleep")
    @patch("bot.common.mb_request_with_retry")
    def test_decrements_edits_after_end(self, mock_retry, mock_sleep, bot):
        bot.number_of_allowed_edits = 3
        bot.end_removed("rel-1", "lt-1", "entity-gid", "url-gid", "artist", "http://gone")
        assert bot.number_of_allowed_edits == 2


class TestBotProcessResult:
    def _make_result(
        self,
        entity_gid="abc-123",
        url_gid="url-456",
        wikipage="https://www.wikidata.org/wiki/Q42",
        rel_id="1",
        link_type_id="352",
        entity_name="Test",
    ):
        return (entity_gid, url_gid, wikipage, rel_id, link_type_id, entity_name)

    @patch("bot.common.get_wikidata_itempage_from_wikilink")
    def test_skips_when_no_itempage(self, mock_get, bot):
        mock_get.return_value = None
        bot.process_result(self._make_result())
        bot.donefunc.assert_not_called()

    @patch("bot.common.get_wikidata_itempage_from_wikilink")
    def test_marks_done_when_already_has_claim(self, mock_get, bot):
        itempage = MagicMock()
        itempage.claims = {"P434": [MagicMock(target="abc-123")]}
        mock_get.return_value = itempage

        bot.process_result(self._make_result())
        bot.donefunc.assert_called_once_with("abc-123")

    @patch("bot.common.get_wikidata_itempage_from_wikilink")
    def test_adds_claim_when_not_linked(self, mock_get, bot):
        itempage = MagicMock()
        itempage.claims = {}
        mock_get.return_value = itempage

        with patch.object(bot, "add_mbid_claim_to_item") as mock_add:
            bot.process_result(self._make_result())
            mock_add.assert_called_once_with(itempage, "abc-123", "Test")

    @patch("bot.common.get_wikidata_itempage_from_wikilink")
    def test_fixes_redirect_when_can_edit(self, mock_get, bot):
        from bot.exceptions import IsRedirectPage

        mock_get.side_effect = IsRedirectPage("http://old", "http://new")

        with patch.object(bot, "fix_redirect") as mock_fix:
            bot.process_result(self._make_result())
            mock_fix.assert_called_once_with("url-456", "http://old", "http://new")

    @patch("bot.common.get_wikidata_itempage_from_wikilink")
    def test_skips_redirect_when_cannot_edit(self, mock_get, bot):
        from bot.exceptions import IsRedirectPage

        mock_get.side_effect = IsRedirectPage("http://old", "http://new")
        bot.client = None  # can_edit = False

        with patch.object(bot, "fix_redirect") as mock_fix:
            bot.process_result(self._make_result())
            mock_fix.assert_not_called()

    @patch("bot.common.get_wikidata_itempage_from_wikilink")
    def test_ends_removed_when_page_gone(self, mock_get, bot):
        from bot.exceptions import PageGone

        mock_get.side_effect = PageGone("SomePage")

        with patch.object(bot, "end_removed") as mock_end:
            bot.process_result(self._make_result())
            mock_end.assert_called_once()

    @patch("bot.common.get_wikidata_itempage_from_wikilink")
    def test_skips_page_on_skip_exception(self, mock_get, bot):
        from bot.exceptions import IsDisambigPage

        mock_get.side_effect = IsDisambigPage("http://x.org")
        # Should not raise
        bot.process_result(self._make_result())
        bot.donefunc.assert_not_called()

    @patch("bot.common.get_wikidata_itempage_from_wikilink")
    def test_handles_valueerror(self, mock_get, bot):
        mock_get.side_effect = ValueError("bad url")
        bot.process_result(self._make_result())
        bot.donefunc.assert_not_called()


class TestEntityTypeLoop:
    @patch("bot.common.do_readwrite_query")
    @patch("bot.common.do_readonly_query")
    def test_filters_already_processed(self, mock_ro, mock_rw, bot):
        # Simulate 3 results, 1 already processed
        mock_ro.return_value.__enter__ = MagicMock(
            return_value=[
                ("gid-1", "u1", "http://a", "1", "1", "A"),
                ("gid-2", "u2", "http://b", "2", "2", "B"),
                ("gid-3", "u3", "http://c", "3", "3", "C"),
            ]
        )
        mock_ro.return_value.__exit__ = MagicMock(return_value=False)
        mock_rw.return_value.__enter__ = MagicMock(return_value=[("gid-2",)])
        mock_rw.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(bot, "process_result") as mock_process:
            entity_type_loop(bot, "artist", 100)
            # Should process gid-1 and gid-3, not gid-2
            assert mock_process.call_count == 2
            processed_gids = [call[0][0][0] for call in mock_process.call_args_list]
            assert "gid-1" in processed_gids
            assert "gid-3" in processed_gids
            assert "gid-2" not in processed_gids

    @patch("bot.common.do_readwrite_query")
    @patch("bot.common.do_readonly_query")
    def test_no_results_does_nothing(self, mock_ro, mock_rw, bot):
        mock_ro.return_value.__enter__ = MagicMock(return_value=[])
        mock_ro.return_value.__exit__ = MagicMock(return_value=False)
        mock_rw.return_value.__enter__ = MagicMock(return_value=[])
        mock_rw.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(bot, "process_result") as mock_process:
            entity_type_loop(bot, "artist", 100)
            mock_process.assert_not_called()
