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
from bot.common import mainloop
mainloop()
