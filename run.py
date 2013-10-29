"""
This is a bot to automatically add MBIDs to Wikidata pages.

Usage: python2 run.py [options]

Command line options:

-createtable: Create the table storing the processed MBIDs
-dryrun:    Don't write anything on the server
-limit:x:   Only handle x artists
"""
from bot import common
if __name__ == '__main__':
    common.mainloop()
