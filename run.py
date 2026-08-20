#!/usr/bin/env python
"""Entry point for the MusicBrainz-to-Wikidata bot.

Runs the main loop with automatic recovery from database errors and
settings reloads (via SIGHUP).

Usage: uv run python run.py [options]

Options:
    -limit:N              Only process N entities of each type
    -entities:artist,work Only process specific entity types
"""

import traceback
from time import sleep

import psycopg2

from bot.common import SettingsReloadedException, mainloop

while True:
    try:
        mainloop()
    except psycopg2.Error as e:
        # It might take a few seconds for everything to properly work after
        # settings have been changed, so give Docker a few seconds to get
        # everything running.
        print("Trouble connecting to PostgreSQL: {}".format(e.pgerror))
        traceback.print_exc()
        sleep(5)
    except SettingsReloadedException:
        # Settings have been reloaded, just start the mainloop again.
        pass
    except Exception as err:
        print("General exception caught: {}".format(err))
        traceback.print_exc()
        sleep(5)
