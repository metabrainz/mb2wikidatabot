"""Conftest that mocks pywikibot before bot.common is imported.

pywikibot initialization is extremely slow (reads user-config.py,
connects to sites). We mock it at sys.modules level before any
test imports bot.common.
"""

import sys
from unittest.mock import MagicMock

# Create a real class for ItemPage so isinstance() works
class FakeItemPage:
    def __init__(self, *args, **kwargs):
        pass

    @classmethod
    def fromPage(cls, page):
        pass


# Mock pywikibot before anything imports it
mock_wp = MagicMock()
mock_wp.__name__ = "pywikibot"
mock_wp.exceptions.NoPageError = type("NoPageError", (Exception,), {})
mock_wp.exceptions.Error = type("Error", (Exception,), {})
mock_wp.exceptions.SiteDefinitionError = type("SiteDefinitionError", (Exception,), {})
mock_wp.exceptions.InvalidTitleError = type("InvalidTitleError", (Exception,), {})
mock_wp.exceptions.OtherPageSaveError = type("OtherPageSaveError", (Exception,), {})
mock_wp.config.simulate = False
mock_wp.ItemPage = FakeItemPage

sys.modules["pywikibot"] = mock_wp
sys.modules["pywikibot.exceptions"] = mock_wp.exceptions
