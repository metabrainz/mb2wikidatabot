# Wikidata bot to add MBIDs

## Installation

This needs both `psycopg2` and
[pywikipediabot](http://pywikipediabot.sourceforge.net/) (rewrite branch)

The former can be installed with

> pip install -r requirements.txt

the latter with

> svn co http://svn.wikimedia.org/svnroot/pywikipedia/branches/rewrite pywikipediabot
>
> cd pywikipediabot
>
> python2 setup.py install

Copy `bot/settings.py.dist` to `bot/settings.py` and edit the connection string
which is documented
[here](http://www.postgresql.org/docs/current/static/libpq-connect.html#LIBPQ-CONNSTRING).

To use the `stats.py` file which generates a plot of the number of entries linked in Wikidata you also need [matplotlib](http://matplotlib.org/) and [brewer2mpl](https://github.com/jiffyclub/brewer2mpl).
