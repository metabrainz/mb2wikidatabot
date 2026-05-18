"""Mock pywikibot before any test imports it.

bot.mb_client imports pywikibot for wp.output(). Without this mock,
pywikibot initialization adds ~0.5s to the test suite.
"""

import sys
from unittest.mock import MagicMock

mock_wp = MagicMock()
mock_wp.__name__ = "pywikibot"

sys.modules.setdefault("pywikibot", mock_wp)
