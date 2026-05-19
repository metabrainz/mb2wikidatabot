# Wikidata bot to add MBIDs

## Installation

This project uses [uv](https://docs.astral.sh/uv/) for dependency management.

```sh
uv sync
```

For development (includes ruff, pytest, pre-commit):

```sh
uv sync --dev
pre-commit install
```

## Configuration

Configure pywikibot so the login works non-interactively. This repository is made to work with the `MineoBot` user on Wikidata. Its password needs to be stored in a file called `passwd` with the following content:

```
('MineoBot', '<bot-password-here>')
```

Copy `bot/settings.py.dist` to `bot/settings.py` and edit the connection string
settings. Their format is
documented
[here](https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING).

The `readonly_connection_string` is used to connect to a MusicBrainz database to
extract all the entities that have links to Wikipedia articles. The `readwrite`
connection string is used to connect to a database with read and write access to
keep a log of all already processed MBIDs.

If you want the bot to automatically edit URLs to redirect pages in Wikipedia to
their target pages, set the `mb_user`, `mb_password`, and `mb_editor_id` values
in `bot/settings.py` to your bot's login data in MusicBrainz.

## Running

```sh
uv run python run.py
```

Options:
- `-limit:N` — only process N entities of each type
- `-entities:artist,work` — only process specific entity types

The configuration of a running bot can be reloaded by sending it a HUP signal.

## Testing

```sh
uv run pytest
```

With coverage:

```sh
uv run pytest --cov=bot
```

## Code quality

```sh
uvx ruff check bot/ tests/
uvx ruff format bot/ tests/
```

## Bot policy

Please make sure that your bot does not violate the
[Code of Conduct](https://musicbrainz.org/doc/Code_of_Conduct/Bots) for bots in MusicBrainz.
