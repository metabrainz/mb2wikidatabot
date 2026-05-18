import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from bot.mb_client import _get_retry_after, mb_request_with_retry


def _make_http_error(code, retry_after=None):
    headers = MagicMock()
    headers.get = MagicMock(return_value=retry_after)
    err = urllib.error.HTTPError("http://example.com", code, "msg", headers, None)
    return err


class TestGetRetryAfter:
    def test_returns_value_from_header(self):
        exc = _make_http_error(429, "30")
        assert _get_retry_after(exc) == 30

    def test_returns_none_when_missing(self):
        exc = _make_http_error(429, None)
        assert _get_retry_after(exc) is None

    def test_returns_none_on_non_numeric(self):
        exc = _make_http_error(429, "not-a-number")
        assert _get_retry_after(exc) is None

    def test_returns_none_when_no_headers_attr(self):
        exc = Exception("no headers")
        assert _get_retry_after(exc) is None


class TestMbRequestWithRetry:
    @patch("bot.mb_client.sleep")
    def test_succeeds_on_first_try(self, mock_sleep):
        func = MagicMock(return_value="ok")
        assert mb_request_with_retry(func, "arg1", key="val") == "ok"
        func.assert_called_once_with("arg1", key="val")
        mock_sleep.assert_not_called()

    @patch("bot.mb_client.sleep")
    def test_retries_on_429(self, mock_sleep):
        func = MagicMock(side_effect=[_make_http_error(429), "ok"])
        assert mb_request_with_retry(func) == "ok"
        assert func.call_count == 2
        mock_sleep.assert_called_once_with(10)  # INITIAL_BACKOFF

    @patch("bot.mb_client.sleep")
    def test_retries_on_503(self, mock_sleep):
        func = MagicMock(side_effect=[_make_http_error(503), "ok"])
        assert mb_request_with_retry(func) == "ok"
        assert func.call_count == 2

    @patch("bot.mb_client.sleep")
    def test_respects_retry_after_header(self, mock_sleep):
        func = MagicMock(side_effect=[_make_http_error(429, "60"), "ok"])
        mb_request_with_retry(func)
        mock_sleep.assert_called_once_with(60)

    @patch("bot.mb_client.sleep")
    def test_exponential_backoff(self, mock_sleep):
        func = MagicMock(
            side_effect=[_make_http_error(429), _make_http_error(429), "ok"]
        )
        mb_request_with_retry(func)
        assert mock_sleep.call_args_list[0][0][0] == 10  # initial
        assert mock_sleep.call_args_list[1][0][0] == 20  # doubled

    @patch("bot.mb_client.sleep")
    def test_raises_after_max_retries(self, mock_sleep):
        func = MagicMock(side_effect=_make_http_error(429))
        with pytest.raises(urllib.error.HTTPError):
            mb_request_with_retry(func)
        # MAX_RETRIES attempts + 1 final attempt
        assert func.call_count == 6

    @patch("bot.mb_client.sleep")
    def test_non_retryable_error_raises_immediately(self, mock_sleep):
        func = MagicMock(side_effect=_make_http_error(404))
        with pytest.raises(urllib.error.HTTPError):
            mb_request_with_retry(func)
        assert func.call_count == 1
        mock_sleep.assert_not_called()

    @patch("bot.mb_client.sleep")
    def test_backoff_caps_at_300(self, mock_sleep):
        # 10, 20, 40, 80, 160 -> all under 300
        # next would be 320 -> capped to 300
        errors = [_make_http_error(429) for _ in range(5)]
        func = MagicMock(side_effect=errors + ["ok"])
        mb_request_with_retry(func)
        # Last backoff: 10*2^4 = 160, still under cap
        # But the 6th call is the final attempt (no sleep after it)
        assert mock_sleep.call_args_list[-1][0][0] == 160
