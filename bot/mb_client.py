"""Wrapper around musicbrainz_bot.editing that handles HTTP 429/503 with
retry + exponential backoff."""

import urllib.error
from collections.abc import Callable
from time import sleep
from typing import Any

import pywikibot as wp

MAX_RETRIES = 5
INITIAL_BACKOFF = 10  # seconds
BACKOFF_FACTOR = 2


def _get_retry_after(exc: urllib.error.HTTPError) -> int | None:
    """Extract Retry-After header value from an HTTPError, or return None."""
    try:
        val = exc.headers.get("Retry-After")
        if val is not None:
            return int(val)
    except (AttributeError, ValueError, TypeError):
        pass
    return None


def mb_request_with_retry(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Call func(*args, **kwargs) with retry on HTTP 429/503.

    Raises the original exception if retries are exhausted.
    """
    backoff = INITIAL_BACKOFF
    for attempt in range(MAX_RETRIES):
        try:
            return func(*args, **kwargs)
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                wait = _get_retry_after(e) or backoff
                wp.output(
                    "MusicBrainz returned HTTP %d, waiting %d seconds "
                    "(attempt %d/%d)" % (e.code, wait, attempt + 1, MAX_RETRIES)
                )
                sleep(wait)
                backoff = min(backoff * BACKOFF_FACTOR, 300)
            else:
                raise
    # Final attempt, let it raise if it fails
    return func(*args, **kwargs)
