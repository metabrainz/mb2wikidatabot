#!/usr/bin/env python2
import brewer2mpl
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import psycopg2 as pg
from bot import settings

STATS_QUERY = """
SELECT processed, sum(count(gid)) over (order by processed)
FROM bot_wikidata_%s_processed
GROUP BY processed;
"""

ENTITIES = ("artist", "rg")

def main():
    db = pg.connect(settings.connection_string)
    ax = plt.gca()
    colors = brewer2mpl.get_map("Accent","qualitative",
                       8).mpl_colors
    for i, entity in enumerate(ENTITIES):
        cursor = db.cursor()
        cursor.execute(STATS_QUERY % entity)
        data = cursor.fetchall()
        dates = mdates.date2num(item[0] for item in data)
        plt.plot_date(dates, [item[1] for item in data], linestyle="solid",
                      marker=",", label=entity, color=colors[i])
    plt.xticks(rotation=20)
    plt.grid(True)
    plt.legend(loc="best")
    plt.savefig("wikidata-bot.png")

if __name__ == '__main__':
    main()
