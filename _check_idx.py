import sqlite3
from pathlib import Path
p = Path('data/journeymap.db')
con = sqlite3.connect(p)
cur = con.cursor()
cur.execute("PRAGMA index_list('photos')")
idx = cur.fetchall()
print('INDEX_COUNT:', len(idx))
for row in idx:
    print('INDEX:', row[1], 'UNIQUE' if row[2] else 'NON_UNIQUE')
con.close()
