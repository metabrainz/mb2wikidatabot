"""Exception classes for the wikidata bot."""


class SkipPage(Exception):
    def __init__(self, url: str) -> None:
        self.url = url


class IsDisambigPage(SkipPage):
    def __str__(self) -> str:
        return "{url} is a disambiguation page".format(url=self.url)


class HasFragment(SkipPage):
    def __str__(self) -> str:
        return "{url} has a fragment".format(url=self.url)


class InstanceOfForbidden(SkipPage):
    def __init__(self, url: str, item_id: str) -> None:
        super().__init__(url)
        self.item_id = item_id

    def __str__(self) -> str:
        return "{url} is an instance of {id}".format(url=self.url, id=self.item_id)


class IsRedirectWithItemPage(SkipPage):
    def __str__(self) -> str:
        return "{url} is a redirect page, but is linked to a Wikidata item".format(url=self.url)


class IsRedirectPage(Exception):
    def __init__(self, old: str, new: str) -> None:
        self.old = old
        self.new = new

    def __str__(self) -> str:
        return "%s is a redirect to %s" % (self.old, self.new)


class PageGone(Exception):
    def __init__(self, pagename: str) -> None:
        self.pagename = pagename

    def __str__(self) -> str:
        return "%s is no more" % (self.pagename)


class SettingsReloadedException(Exception):
    """Custom Exception class to signal that the settings have been reloaded
    during SIGHUP processing."""

    pass
