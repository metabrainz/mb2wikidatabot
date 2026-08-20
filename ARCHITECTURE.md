# Architecture

## Overview

This bot links MusicBrainz entities to their corresponding Wikidata items by
adding MBID claims (e.g. P434 for artists, P436 for release groups). It reads
Wikipedia/Wikidata URLs from the MusicBrainz database, resolves them to Wikidata
items, and adds the appropriate property if missing.

## Pipeline

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
│ MusicBrainz DB  │────▶│ Filter       │────▶│ Resolve URL to  │────▶│ Add MBID     │
│ (readonly)      │     │ already      │     │ Wikidata item   │     │ claim to     │
│                 │     │ processed    │     │                 │     │ Wikidata     │
└─────────────────┘     └──────────────┘     └─────────────────┘     └──────────────┘
                              │                      │
                              ▼                      ▼
                        ┌──────────┐          ┌──────────────┐
                        │ Bot DB   │          │ Fix redirect │
                        │ (r/w)    │          │ or end link  │
                        └──────────┘          │ on MB        │
                                              └──────────────┘
```

1. **Query**: For each entity type (artist, work, label, etc.), fetch all
   entities that have a Wikipedia or Wikidata URL relationship in MusicBrainz.
2. **Filter**: Skip entities already processed (tracked in a separate PostgreSQL
   database).
3. **Resolve**: Convert the Wikipedia/Wikidata URL to a Wikidata ItemPage.
   During resolution, pages are checked for skip conditions (see below).
4. **Act**: Either add the MBID claim to Wikidata, or fix a redirect/dead link
   on MusicBrainz.
5. **Record**: Mark the entity as processed so it's skipped next cycle.

The bot loops through all entity types, then sleeps for `sleep_time_in_seconds`
(default: 1 hour) before starting again.

## Skip conditions

A URL is skipped (not processed) if:

- It contains a URL fragment (`#section`) — usually a discography subsection
- The Wikipedia page is a disambiguation page
- The Wikipedia page is a redirect **with its own Wikidata item** (e.g. an
  article that exists in other languages)
- The Wikidata item is an instance of a forbidden type (disambiguation page
  Q4167410, discography Q273057)

If the page is a redirect **without** its own Wikidata item, the bot fixes the
URL in MusicBrainz to point to the redirect target.

If the Wikipedia page no longer exists, the bot marks the relationship as ended
in MusicBrainz.

## Module structure

```
bot/
├── checks.py        # URL validation and skip logic (pure, no side effects)
├── common.py        # Orchestration: Bot class, main loop, DB access
├── const.py         # Constants: property IDs, link IDs, SQL templates
├── exceptions.py    # Exception classes (pure, no dependencies)
├── mb_client.py     # HTTP retry wrapper for MusicBrainz mechanize calls
├── queries.py       # SQL query builders (pure string formatting)
└── settings.py      # Runtime config (generated from settings.py.dist)
```

- **Pure modules** (`checks`, `exceptions`, `queries`, `mb_client`): No
  module-level side effects, take dependencies as parameters, fully unit-tested.
- **Orchestration** (`common`): Wires everything together with pywikibot,
  psycopg2, and the musicbrainz-bot library. Has module-level initialization.

## MusicBrainz editing

The bot optionally edits MusicBrainz via the `musicbrainz-bot` library (a
`mechanize`-based web scraper). It performs two types of edits:

- **Fix redirects**: Update a URL relationship to point to the redirect target.
- **End removed**: Mark a relationship as ended when the Wikipedia page no longer
  exists.

These edits are rate-limited by `settings.mb_edit_delay` (default: 5 seconds
between edits) and protected by retry-with-backoff on HTTP 429/503.

## Deployment

The bot runs in Docker with consul-template for configuration injection:

- `consul-template` renders `settings.py` and `passwd` from Consul KV
- The bot process is managed as a runit service
- Sending SIGHUP reloads settings without restarting
- A single instance runs at a time (`wikidata-bot.service`)

## Authentication

- **Wikidata**: Authenticates as `MineoBot` using pywikibot bot passwords.
  MineoBot has a bot flag on Wikidata (exempt from API rate limits).
- **MusicBrainz**: Authenticates via the `musicbrainz-bot` mechanize client
  for URL edits. Rate-limited by MusicBrainz's server-side limits.
