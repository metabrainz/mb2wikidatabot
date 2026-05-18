"""Mock pywikibot before any test imports it.

bot.mb_client and bot.common import pywikibot. Without this mock,
pywikibot initialization adds ~0.5s to the test suite.
"""

import sys
from unittest.mock import MagicMock

mock_wp = MagicMock()
mock_wp.__name__ = "pywikibot"
mock_wp.exceptions.NoPageError = type("NoPageError", (Exception,), {})
mock_wp.exceptions.Error = type("Error", (Exception,), {})
mock_wp.exceptions.SiteDefinitionError = type("SiteDefinitionError", (Exception,), {})
mock_wp.exceptions.InvalidTitleError = type("InvalidTitleError", (Exception,), {})
mock_wp.exceptions.OtherPageSaveError = type("OtherPageSaveError", (Exception,), {})
mock_wp.config.simulate = False

sys.modules.setdefault("pywikibot", mock_wp)
sys.modules.setdefault("pywikibot.exceptions", mock_wp.exceptions)
