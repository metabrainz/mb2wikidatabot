#!/usr/bin/env python2
"""
This is a bot to automatically add MBIDs to Wikidata pages.

Usage: python2 run.py [options]

Command line options:

-createtable: Create the table storing the processed MBIDs
-entites: A comma-separated list of entity types for which MBIDs are to be
          added to their Wikidata pages. Example: `-entities:artist,work,place`
-limit:x: Only handle x entities of *each* type
"""
import sys
from time import sleep

import psycopg2
import pywikibot as wp
from bot.common import mainloop, SettingsReloadedException

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
